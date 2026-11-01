import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

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
    questions: list[dict], api_url: str, top_k: int
) -> list[dict]:
    async with httpx.AsyncClient(timeout=180) as client:
        results = []
        for question in questions:
            response = await client.post(
                api_url,
                json={
                    "question": question["question"],
                    "collection_name": question.get("collection_name", "default"),
                    "top_k": question.get("top_k", top_k),
                },
            )
            response.raise_for_status()
            answer = response.json()
            retrieved_documents = answer.get("source_documents", [])
            answer_text = answer.get("answer", "")
            normalized = answer_text.casefold()
            results.append(
                {
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
            )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run or score the DocEnquire RAG evaluation.")
    parser.add_argument("--questions", type=Path, help="JSONL question set for a model run")
    parser.add_argument("--output", type=Path, help="Run output JSON path")
    parser.add_argument("--api-url", default="http://localhost:8000/api/v1/query/")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--label", default="baseline", help="Run/configuration label")
    parser.add_argument("--change", default="", help="Single setting changed from baseline")
    parser.add_argument(
        "--score",
        type=Path,
        help="Add metrics to an existing run JSON after human labels are reviewed",
    )
    args = parser.parse_args()

    if args.score:
        result = json.loads(args.score.read_text(encoding="utf-8"))
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

    records = asyncio.run(run_questions(questions, args.api_url, args.top_k))
    result = {
        "metadata": {
            "label": args.label,
            "single_change": args.change,
            "api_url": args.api_url,
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "question_count": len(records),
        },
        "records": records,
        "metrics": score_records(records),
    }
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["metrics"], indent=2))


if __name__ == "__main__":
    main()
