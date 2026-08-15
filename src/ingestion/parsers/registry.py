from pathlib import Path

from src.core.exceptions import UnsupportedFormatError
from src.ingestion.parsers.base import BaseParser


class ParserRegistry:
    def __init__(self) -> None:
        self._parsers: dict[str, BaseParser] = {}

    def register(self, parser: BaseParser) -> None:
        for ext in parser.supported_extensions():
            self._parsers[ext.lower()] = parser

    def get_parser(self, file_path: str) -> BaseParser:
        ext = Path(file_path).suffix.lower()
        if ext not in self._parsers:
            raise UnsupportedFormatError(f"No parser registered for '{ext}'")
        return self._parsers[ext]

    def supported_extensions(self) -> list[str]:
        return list(self._parsers.keys())

    def register_defaults(self) -> None:
        from src.ingestion.parsers.docx_parser import DOCXParser
        from src.ingestion.parsers.html_parser import HTMLParser
        from src.ingestion.parsers.markdown_parser import MarkdownParser
        from src.ingestion.parsers.pdf_parser import PDFParser
        from src.ingestion.parsers.pptx_parser import PPTXParser
        from src.ingestion.parsers.text_parser import TextParser
        from src.ingestion.parsers.xlsx_parser import XLSXParser

        for parser_cls in [
            PDFParser,
            DOCXParser,
            PPTXParser,
            XLSXParser,
            HTMLParser,
            MarkdownParser,
            TextParser,
        ]:
            self.register(parser_cls())
