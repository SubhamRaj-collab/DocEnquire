import logging

from bs4 import BeautifulSoup

from src.ingestion.parsers.base import BaseParser, ParsedSegment

logger = logging.getLogger(__name__)

CONTENT_TAGS = [
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "li", "td", "th", "pre", "blockquote",
    "div", "section", "article", "main", "figcaption", "dt", "dd",
]

HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}

STRIP_TAGS = ["script", "style", "nav", "footer", "header", "noscript", "svg", "iframe"]


class HTMLParser(BaseParser):
    def supported_extensions(self) -> list[str]:
        return [".html", ".htm"]

    def parse(self, file_path: str) -> list[ParsedSegment]:
        with open(file_path, encoding="utf-8", errors="replace") as f:
            content = f.read()

        if not content.strip():
            return []

        try:
            soup = BeautifulSoup(content, "lxml")
        except Exception:
            soup = BeautifulSoup(content, "html.parser")

        for tag in soup(STRIP_TAGS):
            tag.decompose()

        segments = []
        current_section: str | None = None
        seen_texts: set[str] = set()

        for idx, element in enumerate(soup.find_all(CONTENT_TAGS)):
            if element.find_parent(CONTENT_TAGS):
                continue

            text = element.get_text(separator=" ", strip=True)
            if not text or text in seen_texts:
                continue
            seen_texts.add(text)

            if element.name in HEADING_TAGS:
                current_section = text

            segments.append(
                ParsedSegment(
                    text=text,
                    section_title=current_section,
                    paragraph_index=idx,
                )
            )

        if not segments:
            text = soup.get_text(separator="\n", strip=True)
            if text:
                segments.append(ParsedSegment(text=text, paragraph_index=0))

        return segments
