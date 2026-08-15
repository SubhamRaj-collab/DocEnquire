from markdown_it import MarkdownIt

from src.ingestion.parsers.base import BaseParser, ParsedSegment


class MarkdownParser(BaseParser):
    def supported_extensions(self) -> list[str]:
        return [".md", ".markdown"]

    def parse(self, file_path: str) -> list[ParsedSegment]:
        with open(file_path, encoding="utf-8", errors="replace") as f:
            content = f.read()

        md = MarkdownIt()
        tokens = md.parse(content)

        segments = []
        current_section: str | None = None
        idx = 0

        i = 0
        while i < len(tokens):
            token = tokens[i]

            if token.type == "heading_open":
                if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                    heading_text = tokens[i + 1].content.strip()
                    current_section = heading_text
                    segments.append(
                        ParsedSegment(
                            text=heading_text,
                            section_title=current_section,
                            paragraph_index=idx,
                        )
                    )
                    idx += 1
                    i += 3
                    continue

            if token.type == "paragraph_open":
                if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                    text = tokens[i + 1].content.strip()
                    if text:
                        segments.append(
                            ParsedSegment(
                                text=text,
                                section_title=current_section,
                                paragraph_index=idx,
                            )
                        )
                        idx += 1
                    i += 3
                    continue

            if token.type == "fence" or token.type == "code_block":
                text = token.content.strip()
                if text:
                    segments.append(
                        ParsedSegment(
                            text=text,
                            section_title=current_section,
                            paragraph_index=idx,
                            extra_metadata={"type": "code"},
                        )
                    )
                    idx += 1

            i += 1

        return segments
