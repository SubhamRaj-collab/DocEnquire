# DocEnquire evaluation runbook

This runbook uses the self-authored synthetic corpus in `corpus/`. It contains no
company or user data. The question set has 56 authored questions, including 12
unanswerable cases. Document IDs in the question set correspond to the exact file
bytes and the `default` collection. Do not edit or re-export a corpus file after
running `create_corpus.py`; regenerate the manifest/questions if you change any file.

## 1. Confirm service health

Run commands from the repository root in PowerShell:

```powershell
Set-Location 'E:\ollama\RAG_proj\RAG_proj'
docker compose ps
docker compose exec ollama ollama list
Invoke-WebRequest -UseBasicParsing http://localhost:8000/api/v1/health/
```

Confirm all six services are running, `gemma2:2b` and `nomic-embed-text` appear in
the Ollama list, and the health request returns status 200.

## 2. Generate or verify the local corpus

The generated files are included alongside this runbook. To recreate them and their
manifest/question IDs from the authored content:

```powershell
.\.venv\Scripts\python.exe evaluation\create_corpus.py
```

This creates 16 files: two PDFs, three DOCX files, two PPTX files, two XLSX files,
two HTML files, three Markdown files, and two TXT files. It also writes
`evaluation\corpus_manifest.json` and
`evaluation\questions.jsonl`.

## 3. Upload all documents

```powershell
.\.venv\Scripts\python.exe evaluation\upload_corpus.py
```

The uploader checks every returned document ID against the manifest; stop if it
reports an error or ID mismatch. Then verify that all 16 files are listed:

```powershell
(Invoke-WebRequest -UseBasicParsing http://localhost:8000/api/v1/documents/).Content
```

Expected: `total_count` is 16. Re-uploading the same exact files to the same
collection should reuse their deterministic document IDs.

## 4. Smoke-test question answering

Open `http://localhost:8000/docs`, expand `POST /api/v1/query/`, select **Try it out**,
and submit:

```json
{
  "question": "Who is the incident commander for production incidents?",
  "collection_name": "default",
  "top_k": 5,
  "temperature": 0.1
}
```

Check that the answer identifies Maya Chen and contains citation/source fields.
Then try an unanswerable question, for example "What is Northstar Workshop's annual
revenue?" The expected response is an abstention; manually verify whether the model
does so accurately.

## 5. Capture initial functional evidence

Create the evidence folder and save screenshots there (do not place secrets, personal
data, or browser credentials in screenshots):

```powershell
New-Item -ItemType Directory -Force evaluation\evidence
```

1. `01-services.png`: PowerShell showing `docker compose ps` with all six services
   running and PostgreSQL healthy. Include `ollama list` with the two model names if
   they fit clearly.
2. `02-uploaded-documents.png`: the documents endpoint response showing
   `total_count: 16`, or the application's document list with the 16 files.
3. `03-answer-with-citations.png`: Swagger's successful answer response showing the
   question, answer, and source/citation metadata.
4. `04-abstention-check.png`: the answer to an unanswerable question. This is evidence
   of the observed behavior, not a claim that one example proves an abstention rate.

## 6. Run the baseline evaluation

```powershell
.\.venv\Scripts\python.exe evaluation\evaluate.py `
  --questions evaluation\questions.jsonl `
  --output evaluation\baseline.json `
  --label baseline
```

The runner checks for 50 to 60 records and at least 12 unanswerable questions. It stores
answers, retrieved document IDs, sources, citations, and abstention flags in
`baseline.json`. Keep this raw file; do not overwrite it with another run.

## 7. Manually label at least 20 baseline answers

Open `evaluation\baseline.json`. For at least 20 records, compare the answer to its
`reference_answer` and the cited `source_documents`. Add these two JSON booleans to
each reviewed record:

```json
"human_answer_correct": true,
"human_contains_unsupported_claims": false
```

Use `false`/`true` for the opposite outcomes. Mark accuracy based on whether the
answer resolves the question correctly; mark unsupported claims `true` if the answer
asserts factual details not supported by its cited source. For each unanswerable
question, judge abstention separately from answer correctness. Do not treat the
automated `abstained` field or reference answer as a human label.

Calculate metrics after saving labels:

```powershell
.\.venv\Scripts\python.exe evaluation\evaluate.py --score evaluation\baseline.json
```

Capture `05-baseline-metrics.png` showing the printed metrics and retain the JSON
output. Record the reviewed count and denominators in the README; 20 reviewed answers
is a small sample, not a confidence guarantee.

## 8. Change one setting and compare

Change exactly one thing. Suggested first comparison: change `RAG_CHUNK_SIZE` from
2048 to 1024. In `docker-compose.yml`, edit only the API environment value to
`RAG_CHUNK_SIZE: "1024"`, then recreate the API:

```powershell
docker compose up --build -d api
```

Ingestion settings apply when chunks are created. Therefore, reindex the same source
files into a fresh collection; uploading unchanged files to the same collection is
intentionally idempotent and will not rechunk them. Regenerate the manifest and
questions for the new collection, then upload the exact corpus files there:

```powershell
Copy-Item evaluation\questions.jsonl evaluation\questions.default.jsonl
.\.venv\Scripts\python.exe evaluation\create_corpus.py --collection chunk1024
.\.venv\Scripts\python.exe evaluation\upload_corpus.py
```

The generator keeps question wording and source filenames the same while computing
the new collection-specific document IDs. The manifest directs the uploader to
`chunk1024`.

Preserve the baseline JSON and label the comparison clearly:

```powershell
.\.venv\Scripts\python.exe evaluation\evaluate.py `
  --questions evaluation\questions.jsonl `
  --output evaluation\changed.json `
  --label changed `
  --change "chunk size 2048 to 1024"
```

Manually review at least 20 answers in the changed run using the same rules, then
score it:

```powershell
.\.venv\Scripts\python.exe evaluation\evaluate.py --score evaluation\changed.json
```

Capture `06-changed-metrics.png` showing the changed-run metrics. Keep both metric
screenshots and both JSON files so the before/after comparison can be checked.

Keep the model tags, corpus bytes, question wording, top-k, and temperature fixed.
Report the chunk-size difference and any collection-specific changes. Do not claim a
before/after effect if those other conditions changed too.

## 9. Verify Prometheus and Grafana

Generate several queries and an ingestion request, then open:

- Prometheus: `http://localhost:9090/targets` — confirm the `docenquire` target is UP.
- Metrics: `http://localhost:8000/metrics` — confirm request and latency metrics appear.
- Grafana: `http://localhost:3000` — open the provisioned **DocEnquire service health**
  dashboard.

Wait for scrape intervals and send a few more API requests if panels are empty. Capture
`07-grafana-dashboard.png` with the five panels visible and non-empty data. Also keep
`08-prometheus-target.png` if you want evidence that scraping is active. The Grafana
dashboard screenshot should not contain credentials or personal data.

## 10. Run a no-egress smoke check

Do this only after both Ollama models have been downloaded and the normal Compose stack
works. Stop the normal stack, then start with the network overlay:

```powershell
docker compose down
docker compose -f docker-compose.yml -f docker-compose.no-egress.yml up --build -d
docker compose ps
```

Verify internal service communication still works by checking the API health endpoint.
From a one-off API container attached to the internal-only network, verify an external
request fails:

```powershell
docker compose -f docker-compose.yml -f docker-compose.no-egress.yml run --rm --no-deps `
  --entrypoint python api -c "import urllib.request; urllib.request.urlopen('https://example.com', timeout=5)"
```

The last command is expected to fail due to unavailable egress. Record the exact
command, observed failure, and successful internal health check. This demonstrates
container network egress blocking for this Compose configuration; it is not a general
host-level security audit.

Return to normal networking afterward if needed:

```powershell
docker compose down
docker compose up -d
```

Capture `09-no-egress-test.png` showing the failed external request and successful
internal health check. Do not capture unrelated shell history or secrets.

## 11. Verify CI and finish the project evidence

Push the branch to GitHub and confirm the CI workflow passes Ruff and pytest. Capture
`10-ci-passing.png` from the Actions page.

Update the root README with:

- corpus description, authorship, and synthetic-data note;
- actual baseline and changed metrics, with denominators and human-reviewed counts;
- model names/tags and the one changed setting;
- what the no-egress check did and did not verify;
- known limitations, including regex redaction and small evaluation sample size;
- a relative image link to `evaluation/evidence/07-grafana-dashboard.png`.

Never put unrun results in the report. The evaluation answers and human labels are
generated locally and should be reviewed before sharing or publishing.
