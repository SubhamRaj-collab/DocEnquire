from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ParsedSegment:
    text: str
    page_number: int | None = None
    section_title: str | None = None
    paragraph_index: int | None = None
    sheet_name: str | None = None
    slide_number: int | None = None
    extra_metadata: dict = field(default_factory=dict)


class BaseParser(ABC):
    @abstractmethod
    def supported_extensions(self) -> list[str]: ...

    @abstractmethod
    def parse(self, file_path: str) -> list[ParsedSegment]: ...

    def can_handle(self, file_path: str) -> bool:
        from pathlib import Path

        return Path(file_path).suffix.lower() in self.supported_extensions()
