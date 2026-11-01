import html
import json
import hashlib
import argparse
import re
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import pymupdf
from docx import Document
from openpyxl import Workbook
from pptx import Presentation
from pptx.util import Inches, Pt


ROOT = Path(__file__).parent
CORPUS_DIR = ROOT / "corpus"

DOCUMENTS = [
    {
        "filename": "01-incident-response.pdf",
        "kind": "pdf",
        "text": """Northstar Workshop | Incident Response Playbook
Incident command
The incident commander for all production incidents is Maya Chen. The incident commander assigns an operations lead and a communications lead at incident start.
Severity and acknowledgement
Priority P1 means a production outage affecting all members. The on-call responder acknowledges a P1 within 10 minutes. Priority P2 means a degraded feature with a workaround; acknowledge it within one business hour.
Recovery objectives
The recovery time objective for the member portal is four hours. The recovery point objective is 15 minutes. These objectives are targets, not guarantees.
Communications
During a P1, the communications lead posts an update every 30 minutes in the status channel. The incident commander records the start time, impact, decisions, and recovery time in the incident log.
Review
Within five business days of closing a P1, the incident commander schedules a blameless review and assigns owners and due dates to follow-up actions.""",
    },
    {
        "filename": "02-document-privacy.pdf",
        "kind": "pdf",
        "text": """Northstar Workshop | Document Privacy Standard
Purpose and scope
This standard applies to documents uploaded to the Northstar Workshop knowledge assistant. The evaluation corpus is synthetic and contains no member records.
Redaction
The service redacts detected email addresses and telephone numbers from extracted text before chunking, embedding, retrieval, and model prompting. Pattern-based detection can miss unusual formats and is not a guarantee of anonymization.
Original files
Original uploaded files are retained in the configured upload volume for 30 days, then removed by the operator's retention process. Redaction does not alter the original file.
Access
Only workshop administrators may upload or delete documents. Members may search documents published to their collection. Do not upload credentials, payment card data, medical records, or confidential third-party material.
Deletion
An administrator may request removal by document ID. The operator verifies the document is absent from the vector collection and deletes the corresponding original file.
Incident handling
If sensitive material is uploaded accidentally, restrict access, remove the document, and record the incident without copying the sensitive content into the incident report.""",
    },
    {
        "filename": "03-release-procedure.docx",
        "kind": "docx",
        "text": """Northstar Workshop Release Procedure
Purpose
This procedure describes the standard release for the member portal.
Release owner
Eli Navarro is the release manager. The release manager confirms the candidate version, deployment window, and rollback owner.
Change freeze
The weekly change freeze begins Tuesday at 15:00 UTC and ends Wednesday at 09:00 UTC. Emergency changes may proceed with incident commander approval.
Approval
Two reviewers must approve a production change. At least one reviewer must not be the change author. The release manager checks automated tests and records the approval links.
Deployment
Deploy first to staging, run the smoke checklist, and then deploy to production in a monitored window. Announce the version and start time in the release channel.
Rollback
If the smoke check fails or error rate rises above the release threshold, the rollback owner starts rollback within 15 minutes. Verify the previous version is healthy and record the result.""",
    },
    {
        "filename": "04-calibration-work-instruction.docx",
        "kind": "docx",
        "text": """Northstar Workshop Calibration Work Instruction
Equipment
This instruction covers the digital temperature probe assigned to calibration bench S-14.
Interval and owner
Calibrate the probe every 90 days. Jo Patel owns the calibration schedule and records each completed check in the equipment log.
Acceptance range
At the 20 degrees Celsius reference point, the probe reading must be within plus or minus 0.25 degrees Celsius. If it is outside tolerance, label the probe out of service and notify the lab coordinator.
Procedure
Allow the probe and reference bath to stabilize for five minutes. Record the reference temperature, measured temperature, date, and operator. Repeat the measurement three times.
Records
Keep calibration records for 24 months. The next due date is calculated from the completion date, not the date the equipment was purchased.""",
    },
    {
        "filename": "05-support-escalation.docx",
        "kind": "docx",
        "text": """Northstar Workshop Support Escalation Guide
Service lead
Nia Brooks is the member support service lead and owns escalation policy updates.
Priority P1
A P1 is a production outage affecting all members or a confirmed loss of member data. Acknowledge within 10 minutes, page the incident commander, and keep the reporter updated every 30 minutes.
Priority P2
A P2 is a degraded feature where a safe workaround exists. Acknowledge within one business hour and route it to the feature owner.
Priority P3
A P3 is a general question or minor issue without service impact. Acknowledge within one business day.
Escalation details
Include the affected feature, start time, observed impact, and steps already tried. Never include passwords, access tokens, or unredacted personal data in a support ticket.
Handoff
The outgoing responder names the next owner and summarizes the next action before ending a shift.""",
    },
    {
        "filename": "06-new-member-onboarding.pptx",
        "kind": "pptx",
        "slides": [
            ("New Member Onboarding", "Northstar Workshop\nA practical first-week orientation"),
            ("Day One", "Check-in begins at 09:30 local time.\nThe welcome and safety briefing lasts 45 minutes.\nThe group laboratory is named Cedar."),
            ("First Week", "Each new member has three pairing sessions during week one.\nThe mentor records goals in the onboarding checklist.\nAsk the lab coordinator before using restricted equipment."),
            ("Completion", "Complete the safety quiz before independent lab access.\nThe coordinator confirms access and records the completion date."),
        ],
    },
    {
        "filename": "07-service-continuity.pptx",
        "kind": "pptx",
        "slides": [
            ("Northstar Service Continuity", "Operational recovery overview\nTraining scenario; targets are not guarantees"),
            ("Regions and Targets", "Primary region: us-east-2.\nRecovery region: us-west-2.\nRecovery point objective: 15 minutes.\nMember portal recovery time objective: four hours."),
            ("Exercise", "The most recent tabletop exercise was 12 August 2025.\nThe exercise coordinator was Ravi Shah.\nThe next exercise is planned for February 2026."),
            ("Recovery Sequence", "Confirm incident command.\nDeclare the recovery region.\nRestore the latest verified backup.\nRun the member portal smoke checklist before reopening."),
        ],
    },
    {
        "filename": "08-equipment-inventory.xlsx",
        "kind": "xlsx",
        "sheets": {
            "Inventory": [
                ["Asset", "Location", "Quantity", "Status", "Custodian"],
                ["Digital temperature probe", "Bench S-14", "2", "1 active; 1 spare", "Jo Patel"],
                ["Portable microscope", "Lab Cedar", "3", "2 active; 1 repair", "Uma Das"],
                ["Safety goggles", "Supply room A", "24", "20 available; 4 inspection", "Lee Park"],
                ["Bench power supply", "Lab Birch", "5", "5 active", "Omar Ali"],
                ["Air quality sensor", "Room 204", "4", "3 active; 1 calibration", "Tess Wong"],
            ]
        },
    },
    {
        "filename": "09-monthly-service-metrics.xlsx",
        "kind": "xlsx",
        "sheets": {
            "Monthly Metrics": [
                ["Month", "Tickets", "Median first response minutes", "Resolved within target percent"],
                ["2025-09", "84", "22", "91"],
                ["2025-10", "96", "19", "93"],
                ["2025-11", "88", "21", "92"],
                ["2025-12", "102", "25", "89"],
                ["2026-01", "79", "17", "95"],
            ]
        },
    },
    {
        "filename": "10-account-access-policy.html",
        "kind": "html",
        "text": """Northstar Workshop Account Access Policy
Identity
Each member uses an individual account. Shared accounts are prohibited.
Authentication
Staff accounts use a security key as the second factor. Members use a second factor supported by the account portal.
Roles
Viewer can read published documents. Editor can create and update documents in an assigned collection. Administrator can manage access and delete documents.
Review
Collection owners review access every 90 days and remove access when a member changes teams.
Reporting
Report suspected account compromise to the service desk immediately. Do not send passwords or recovery codes in email.""",
    },
    {
        "filename": "11-backup-operations.html",
        "kind": "html",
        "text": """Northstar Workshop Backup Operations
Schedule
The document database backup starts daily at 02:15 UTC.
Retention
Daily backups are retained for 35 days. A monthly archive is retained for 12 months.
Restore validation
The operations team performs a restore test once per quarter. The test records the backup identifier, restore start and finish times, and validation outcome.
Failure response
If a scheduled backup fails, the on-call operator retries it once and opens a P2 ticket if the retry fails.
Ownership
The data operations rotation owns backup monitoring. The service lead reviews quarterly restore-test results.""",
    },
    {
        "filename": "12-rag-evaluation-protocol.md",
        "kind": "markdown",
        "text": """# Northstar RAG Evaluation Protocol

## Dataset
Use 56 questions written for the evaluation corpus. Include 12 unanswerable questions and record relevant document IDs for answerable questions.

## Retrieval
The baseline retrieves the top 5 chunks. Retrieval hit rate at 5 is the fraction of answerable questions with at least one relevant document ID among retrieved source IDs.

## Human review
Manually label at least 20 answers for answer correctness and unsupported claims. Reviewers compare claims with the cited source text. An automated judge may assist but is not ground truth.

## Comparison
Change one setting at a time, such as chunk size or the context-only instruction. Keep the question set and model versions fixed.

## Reporting
Report answer accuracy, hallucination rate, unanswerable abstention, and retrieval hit rate with denominators. Record model names, configuration, date, dataset limitations, and reviewer method.""",
    },
    {
        "filename": "13-document-retention.md",
        "kind": "markdown",
        "text": """# Northstar Document Retention

## Uploaded originals
Uploaded source files are retained for 30 days in the local upload volume. An operator removes expired originals according to the retention schedule.

## Operational logs
Application logs are retained for 14 days. Do not place document contents, secrets, or personal data in log messages.

## Evaluation outputs
Evaluation run files may contain generated answers and source excerpts. Store them in the project evaluation directory, limit access to the project team, and delete them when the evaluation is no longer needed.

## Removal requests
An administrator verifies the document ID, removes indexed chunks, deletes the original, and records the completion date without copying sensitive content.

## Limitations
These training retention periods describe the sample policy. They do not automatically configure a deletion scheduler.""",
    },
    {
        "filename": "14-local-deployment-checklist.md",
        "kind": "markdown",
        "text": """# Northstar Local Deployment Checklist

## Startup
Start PostgreSQL, Chroma, and Ollama before checking the API health endpoint. Confirm the configured language and embedding models are present in Ollama.

## Smoke checks
The API listens on port 8000. Prometheus listens on port 9090. Grafana listens on port 3000. The API metrics path is `/metrics`.

## Observability
Check request totals, HTTP errors, request latency, time to first generated token, and ingestion failures. Send a sample query before expecting the dashboard to show non-zero traffic.

## Recovery
Keep persistent volumes for PostgreSQL, Chroma, uploads, and Ollama model weights. Back up volumes before changing service versions.

## Security
The sample Compose credentials are for local development only. Replace them before shared use. The internal-only network overlay blocks external container egress but still permits communication among its attached services.""",
    },
    {
        "filename": "15-workshop-glossary.txt",
        "kind": "text",
        "text": """Northstar Workshop Glossary

Priority P1 means a production outage affecting all members or confirmed loss of member data.

Priority P2 means a degraded feature with a safe workaround.

RPO means recovery point objective: the target maximum period of data changes that may be lost after recovery.

RTO means recovery time objective: the target time to restore a service after an incident.

Smoke check means a short set of checks confirming the primary user workflow works after a deployment or restore.

Collection means a named group of documents indexed together for retrieval.""",
    },
    {
        "filename": "16-facilities-emergency-card.txt",
        "kind": "text",
        "text": """Northstar Workshop Facilities Emergency Card

Evacuation
The outdoor assembly point is the south courtyard beside the bicycle shelter.

First aid
The first aid kit is mounted outside the main workshop office. Notify the facilities coordinator after use.

Emergency coordinator
Sam Rivera is the facilities emergency coordinator on weekdays.

Alarm
On hearing the building alarm, leave by the nearest safe exit. Do not use the passenger lift.

Headcount
Team leads bring the daily attendance list to the assembly point and report missing people to the emergency coordinator.

Re-entry
Only emergency services or the facilities coordinator may authorize re-entry.""",
    },
]


ANSWERABLE = [
    ("a001", "Who is the incident commander for production incidents?", "01-incident-response.pdf", "Maya Chen."),
    ("a002", "How quickly should a P1 be acknowledged?", "01-incident-response.pdf", "Within 10 minutes."),
    ("a003", "How often should status updates be posted during a P1?", "01-incident-response.pdf", "Every 30 minutes."),
    ("a004", "What is the member portal recovery time objective?", "01-incident-response.pdf", "Four hours."),
    ("a005", "How soon after a P1 should a blameless review be scheduled?", "01-incident-response.pdf", "Within five business days of closing it."),
    ("a006", "At which stages does the service redact detected emails and phone numbers?", "02-document-privacy.pdf", "Before chunking, embedding, retrieval, and model prompting."),
    ("a007", "How long are original uploaded files retained under the sample standard?", "02-document-privacy.pdf", "30 days."),
    ("a008", "Which roles may upload or delete documents?", "02-document-privacy.pdf", "Workshop administrators."),
    ("a009", "Name two types of data the policy says not to upload.", "02-document-privacy.pdf", "Examples include credentials, payment card data, medical records, and confidential third-party material."),
    ("a010", "Who is the release manager?", "03-release-procedure.docx", "Eli Navarro."),
    ("a011", "When does the weekly change freeze begin?", "03-release-procedure.docx", "Tuesday at 15:00 UTC."),
    ("a012", "How many reviewers must approve a production change?", "03-release-procedure.docx", "Two reviewers."),
    ("a013", "How soon should rollback start if the release smoke check fails?", "03-release-procedure.docx", "Within 15 minutes."),
    ("a014", "How often is the S-14 temperature probe calibrated?", "04-calibration-work-instruction.docx", "Every 90 days."),
    ("a015", "What is the allowed deviation at the 20 C reference point?", "04-calibration-work-instruction.docx", "Within plus or minus 0.25 degrees Celsius."),
    ("a016", "Who owns the calibration schedule?", "04-calibration-work-instruction.docx", "Jo Patel."),
    ("a017", "How many times should the calibration measurement be repeated?", "04-calibration-work-instruction.docx", "Three times."),
    ("a018", "Who is the support service lead?", "05-support-escalation.docx", "Nia Brooks."),
    ("a019", "What is the P2 acknowledgement target?", "05-support-escalation.docx", "Within one business hour."),
    ("a020", "What details should an escalation include?", "05-support-escalation.docx", "Affected feature, start time, observed impact, and steps already tried."),
    ("a021", "What time does new-member check-in begin?", "06-new-member-onboarding.pptx", "09:30 local time."),
    ("a022", "What is the onboarding group laboratory called?", "06-new-member-onboarding.pptx", "Cedar."),
    ("a023", "How many pairing sessions happen in the first week?", "06-new-member-onboarding.pptx", "Three."),
    ("a024", "What must be completed before independent lab access?", "06-new-member-onboarding.pptx", "The safety quiz."),
    ("a025", "What is the primary service continuity region?", "07-service-continuity.pptx", "us-east-2."),
    ("a026", "What is the recovery region?", "07-service-continuity.pptx", "us-west-2."),
    ("a027", "Who coordinated the most recent tabletop exercise?", "07-service-continuity.pptx", "Ravi Shah."),
    ("a028", "How many digital temperature probes are listed for bench S-14?", "08-equipment-inventory.xlsx", "Two."),
    ("a029", "How many safety goggles are available?", "08-equipment-inventory.xlsx", "20."),
    ("a030", "Who is the custodian for the portable microscope?", "08-equipment-inventory.xlsx", "Uma Das."),
    ("a031", "How many tickets were recorded in 2025-10?", "09-monthly-service-metrics.xlsx", "96."),
    ("a032", "What was the median first response in 2026-01?", "09-monthly-service-metrics.xlsx", "17 minutes."),
    ("a033", "What percent of tickets were resolved within target in 2025-12?", "09-monthly-service-metrics.xlsx", "89 percent."),
    ("a034", "What second factor do staff accounts use?", "10-account-access-policy.html", "A security key."),
    ("a035", "Who can manage access and delete documents?", "10-account-access-policy.html", "An administrator."),
    ("a036", "How often do collection owners review access?", "10-account-access-policy.html", "Every 90 days."),
    ("a037", "At what time does the daily database backup start?", "11-backup-operations.html", "02:15 UTC."),
    ("a038", "How long are daily backups retained?", "11-backup-operations.html", "35 days."),
    ("a039", "How frequently is a restore test performed?", "11-backup-operations.html", "Once per quarter."),
    ("a040", "How many questions does the evaluation protocol specify?", "12-rag-evaluation-protocol.md", "56."),
    ("a041", "How many answers must be manually labeled at minimum?", "12-rag-evaluation-protocol.md", "At least 20."),
    ("a042", "What setting-change rule applies to the comparison?", "12-rag-evaluation-protocol.md", "Change one setting at a time and keep the questions and model versions fixed."),
    ("a043", "How long are application logs retained in the sample policy?", "13-document-retention.md", "14 days."),
    ("a044", "Does the sample retention policy automatically configure a deletion scheduler?", "13-document-retention.md", "No."),
]

UNANSWERABLE = [
    ("u001", "What is Northstar Workshop's annual revenue?"),
    ("u002", "Who is the company's chief executive officer?"),
    ("u003", "What is the monthly rent for the workshop building?"),
    ("u004", "Which health insurance provider covers employees?"),
    ("u005", "What is the exact salary of the support service lead?"),
    ("u006", "Which vendor supplies the building's electricity?"),
    ("u007", "What is the password for the PostgreSQL database?"),
    ("u008", "What is the personal mobile number of Maya Chen?"),
    ("u009", "How many customers use the mobile application each day?"),
    ("u010", "What is the company's net profit for fiscal year 2025?"),
    ("u011", "Which airline should a new member use for business travel?"),
    ("u012", "What date was Northstar Workshop legally incorporated?"),
]


def write_pdf(path: Path, text: str) -> None:
    pdf = pymupdf.open()
    pdf.set_metadata(
        {
            "title": text.splitlines()[0],
            "author": "DocEnquire synthetic evaluation corpus",
            "subject": "Self-authored synthetic training content",
            "creator": "evaluation/create_corpus.py",
            "producer": "PyMuPDF",
            "creationDate": "D:20250101000000Z",
            "modDate": "D:20250101000000Z",
        }
    )
    page = pdf.new_page()
    y = 55
    for line in text.splitlines():
        if not line.strip():
            y += 8
            continue
        font_size = 16 if y == 55 else (12 if len(line) < 70 and not line.endswith(".") else 10)
        if y > 740:
            page = pdf.new_page()
            y = 55
        page.insert_text((55, y), line, fontsize=font_size)
        y += font_size + 7
    pdf.save(path, no_new_id=True)
    pdf.close()


def write_docx(path: Path, text: str) -> None:
    document = Document()
    document.core_properties.author = "DocEnquire synthetic evaluation corpus"
    document.core_properties.created = datetime(2025, 1, 1)
    document.core_properties.modified = datetime(2025, 1, 1)
    for index, line in enumerate(text.splitlines()):
        if not line.strip():
            continue
        if index == 0:
            document.add_heading(line, 0)
        elif not line.endswith(".") and len(line) < 55:
            document.add_heading(line, 2)
        else:
            document.add_paragraph(line)
    document.save(path)


def write_pptx(path: Path, slides: list[tuple[str, str]]) -> None:
    presentation = Presentation()
    presentation.core_properties.author = "DocEnquire synthetic evaluation corpus"
    presentation.core_properties.created = datetime(2025, 1, 1)
    presentation.core_properties.modified = datetime(2025, 1, 1)
    presentation.slide_width = Inches(10)
    presentation.slide_height = Inches(5.625)
    for title, body in slides:
        slide = presentation.slides.add_slide(presentation.slide_layouts[1])
        slide.shapes.title.text = title
        frame = slide.placeholders[1].text_frame
        frame.clear()
        for index, line in enumerate(body.splitlines()):
            paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
            paragraph.text = line
            paragraph.font.size = Pt(22)
    presentation.save(path)


def write_xlsx(path: Path, sheets: dict[str, list[list[str]]]) -> None:
    workbook = Workbook()
    workbook.properties.creator = "DocEnquire synthetic evaluation corpus"
    workbook.properties.created = datetime(2025, 1, 1)
    workbook.properties.modified = datetime(2025, 1, 1)
    first_sheet = True
    for sheet_name, rows in sheets.items():
        sheet = workbook.active if first_sheet else workbook.create_sheet()
        first_sheet = False
        sheet.title = sheet_name
        for row in rows:
            sheet.append(row)
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
    workbook.save(path)


def normalize_zip_timestamps(path: Path) -> None:
    with tempfile.NamedTemporaryFile(delete=False, dir=path.parent, suffix=".zip") as tmp:
        temp_path = Path(tmp.name)
    try:
        with zipfile.ZipFile(path, "r") as source, zipfile.ZipFile(
            temp_path, "w"
        ) as target:
            target.comment = source.comment
            for member in source.infolist():
                normalized = zipfile.ZipInfo(
                    member.filename,
                    date_time=(2025, 1, 1, 0, 0, 0),
                )
                normalized.compress_type = member.compress_type
                normalized.external_attr = member.external_attr
                normalized.internal_attr = member.internal_attr
                normalized.create_system = member.create_system
                normalized.flag_bits = member.flag_bits
                content = source.read(member.filename)
                if member.filename == "docProps/core.xml":
                    content = re.sub(
                        rb"(<dcterms:modified[^>]*>).*?(</dcterms:modified>)",
                        rb"\g<1>2025-01-01T00:00:00Z\g<2>",
                        content,
                        count=1,
                    )
                target.writestr(normalized, content)
        temp_path.replace(path)
    finally:
        temp_path.unlink(missing_ok=True)


def write_html(path: Path, text: str) -> None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = html.escape(lines[0])
    body = []
    for line in lines[1:]:
        escaped = html.escape(line)
        if len(line) < 55 and not line.endswith("."):
            body.append(f"<h2>{escaped}</h2>")
        else:
            body.append(f"<p>{escaped}</p>")
    path.write_text(
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{title}</title></head><body><h1>{title}</h1>{''.join(body)}"
        "</body></html>\n",
        encoding="utf-8",
    )


def generate(collection: str) -> None:
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []
    ids_by_filename = {}

    for item in DOCUMENTS:
        path = CORPUS_DIR / item["filename"]
        kind = item["kind"]
        if kind == "pdf":
            write_pdf(path, item["text"])
        elif kind == "docx":
            write_docx(path, item["text"])
        elif kind == "pptx":
            write_pptx(path, item["slides"])
        elif kind == "xlsx":
            write_xlsx(path, item["sheets"])
        elif kind == "html":
            write_html(path, item["text"])
        else:
            path.write_text(item["text"].strip() + "\n", encoding="utf-8")
        if kind in {"docx", "pptx", "xlsx"}:
            normalize_zip_timestamps(path)

        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        document_id = str(uuid5(NAMESPACE_URL, f"docenquire:{collection}:{digest}"))
        ids_by_filename[item["filename"]] = document_id
        manifest.append(
            {
                "filename": path.name,
                "document_id": document_id,
                "sha256": digest,
                "collection_name": collection,
                "format": path.suffix.lstrip("."),
                "size_bytes": path.stat().st_size,
            }
        )

    (ROOT / "corpus_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    questions = []
    for question_id, question, filename, reference_answer in ANSWERABLE:
        questions.append(
            {
                "id": question_id,
                "question": question,
                "relevant_document_ids": [ids_by_filename[filename]],
                "relevant_document_filenames": [filename],
                "collection_name": collection,
                "unanswerable": False,
                "reference_answer": reference_answer,
            }
        )
    for question_id, question in UNANSWERABLE:
        questions.append(
            {
                "id": question_id,
                "question": question,
                "relevant_document_ids": [],
                "relevant_document_filenames": [],
                "collection_name": collection,
                "unanswerable": True,
                "reference_answer": "I don't have enough information in the provided documents to answer this question.",
            }
        )
    (ROOT / "questions.jsonl").write_text(
        "".join(json.dumps(question, ensure_ascii=False) + "\n" for question in questions),
        encoding="utf-8",
    )

    counts = {}
    for item in DOCUMENTS:
        ext = Path(item["filename"]).suffix.lower()
        counts[ext] = counts.get(ext, 0) + 1
    counts_text = ", ".join(
        f"{count} {extension.lstrip('.').upper()}" for extension, count in sorted(counts.items())
    )
    print(
        f"Created {len(manifest)} documents across {len(counts)} formats and "
        f"{len(questions)} questions ({len(UNANSWERABLE)} unanswerable)."
    )
    print(f"Corpus: {CORPUS_DIR}")
    print(f"Manifest: {ROOT / 'corpus_manifest.json'}")
    print(f"Questions: {ROOT / 'questions.jsonl'}")
    print(f"Formats: {counts_text}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate the synthetic RAG corpus and questions.")
    parser.add_argument("--collection", default="default")
    generate(parser.parse_args().collection)
