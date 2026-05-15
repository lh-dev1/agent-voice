"""Privacy filters for log-safe text rendering."""

from __future__ import annotations

import re


_PATIENT_ID = re.compile(r"患者(?P<id>\d{4,32})")
_PATIENT_NAME = re.compile(r"患者(?P<name>[\u4e00-\u9fff]{2,8})")
_SECRET = re.compile(r"(?P<key>X-Voice-Signature|token|secret|access_key)=([^,\s]+)", re.IGNORECASE)


def mask_sensitive_text(text: str) -> str:
    """Mask patient identifiers, patient names, and secret-like values in log text."""

    masked = _SECRET.sub(lambda match: f"{match.group('key')}=***", text)
    masked = _PATIENT_ID.sub(lambda match: "患者" + "*" * len(match.group("id")), masked)
    masked = _PATIENT_NAME.sub(lambda match: "患者" + "*" * len(match.group("name")), masked)
    return masked
