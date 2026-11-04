import json

from evaluation.evaluate import load_resume_records, score_records, write_run


def test_evaluation_metrics_and_unlabeled_review_handling() -> None:
    records = [
        {
            "relevant_document_ids": ["doc-1"],
            "retrieved_document_ids": ["doc-1"],
            "unanswerable": True,
            "abstained": True,
            "human_answer_correct": True,
            "human_contains_unsupported_claims": False,
        },
        {
            "relevant_document_ids": ["doc-2"],
            "retrieved_document_ids": ["doc-3"],
            "unanswerable": False,
            "abstained": False,
            "human_answer_correct": False,
            "human_contains_unsupported_claims": True,
        },
    ]

    metrics = score_records(records)

    assert metrics["retrieval_hit_rate_at_k"] == 0.5
    assert metrics["answer_accuracy_human_reviewed"] == 0.5
    assert metrics["hallucination_rate_human_reviewed"] == 0.5
    assert metrics["unanswerable_abstention_rate"] == 1
    assert metrics["human_reviewed_count"] == 2
    assert metrics["at_least_20_human_reviews"] is False


def test_partial_run_checkpoint_can_resume_completed_records(tmp_path) -> None:
    output = tmp_path / "baseline.json"
    question = {
        "id": "q1",
        "question": "Question?",
        "relevant_document_ids": [],
        "unanswerable": True,
        "answer": "I don't have enough information.",
    }

    write_run(output, {"label": "baseline"}, [question], "failed", 2)

    stored = json.loads(output.read_text(encoding="utf-8"))
    assert stored["metadata"]["status"] == "failed"
    assert stored["metadata"]["completed_count"] == 1
    assert load_resume_records(output, [question, {"id": "q2"}]) == [question]
