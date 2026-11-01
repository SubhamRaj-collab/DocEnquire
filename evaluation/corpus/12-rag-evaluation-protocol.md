# Northstar RAG Evaluation Protocol

## Dataset
Use 56 questions written for the evaluation corpus. Include 12 unanswerable questions and record relevant document IDs for answerable questions.

## Retrieval
The baseline retrieves the top 5 chunks. Retrieval hit rate at 5 is the fraction of answerable questions with at least one relevant document ID among retrieved source IDs.

## Human review
Manually label at least 20 answers for answer correctness and unsupported claims. Reviewers compare claims with the cited source text. An automated judge may assist but is not ground truth.

## Comparison
Change one setting at a time, such as chunk size or the context-only instruction. Keep the question set and model versions fixed.

## Reporting
Report answer accuracy, hallucination rate, unanswerable abstention, and retrieval hit rate with denominators. Record model names, configuration, date, dataset limitations, and reviewer method.
