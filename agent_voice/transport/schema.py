"""Schema builders for business command requests."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from agent_voice.nlu.parser import ParseResult


def generate_request_id(now: datetime, suffix: str | None = None) -> str:
    """Generate an idempotency key with a sortable timestamp prefix."""

    actual_suffix = suffix or uuid.uuid4().hex[:6]
    return f"{now.strftime('%Y%m%d-%H%M%S')}-{actual_suffix}"


def build_command_payload(
    parse_result: ParseResult,
    device_id: str,
    app_version: str,
    request_id: str,
    now: datetime,
    duration_ms: dict[str, int],
) -> dict[str, Any]:
    """Build the JSON-serializable command payload sent to the business system."""

    if not parse_result.matched or not parse_result.intent:
        raise ValueError("Only matched parse results can be sent as business commands")
    if not device_id:
        raise ValueError("device_id is required")
    if not request_id:
        raise ValueError("request_id is required")

    return {
        "version": "1.0",
        "request_id": request_id,
        "timestamp": now.isoformat(),
        "device_id": device_id,
        "source": "desktop_voice_widget",
        "event_type": "command",
        "text": parse_result.text,
        "normalized_text": parse_result.normalized_text,
        "asr_confidence": parse_result.asr_confidence,
        "parser_confidence": parse_result.parser_confidence,
        "intent": parse_result.intent,
        "params": parse_result.params,
        "duration_ms": {
            "recording": int(duration_ms.get("recording", 0)),
            "asr": int(duration_ms.get("asr", 0)),
            "parse": int(duration_ms.get("parse", 0)),
        },
        "agent_version": app_version,
    }
