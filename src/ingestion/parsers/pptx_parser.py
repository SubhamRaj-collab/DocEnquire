from pptx import Presentation

from src.ingestion.parsers.base import BaseParser, ParsedSegment


class PPTXParser(BaseParser):
    def supported_extensions(self) -> list[str]:
        return [".pptx"]

    def parse(self, file_path: str) -> list[ParsedSegment]:
        segments = []
        prs = Presentation(file_path)

        for slide_num, slide in enumerate(prs.slides, start=1):
            slide_title: str | None = None
            if slide.shapes.title and slide.shapes.title.text.strip():
                slide_title = slide.shapes.title.text.strip()

            for shape_idx, shape in enumerate(slide.shapes):
                if not shape.has_text_frame:
                    continue
                text = shape.text_frame.text.strip()
                if not text:
                    continue
                segments.append(
                    ParsedSegment(
                        text=text,
                        slide_number=slide_num,
                        section_title=slide_title,
                        paragraph_index=shape_idx,
                    )
                )

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

        return segments
