"""Text redaction rules established in docs/project/DATA_GATE.md section 4.

Pattern order matters: handles and emails are replaced before the generic
digit-sequence rule so an email's leading digits are not double-redacted.
"""

from __future__ import annotations

import re

_URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_HANDLE_PATTERN = re.compile(r"@\w+")
_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_LONG_NUMBER_PATTERN = re.compile(r"(?<!\d)\d{10,12}(?!\d)")


def redact_text(text: str) -> str:
    text = _URL_PATTERN.sub("[URL]", text)
    text = _EMAIL_PATTERN.sub("[EMAIL]", text)
    text = _HANDLE_PATTERN.sub("[USER]", text)
    text = _LONG_NUMBER_PATTERN.sub("[NUMBER]", text)
    return text
