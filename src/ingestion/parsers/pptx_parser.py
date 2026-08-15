import logging

from pptx import Presentation

from src.ingestion.parsers.base import BaseParser, ParsedSegment

logger = logging.getLogger(__name__)


class PPTXParser(BaseParser):
    def supported_extensions(self) -> list[str]:
        return [".pptx"]

    def parse(self, file_path: str) -> list[ParsedSegment]:
        segments = []
        prs = Presentation(file_path)

        for slide_num, slide in enumerate(prs.slides, start=1):
            slide_title: str | None = None
            try:
                if slide.shapes.title and slide.shapes.title.text.strip():
                    slide_title = slide.shapes.title.text.strip()
            except Exception:
                pass

            for shape_idx, shape in enumerate(slide.shapes):
                try:
                    if shape.has_text_frame:
                        text = shape.text_frame.text.strip()
                        if text:
                            segments.append(
                                ParsedSegment(
                                    text=text,
                                    slide_number=slide_num,
                                    section_title=slide_title,
                                    paragraph_index=shape_idx,
                                )
                            )
                    elif shape.has_table:
                        rows_text = []
                        for row in shape.table.rows:
                            cells = [cell.text.strip() for cell in row.cells]
                            rows_text.append(" | ".join(c for c in cells if c))
                        table_text = "\n".join(r for r in rows_text if r)
                        if table_text:
                            segments.append(
                                ParsedSegment(
                                    text=table_text,
                                    slide_number=slide_num,
                                    section_title=slide_title,
                                    paragraph_index=shape_idx,
                                )
                            )
                except Exception:
                    logger.warning("Failed to parse shape %d on slide %d", shape_idx, slide_num)

            try:
                if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                    notes = slide.notes_slide.notes_text_frame.text.strip()
                    if notes:
                        segments.append(
                            ParsedSegment(
                                text=notes,
                                slide_number=slide_num,
                                section_title=slide_title,
                                extra_metadata={"type": "speaker_notes"},
                            )
                        )
            except Exception:
                pass

        return segments
