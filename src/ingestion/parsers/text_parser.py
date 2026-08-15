import chardet

from src.ingestion.parsers.base import BaseParser, ParsedSegment


class TextParser(BaseParser):
    def supported_extensions(self) -> list[str]:
        return [".txt"]

    def parse(self, file_path: str) -> list[ParsedSegment]:
        with open(file_path, "rb") as f:
            raw = f.read()

        detected = chardet.detect(raw)
        encoding = detected.get("encoding") or "utf-8"
        content = raw.decode(encoding, errors="replace")

        segments = []
        paragraphs = content.split("\n\n")

        for idx, para in enumerate(paragraphs):
            text = para.strip()
            if not text:
                continue
            segments.append(
                ParsedSegment(
                    text=text,
                    paragraph_index=idx,
                )
            )

        return segments
