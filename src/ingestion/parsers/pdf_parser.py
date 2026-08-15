import logging

import fitz

from src.ingestion.parsers.base import BaseParser, ParsedSegment

logger = logging.getLogger(__name__)


class PDFParser(BaseParser):
    def supported_extensions(self) -> list[str]:
        return [".pdf"]

    def parse(self, file_path: str) -> list[ParsedSegment]:
        segments = []
        doc = fitz.open(file_path)
        try:
            for page_num, page in enumerate(doc, start=1):
                try:
                    blocks = page.get_text("dict")["blocks"]
                except Exception:
                    page_text = page.get_text().strip()
                    if page_text:
                        segments.append(
                            ParsedSegment(text=page_text, page_number=page_num)
                        )
                    continue

                current_section: str | None = None
                for block_idx, block in enumerate(blocks):
                    if block["type"] != 0:
                        continue
                    lines_text = []
                    max_font_size = 0.0
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            lines_text.append(span.get("text", ""))
                            max_font_size = max(max_font_size, span.get("size", 0.0))
                    text = " ".join(lines_text).strip()
                    if not text:
                        continue
                    if max_font_size >= 14.0 and len(text) < 200:
                        current_section = text
                    segments.append(
                        ParsedSegment(
                            text=text,
                            page_number=page_num,
                            section_title=current_section,
                            paragraph_index=block_idx,
                        )
                    )
        finally:
            doc.close()
        return segments
