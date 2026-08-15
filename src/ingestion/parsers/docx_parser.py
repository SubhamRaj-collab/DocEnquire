import logging

from docx import Document

from src.ingestion.parsers.base import BaseParser, ParsedSegment

logger = logging.getLogger(__name__)


class DOCXParser(BaseParser):
    def supported_extensions(self) -> list[str]:
        return [".docx"]

    def parse(self, file_path: str) -> list[ParsedSegment]:
        segments = []
        doc = Document(file_path)
        current_section: str | None = None

        for idx, para in enumerate(doc.paragraphs):
            text = para.text.strip()
            if not text:
                continue
            try:
                if para.style and para.style.name and para.style.name.startswith("Heading"):
                    current_section = text
            except Exception:
                pass
            segments.append(
                ParsedSegment(
                    text=text,
                    section_title=current_section,
                    paragraph_index=idx,
                )
            )

        for table_idx, table in enumerate(doc.tables):
            try:
                rows_text = []
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells]
                    rows_text.append(" | ".join(cells))
                table_text = "\n".join(rows_text)
                if table_text.strip():
                    segments.append(
                        ParsedSegment(
                            text=table_text,
                            section_title=current_section,
                            paragraph_index=len(doc.paragraphs) + table_idx,
                        )
                    )
            except Exception:
                logger.warning("Failed to parse table %d in %s", table_idx, file_path)

        return segments
