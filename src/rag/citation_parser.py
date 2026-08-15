import re
from dataclasses import dataclass


@dataclass
class Citation:
    source_label: str
    document_id: str
    filename: str
    page_number: int | None = None
    section_title: str | None = None
    slide_number: int | None = None
    sheet_name: str | None = None
    chunk_text: str = ""
    relevance_score: float | None = None


SOURCE_PATTERN = re.compile(r"\[SOURCE_(\d+)\]")


class CitationParser:
    def parse(
        self,
        raw_response: str,
        source_map: list[dict],
    ) -> tuple[str, list[Citation]]:
        parts = re.split(r"\nSOURCES:\s*\n?", raw_response, maxsplit=1)
        answer_text = parts[0]
        if answer_text.startswith("ANSWER:"):
            answer_text = answer_text[7:]
        answer_text = answer_text.strip()

        cited_indices = {int(m) for m in SOURCE_PATTERN.findall(answer_text)}

        source_lookup = {s["source_index"]: s for s in source_map}
        citations: list[Citation] = []

        for idx in sorted(cited_indices):
            if idx in source_lookup:
                src = source_lookup[idx]
                citations.append(
                    Citation(
                        source_label=src["source_label"],
                        document_id=src["document_id"],
                        filename=src.get("filename", ""),
                        page_number=src.get("page_number"),
                        section_title=src.get("section_title"),
                        slide_number=src.get("slide_number"),
                        sheet_name=src.get("sheet_name"),
                        chunk_text=src.get("chunk_text", ""),
                        relevance_score=src.get("relevance_score"),
                    )
                )

        return answer_text, citations
