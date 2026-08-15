from markdown_it import MarkdownIt

from src.ingestion.parsers.base import BaseParser, ParsedSegment


class MarkdownParser(BaseParser):
    def supported_extensions(self) -> list[str]:
        return [".md", ".markdown"]

    def parse(self, file_path: str) -> list[ParsedSegment]:
        with open(file_path, encoding="utf-8", errors="replace") as f:
            content = f.read()

        if not content.strip():
            return []

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
                continue

            if token.type == "bullet_list_open" or token.type == "ordered_list_open":
                list_items = []
                i += 1
                while i < len(tokens) and token.type not in ("bullet_list_close", "ordered_list_close"):
                    token = tokens[i]
                    if token.type == "inline":
                        item_text = token.content.strip()
                        if item_text:
                            list_items.append(f"- {item_text}")
                    i += 1
                if list_items:
                    segments.append(
                        ParsedSegment(
                            text="\n".join(list_items),
                            section_title=current_section,
                            paragraph_index=idx,
                        )
                    )
                    idx += 1
                continue

            if token.type == "blockquote_open":
                quote_parts = []
                i += 1
                while i < len(tokens) and tokens[i].type != "blockquote_close":
                    if tokens[i].type == "inline":
                        quote_parts.append(tokens[i].content.strip())
                    i += 1
                if quote_parts:
                    segments.append(
                        ParsedSegment(
                            text="\n".join(quote_parts),
                            section_title=current_section,
                            paragraph_index=idx,
                        )
                    )
                    idx += 1
                i += 1
                continue

            if token.type == "html_block":
                text = token.content.strip()
                if text:
                    segments.append(
                        ParsedSegment(
                            text=text,
                            section_title=current_section,
                            paragraph_index=idx,
                        )
                    )
                    idx += 1

            i += 1

        if not segments and content.strip():
            segments.append(
                ParsedSegment(text=content.strip(), paragraph_index=0)
            )

        return segments
