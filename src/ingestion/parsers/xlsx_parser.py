import logging

from openpyxl import load_workbook

from src.ingestion.parsers.base import BaseParser, ParsedSegment

logger = logging.getLogger(__name__)


class XLSXParser(BaseParser):
    def supported_extensions(self) -> list[str]:
        return [".xlsx"]

    def parse(self, file_path: str) -> list[ParsedSegment]:
        segments = []
        wb = load_workbook(file_path, read_only=True, data_only=True)

        try:
            for sheet_name in wb.sheetnames:
                try:
                    ws = wb[sheet_name]

                    for row_idx, row in enumerate(ws.iter_rows(values_only=True)):
                        cells = [str(cell) if cell is not None else "" for cell in row]
                        row_text = " | ".join(c for c in cells if c).strip()
                        if not row_text:
                            continue

                        segments.append(
                            ParsedSegment(
                                text=row_text,
                                sheet_name=sheet_name,
                                paragraph_index=row_idx,
                                section_title=sheet_name,
                            )
                        )
                except Exception:
                    logger.warning("Failed to parse sheet '%s' in %s", sheet_name, file_path)
        finally:
            wb.close()

        return segments
