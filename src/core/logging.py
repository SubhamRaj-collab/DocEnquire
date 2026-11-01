import json
import logging
import sys
from datetime import UTC, datetime

from src.core.config import get_settings
from src.core.request_context import request_id_var


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": request_id_var.get(),
            "message": record.getMessage(),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=True)


def setup_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        stream=sys.stdout,
        force=True,
    )
    for handler in logging.getLogger().handlers:
        handler.setFormatter(StructuredFormatter())
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
