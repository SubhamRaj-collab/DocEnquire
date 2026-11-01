import re

EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(
    r"(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?!\w)"
)


def redact_pii(text: str) -> str:
    text = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
    return PHONE_PATTERN.sub("[REDACTED_PHONE]", text)
