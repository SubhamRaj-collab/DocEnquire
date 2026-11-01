from evaluation.evaluate import score_records


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
