import hashlib
import html
import io
import json
import re
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import httpx
import pymupdf
from bs4 import BeautifulSoup
from docx import Document
from openpyxl import load_workbook
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt


ROOT = Path(__file__).parent
CORPUS_DIR = ROOT / "corpus"
MANIFEST_PATH = ROOT / "corpus_manifest.json"
COLLECTION_NAME = "nist-csf-2-0-eval"
FIXED_DATE = datetime(2024, 2, 26)

PDF_SOURCES = [
    {
        "filename": "01-nist-csf-2.0-framework.pdf",
        "url": "https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf",
        "title": "The NIST Cybersecurity Framework (CSF) 2.0",
        "publication": "NIST CSWP 29",
    },
    {
        "filename": "02-sp-1299-csf-overview.pdf",
        "url": "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.1299.pdf",
        "title": "NIST CSF 2.0 Resource and Overview Guide",
        "publication": "NIST SP 1299",
    },
    {
        "filename": "03-sp-1300-small-business.pdf",
        "url": "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.1300.pdf",
        "title": "NIST CSF 2.0 Small Business Quick-Start Guide",
        "publication": "NIST SP 1300",
    },
    {
        "filename": "04-sp-1301-organizational-profiles.pdf",
        "url": "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.1301.pdf",
        "title": "NIST CSF 2.0 Organizational Profiles Quick-Start Guide",
        "publication": "NIST SP 1301",
    },
    {
        "filename": "05-sp-1303-enterprise-risk-management.pdf",
        "url": "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.1303.pdf",
        "title": "NIST CSF 2.0 Enterprise Risk Management Quick-Start Guide",
        "publication": "NIST SP 1303",
    },
    {
        "filename": "06-sp-1305-supply-chain-risk-management.pdf",
        "url": "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.1305.pdf",
        "title": "NIST CSF 2.0 Cybersecurity Supply Chain Risk Management Guide",
        "publication": "NIST SP 1305",
    },
    {
        "filename": "07-sp-1308-workforce-management.pdf",
        "url": "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.1308.pdf",
        "title": "NIST CSF 2.0 Cybersecurity, ERM, and Workforce Management Guide",
        "publication": "NIST SP 1308",
    },
    {
        "filename": "08-sp-1347-informative-references.pdf",
        "url": "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.1347.pdf",
        "title": "NIST CSF 2.0 Informative References Quick-Start Guide",
        "publication": "NIST SP 1347",
    },
    {
        "filename": "09-sp-800-218-secure-software-development.pdf",
        "url": "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-218.pdf",
        "title": "Secure Software Development Framework (SSDF) Version 1.1",
        "publication": "NIST SP 800-218",
    },
]

DERIVED_PDF_SOURCES = [
    {
        "filename": "10-sp-1302-tiers.pptx",
        "url": "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.1302.pdf",
        "title": "NIST CSF 2.0 Tiers Quick-Start Guide",
        "publication": "NIST SP 1302",
        "format": "pptx",
        "transformation": "Text extracted page-by-page from the official PDF into one or more slides per page.",
    },
    {
        "filename": "11-sp-800-61-rev3-incident-response.docx",
        "url": "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-61r3.pdf",
        "title": "Incident Response Recommendations and Considerations for Cybersecurity Risk Management",
        "publication": "NIST SP 800-61 Rev. 3",
        "format": "docx",
        "transformation": "Text extracted page-by-page from the official PDF into a Word document.",
    },
    {
        "filename": "12-sp-800-30-rev1-risk-assessment.md",
        "url": "https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-30r1.pdf",
        "title": "Guide for Conducting Risk Assessments",
        "publication": "NIST SP 800-30 Rev. 1",
        "format": "md",
        "transformation": "Text extracted page-by-page from the official PDF into Markdown.",
    },
    {
        "filename": "13-sp-800-37-rev2-risk-management-framework.txt",
        "url": "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-37r2.pdf",
        "title": "Risk Management Framework for Information Systems and Organizations",
        "publication": "NIST SP 800-37 Rev. 2",
        "format": "txt",
        "transformation": "Text extracted page-by-page from the official PDF into UTF-8 text.",
    },
]

XLSX_SOURCE = {
    "filename": "14-csf-2.0-organizational-profile-template.xlsx",
    "url": "https://www.nist.gov/document/csf-20-organizational-profile-template",
    "title": "NIST CSF 2.0 Organizational Profile Template",
    "publication": "NIST CSF 2.0 profile resource",
}

HTML_SOURCES = [
    {
        "filename": "15-csf-2.0-overview.html",
        "url": "https://www.nist.gov/cyberframework",
        "title": "NIST Cybersecurity Framework",
    },
    {
        "filename": "16-csf-2.0-quick-start-guides.html",
        "url": "https://www.nist.gov/cyberframework/quick-start-guides",
        "title": "NIST CSF 2.0 Quick-Start Guides",
    },
    {
        "filename": "17-csf-2.0-profiles.html",
        "url": "https://www.nist.gov/cyberframework/profiles",
        "title": "NIST CSF 2.0 Profiles",
    },
]


def fetch(client: httpx.Client, url: str) -> bytes:
    response = client.get(url)
    response.raise_for_status()
    return response.content


def extract_pdf_pages(content: bytes, source_title: str) -> list[str]:
    if not content.startswith(b"%PDF"):
        raise ValueError(f"{source_title}: response is not a PDF")
    pages: list[str] = []
    with pymupdf.open(stream=content, filetype="pdf") as pdf:
        for page in pdf:
            pages.append(page.get_text("text").strip())
    useful_pages = sum(bool(page) for page in pages)
    if useful_pages == 0 or sum(len(page) for page in pages) < 500:
        raise ValueError(f"{source_title}: PDF text extraction returned too little text")
    return pages


def write_docx(path: Path, source: dict, pages: list[str]) -> None:
    doc = Document()
    doc.core_properties.author = "NIST source text; locally converted for format coverage"
    doc.core_properties.created = FIXED_DATE
    doc.core_properties.modified = FIXED_DATE
    doc.add_heading(source["title"], 0)
    doc.add_paragraph(f"Source: {source['url']}")
    doc.add_paragraph(f"Publication: {source['publication']}")
    doc.add_paragraph("Text-only local conversion. Original page layout and figures are not included.")
    for page_number, text in enumerate(pages, start=1):
        if text:
            doc.add_heading(f"Source PDF page {page_number}", level=2)
            for block in re.split(r"\n\s*\n", text):
                if block.strip():
                    doc.add_paragraph(block.strip())
    doc.save(path)


def text_chunks(text: str, max_chars: int = 1800) -> list[str]:
    chunks: list[str] = []
    remaining = text.strip()
    while remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining)
            break
        boundary = remaining.rfind("\n", 0, max_chars)
        if boundary < max_chars // 2:
            boundary = remaining.rfind(" ", 0, max_chars)
        if boundary < max_chars // 2:
            boundary = max_chars
        chunks.append(remaining[:boundary].strip())
        remaining = remaining[boundary:].strip()
    return chunks


def write_pptx(path: Path, source: dict, pages: list[str]) -> None:
    deck = Presentation()
    deck.core_properties.author = "NIST source text; locally converted for format coverage"
    deck.core_properties.created = FIXED_DATE
    deck.core_properties.modified = FIXED_DATE
    deck.slide_width = Inches(10)
    deck.slide_height = Inches(7.5)
    layout = deck.slide_layouts[1]

    for page_number, page_text in enumerate(pages, start=1):
        chunks = text_chunks(page_text)
        for chunk_number, chunk in enumerate(chunks, start=1):
            slide = deck.slides.add_slide(layout)
            slide.shapes.title.text = (
                f"{source['publication']} | PDF page {page_number}"
                + (f" | part {chunk_number}" if len(chunks) > 1 else "")
            )
            frame = slide.placeholders[1].text_frame
            frame.clear()
            frame.word_wrap = True
            if page_number == 1 and chunk_number == 1:
                chunk = f"Source: {source['url']}\n\n{chunk}"
            frame.text = chunk
            for paragraph in frame.paragraphs:
                paragraph.font.size = Pt(11)
                paragraph.font.color.rgb = RGBColor(35, 45, 55)
    if not deck.slides:
        raise ValueError(f"{source['title']}: no text available for PPTX conversion")
    deck.save(path)


def write_markdown(path: Path, source: dict, pages: list[str]) -> None:
    parts = [
        f"# {source['title']}",
        "",
        f"Source: {source['url']}",
        f"Publication: {source['publication']}",
        "",
        "Text-only local conversion. Original page layout and figures are not included.",
    ]
    for page_number, text in enumerate(pages, start=1):
        if text:
            parts.extend(["", f"## Source PDF page {page_number}", "", text])
    path.write_text("\n".join(parts).strip() + "\n", encoding="utf-8")


def write_text(path: Path, source: dict, pages: list[str]) -> None:
    parts = [
        source["title"],
        f"Source: {source['url']}",
        f"Publication: {source['publication']}",
        "Text-only local conversion. Original page layout and figures are not included.",
    ]
    for page_number, text in enumerate(pages, start=1):
        if text:
            parts.extend(["", f"--- Source PDF page {page_number} ---", "", text])
    path.write_text("\n".join(parts).strip() + "\n", encoding="utf-8")


def write_html(path: Path, source: dict, content: bytes) -> None:
    soup = BeautifulSoup(content, "lxml")
    for tag in soup(
        ["script", "style", "nav", "footer", "header", "noscript", "svg", "iframe", "img"]
    ):
        tag.decompose()
    main = soup.find("main") or soup.body or soup
    title = source["title"]
    body = str(main)
    output = (
        "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>{html.escape(title)}</title></head><body>"
        f"<h1>{html.escape(title)}</h1><p>Source: "
        f"<a href=\"{html.escape(source['url'], quote=True)}\">"
        f"{html.escape(source['url'])}</a></p>{body}</body></html>\n"
    )
    path.write_text(output, encoding="utf-8")


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
                    date_time=(2024, 2, 26, 0, 0, 0),
                )
                normalized.compress_type = member.compress_type
                normalized.external_attr = member.external_attr
                normalized.internal_attr = member.internal_attr
                normalized.create_system = member.create_system
                normalized.flag_bits = member.flag_bits
                target.writestr(normalized, source.read(member.filename))
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def manifest_entry(path: Path, source: dict, transformation: str) -> dict:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "filename": path.name,
        "document_id": str(
            uuid5(NAMESPACE_URL, f"docenquire:{COLLECTION_NAME}:{digest}")
        ),
        "sha256": digest,
        "collection_name": COLLECTION_NAME,
        "format": path.suffix.lstrip("."),
        "size_bytes": path.stat().st_size,
        "source_title": source["title"],
        "source_publication": source.get("publication"),
        "source_url": source["url"],
        "source_format": source.get("source_format", "pdf"),
        "transformation": transformation,
    }


def build() -> None:
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    entries: list[dict] = []
    source_cache: dict[str, bytes] = {}
    with httpx.Client(follow_redirects=True, timeout=120) as client:
        for source in PDF_SOURCES + DERIVED_PDF_SOURCES:
            source_cache[source["url"]] = fetch(client, source["url"])

        for source in PDF_SOURCES:
            path = CORPUS_DIR / source["filename"]
            path.write_bytes(source_cache[source["url"]])
            entries.append(manifest_entry(path, source, "Original NIST PDF."))

        for source in DERIVED_PDF_SOURCES:
            pages = extract_pdf_pages(source_cache[source["url"]], source["title"])
            path = CORPUS_DIR / source["filename"]
            if source["format"] == "docx":
                write_docx(path, source, pages)
            elif source["format"] == "pptx":
                write_pptx(path, source, pages)
            elif source["format"] == "md":
                write_markdown(path, source, pages)
            elif source["format"] == "txt":
                write_text(path, source, pages)
            else:
                raise ValueError(f"Unsupported conversion format: {source['format']}")
            if source["format"] in {"docx", "pptx"}:
                normalize_zip_timestamps(path)
            entries.append(
                manifest_entry(path, source, source["transformation"])
            )

        xlsx_path = CORPUS_DIR / XLSX_SOURCE["filename"]
        xlsx_bytes = fetch(client, XLSX_SOURCE["url"])
        if not xlsx_bytes.startswith(b"PK"):
            raise ValueError("The NIST profile template download is not an XLSX file")
        workbook = load_workbook(io.BytesIO(xlsx_bytes), read_only=True, data_only=True)
        if not workbook.sheetnames:
            raise ValueError("The NIST profile template has no worksheets")
        workbook.close()
        xlsx_path.write_bytes(xlsx_bytes)
        xlsx_source = {**XLSX_SOURCE, "source_format": "xlsx"}
        entries.append(
            manifest_entry(xlsx_path, xlsx_source, "Original NIST XLSX template.")
        )

        for source in HTML_SOURCES:
            path = CORPUS_DIR / source["filename"]
            content = fetch(client, source["url"])
            if b"<html" not in content.lower():
                raise ValueError(f"{source['title']}: response is not HTML")
            write_html(path, source, content)
            html_source = {**source, "source_format": "html"}
            entries.append(
                manifest_entry(path, html_source, "NIST webpage saved as HTML.")
            )

    formats = {entry["format"] for entry in entries}
    if len(entries) < 15 or len(entries) > 20:
        raise ValueError(f"Expected 15-20 documents; built {len(entries)}")
    if formats != {"pdf", "docx", "pptx", "xlsx", "html", "md", "txt"}:
        raise ValueError(f"Unexpected corpus formats: {sorted(formats)}")
    MANIFEST_PATH.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"Built {len(entries)} NIST documents in {len(formats)} supported formats.")
    for format_name in sorted(formats):
        count = sum(entry["format"] == format_name for entry in entries)
        print(f"  {format_name}: {count}")


if __name__ == "__main__":
    build()
