from bs4 import BeautifulSoup

from src.ingestion.parsers.base import BaseParser, ParsedSegment


class HTMLParser(BaseParser):
    def supported_extensions(self) -> list[str]:
        return [".html", ".htm"]

    def parse(self, file_path: str) -> list[ParsedSegment]:
        with open(file_path, encoding="utf-8", errors="replace") as f:
            content = f.read()

        soup = BeautifulSoup(content, "lxml")

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        segments = []
        current_section: str | None = None
        heading_tags = {"h1", "h2", "h3", "h4", "h5", "h6"}

        for idx, element in enumerate(soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "pre", "blockquote"])):
            text = element.get_text(separator=" ", strip=True)
            if not text:
                continue

            if element.name in heading_tags:
                current_section = text

            segments.append(
                ParsedSegment(
                    text=text,
                    section_title=current_section,
                    paragraph_index=idx,
                )
            )

        return segments
