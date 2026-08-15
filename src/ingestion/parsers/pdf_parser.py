import fitz

from src.ingestion.parsers.base import BaseParser, ParsedSegment


class PDFParser(BaseParser):
    def supported_extensions(self) -> list[str]:
        return [".pdf"]

    def parse(self, file_path: str) -> list[ParsedSegment]:
        segments = []
        doc = fitz.open(file_path)
        try:
            for page_num, page in enumerate(doc, start=1):
                blocks = page.get_text("dict")["blocks"]
                current_section: str | None = None
                for block_idx, block in enumerate(blocks):
                    if block["type"] != 0:
                        continue
                    lines_text = []
                    max_font_size = 0.0
                    for line in block["lines"]:
                        for span in line["spans"]:
                            lines_text.append(span["text"])
                            max_font_size = max(max_font_size, span["size"])
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
