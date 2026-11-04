import argparse
import asyncio
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

import httpx


ABSTENTION_TEXT = "I don't have enough information in the provided documents to answer"


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def score_records(records: list[dict]) -> dict:
    retrieval_records = [
        record for record in records if record.get("relevant_document_ids")
    ]
    retrieval_hits = sum(
        bool(
            set(record["relevant_document_ids"])
            & set(record.get("retrieved_document_ids", []))
        )
        for record in retrieval_records
    )
    unanswerable_records = [record for record in records if record.get("unanswerable")]
    abstentions = sum(record.get("abstained", False) for record in unanswerable_records)

    reviewed = [
        record
        for record in records
        if isinstance(record.get("human_answer_correct"), bool)
        and isinstance(record.get("human_contains_unsupported_claims"), bool)
    ]

    return {
        "question_count": len(records),
        "retrieval_hit_rate_at_k": (
            retrieval_hits / len(retrieval_records) if retrieval_records else None
        ),
        "retrieval_denominator": len(retrieval_records),
        "answer_accuracy_human_reviewed": (
            sum(record["human_answer_correct"] for record in reviewed) / len(reviewed)
            if reviewed
            else None
        ),
        "hallucination_rate_human_reviewed": (
            sum(record["human_contains_unsupported_claims"] for record in reviewed)
            / len(reviewed)
            if reviewed
            else None
        ),
        "human_reviewed_count": len(reviewed),
        "at_least_20_human_reviews": len(reviewed) >= 20,
        "unanswerable_abstention_rate": (
            abstentions / len(unanswerable_records) if unanswerable_records else None
        ),
        "unanswerable_denominator": len(unanswerable_records),
    }


async def run_questions(
    questions: list[dict],
    api_url: str,
    top_k: int,
    timeout_seconds: float,
    retries: int,
    existing_records: list[dict],
    save_progress,
) -> list[dict]:
    records_by_id = {record["id"]: record for record in existing_records}
    completed = len(records_by_id)
    timeout = httpx.Timeout(
        connect=15,
        read=timeout_seconds,
        write=30,
        pool=30,
    )
    async with httpx.AsyncClient(timeout=timeout) as client:
        for index, question in enumerate(questions, start=1):
            if question["id"] in records_by_id:
                continue

            print(
                f"[{completed + 1}/{len(questions)}] {question['id']}: "
                f"{question['question']}",
                flush=True,
            )
            response = None
            for attempt in range(retries + 1):
                try:
                    response = await client.post(
                        api_url,
                        json={
                            "question": question["question"],
                            "collection_name": question.get("collection_name", "default"),
                            "top_k": question.get("top_k", top_k),
                        },
                    )
                    response.raise_for_status()
                    break
                except (httpx.TimeoutException, httpx.ConnectError) as error:
                    if attempt >= retries:
                        partial_records = [
                            records_by_id[item["id"]]
                            for item in questions
                            if item["id"] in records_by_id
                        ]
                        save_progress(partial_records, "failed")
                        raise RuntimeError(
                            f"Question {question['id']} failed after {attempt + 1} "
                            f"attempt(s): {error}. Saved {len(partial_records)} "
                            f"completed record(s); rerun with --resume."
                        ) from error
                    delay = min(5 * (2**attempt), 30)
                    print(
                        f"Transient API failure for {question['id']}; "
                        f"retrying in {delay}s ({attempt + 1}/{retries}).",
                        file=sys.stderr,
                        flush=True,
                    )
                    await asyncio.sleep(delay)
                except httpx.HTTPStatusError as error:
                    partial_records = [
                        records_by_id[item["id"]]
                        for item in questions
                        if item["id"] in records_by_id
                    ]
                    save_progress(partial_records, "failed")
                    raise RuntimeError(
                        f"API returned HTTP {error.response.status_code} for "
                        f"question {question['id']}. Saved {len(partial_records)} "
                        "completed record(s); inspect the API and rerun with --resume."
                    ) from error

            if response is None:
                raise RuntimeError(f"No response received for question {question['id']}")

            answer = response.json()
            retrieved_documents = answer.get("source_documents", [])
            answer_text = answer.get("answer", "")
            normalized = answer_text.casefold()
            records_by_id[question["id"]] = {
                **question,
                "answer": answer_text,
                "retrieved_document_ids": sorted(
                    {
                        source["document_id"]
                        for source in retrieved_documents
                        if source.get("document_id")
                    }
                ),
                "source_documents": retrieved_documents,
                "citations": answer.get("citations", []),
                "abstained": (
                    ABSTENTION_TEXT.casefold() in normalized
                    or "no relevant documents found" in normalized
                ),
            }
            completed += 1
            current_records = [
                records_by_id[item["id"]]
                for item in questions
                if item["id"] in records_by_id
            ]
            save_progress(current_records, "running")
            print(f"Completed {completed}/{len(questions)} questions.", flush=True)

    return [records_by_id[item["id"]] for item in questions]


def write_run(
    path: Path,
    metadata: dict,
    records: list[dict],
    status: str,
    total_questions: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "metadata": {
            **metadata,
            "status": status,
            "completed_count": len(records),
            "question_count": total_questions,
        },
        "records": records,
        "metrics": score_records(records),
    }
    with NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
    ) as temporary:
        json.dump(payload, temporary, indent=2, ensure_ascii=False)
        temporary.write("\n")
        temp_path = Path(temporary.name)
    temp_path.replace(path)


def load_resume_records(path: Path, questions: list[dict]) -> list[dict]:
    existing = json.loads(path.read_text(encoding="utf-8"))
    valid_ids = {question["id"] for question in questions}
    records = existing.get("records", [])
    record_ids = [record.get("id") for record in records]
    if len(record_ids) != len(set(record_ids)) or not set(record_ids) <= valid_ids:
        raise ValueError(f"{path} contains duplicate or unknown question IDs")
    return records


def question_set_digest(questions: list[dict]) -> str:
    serialized = json.dumps(
        questions, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run or score the DocEnquire RAG evaluation.")
    parser.add_argument("--questions", type=Path, help="JSONL question set for a model run")
    parser.add_argument("--output", type=Path, help="Run output JSON path")
    parser.add_argument("--api-url", default="http://localhost:8000/api/v1/query/")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=600,
        help="Maximum wait for each API response (default: 600 seconds)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=1,
        help="Retries after transient network timeout/connection errors (default: 1)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Continue an existing partial run at --output, skipping completed question IDs",
    )
    parser.add_argument("--label", default="baseline", help="Run/configuration label")
    parser.add_argument("--change", default="", help="Single setting changed from baseline")
    parser.add_argument(
        "--score",
        type=Path,
        help="Add metrics to an existing run JSON after human labels are reviewed",
    )
    args = parser.parse_args()

    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be greater than zero")
    if args.retries < 0:
        parser.error("--retries cannot be negative")

    if args.score:
        result = json.loads(args.score.read_text(encoding="utf-8"))
        if result.get("metadata", {}).get("status") != "completed":
            parser.error("Cannot score an incomplete run; finish it before manual review")
        result["metrics"] = score_records(result["records"])
        args.score.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result["metrics"], indent=2))
        return

    if not args.questions or not args.output:
        parser.error("--questions and --output are required for an evaluation run")

    questions = load_jsonl(args.questions)
    if not 50 <= len(questions) <= 60:
        parser.error(f"Expected 50–60 questions; received {len(questions)}")
    unanswerable_count = sum(bool(question.get("unanswerable")) for question in questions)
    if unanswerable_count < 12:
        parser.error(f"Expected at least 12 unanswerable questions; received {unanswerable_count}")
    if any(not question.get("id") or not question.get("question") for question in questions):
        parser.error("Every question must include a non-empty id and question")
    if any(
        not isinstance(question.get("relevant_document_ids"), list)
        or not isinstance(question.get("unanswerable"), bool)
        for question in questions
    ):
        parser.error(
            "Every question must include relevant_document_ids (list) and unanswerable (bool)"
        )

    if args.output.exists() and not args.resume:
        parser.error(
            f"{args.output} already exists. Choose a new --output path or pass --resume."
        )
    if args.resume and not args.output.exists():
        parser.error(f"Cannot resume: {args.output} does not exist")

    metadata = {
        "label": args.label,
        "single_change": args.change,
        "api_url": args.api_url,
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "top_k": args.top_k,
        "question_set_sha256": question_set_digest(questions),
        "timeout_seconds": args.timeout_seconds,
        "retries": args.retries,
    }
    existing_records = []
    if args.resume:
        saved = json.loads(args.output.read_text(encoding="utf-8"))
        saved_metadata = saved.get("metadata", {})
        for key in ("label", "single_change", "api_url", "top_k", "question_set_sha256"):
            if saved_metadata.get(key) != metadata[key]:
                parser.error(
                    f"Cannot resume: saved run's {key} does not match this invocation"
                )
        metadata["timestamp_utc"] = saved_metadata.get(
            "timestamp_utc", metadata["timestamp_utc"]
        )
        existing_records = load_resume_records(args.output, questions)

    def save_progress(records: list[dict], status: str) -> None:
        write_run(args.output, metadata, records, status, len(questions))

    try:
        records = asyncio.run(
            run_questions(
                questions,
                args.api_url,
                args.top_k,
                args.timeout_seconds,
                args.retries,
                existing_records,
                save_progress,
            )
        )
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error

    save_progress(records, "completed")
    print(json.dumps(score_records(records), indent=2))


if __name__ == "__main__":
    main()
