from openpyxl import load_workbook

from src.ingestion.parsers.base import BaseParser, ParsedSegment


class XLSXParser(BaseParser):
    def supported_extensions(self) -> list[str]:
        return [".xlsx"]

    def parse(self, file_path: str) -> list[ParsedSegment]:
        segments = []
        wb = load_workbook(file_path, read_only=True, data_only=True)

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            header_row: list[str] = []

            for row_idx, row in enumerate(ws.iter_rows(values_only=True)):
                cells = [str(cell) if cell is not None else "" for cell in row]
                row_text = " | ".join(c for c in cells if c).strip()
                if not row_text:
                    continue

                if row_idx == 0:
                    header_row = cells

                segments.append(
                    ParsedSegment(
                        text=row_text,
                        sheet_name=sheet_name,
                        paragraph_index=row_idx,
                        section_title=sheet_name,
                    )
                )

        wb.close()
        return segments
