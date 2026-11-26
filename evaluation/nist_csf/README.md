# NIST CSF 2.0 evaluation corpus

This is a separate, public-source corpus for the next evaluation. The original
self-authored synthetic corpus and its results remain unchanged.

The corpus contains 17 files in the seven formats supported by DocEnquire:

| Format | Count |
|---|---:|
| PDF | 9 |
| DOCX | 1 |
| PPTX | 1 |
| XLSX | 1 |
| HTML | 3 |
| Markdown | 1 |
| TXT | 1 |

It is a curated set of NIST cybersecurity publications and webpages, including
the Secure Software Development Framework, not a
pre-packaged dataset from NIST. The corpus manifest records each source URL,
publication, local filename, format conversion, SHA-256, and deterministic document
ID. The NIST SP 1302, SP 800-61 Rev. 3, SP 800-30 Rev. 1, and SP 800-37 Rev. 2
items are text-only conversions from their official PDFs. These conversions retain
extracted text but not original page layout, figures, or formatting.

Official source indexes:

- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [NIST CSF 2.0 Quick-Start Guides](https://www.nist.gov/cyberframework/quick-start-guides)
- [NIST CSF 2.0 Profiles](https://www.nist.gov/cyberframework/profiles)

The documents are from official NIST sources. Retain the source links and publication
numbers when using or redistributing the corpus, and review each source for any
third-party material or rights notices. The HTML files omit scripts, navigation,
and embedded media.

## Rebuild and upload

Run from the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe evaluation\nist_csf\build_corpus.py
.\.venv\Scripts\python.exe evaluation\nist_csf\upload_corpus.py
```

The uploader uses the isolated `nist-csf-2-0-eval` collection and checks each file
hash and returned document ID. Do not mix these documents with the existing
`default` collection used by the synthetic experiment.

## Evaluation

[`questions.jsonl`](./questions.jsonl) contains 56 questions: 44 answerable and
12 unanswerable. The answerable questions cover all 17 corpus documents; each
row includes the expected document IDs and filenames, while unanswerable rows
have empty document lists. Every row targets the isolated
`nist-csf-2-0-eval` collection.

Run the baseline and prompt-v2 against the same question set, model, and
retrieval settings; change only the prompt. Manually label answer correctness
and unsupported claims for at least 20 outputs (preferably all 56). Measure
retrieval hit@k, answer accuracy, unsupported-claim rate, and abstention.
Citation correctness is not a scored metric for this experiment.

Run each configuration from the repository root in PowerShell, with the
corresponding prompt active in the API:

```powershell
.\.venv\Scripts\python.exe evaluation\evaluate.py `
  --questions evaluation\nist_csf\questions.jsonl `
  --output evaluation\nist_csf\baseline.json `
  --label nist-csf-baseline
```

After activating prompt-v2 and restarting the API, use a separate output file:

```powershell
.\.venv\Scripts\python.exe evaluation\evaluate.py `
  --questions evaluation\nist_csf\questions.jsonl `
  --output evaluation\nist_csf\prompt-v2.json `
  --label nist-csf-prompt-v2 `
  --change "prompt only"
```
