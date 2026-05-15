"""Reusable command processing pipeline for CLI and desktop UI."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone

from agent_voice.nlu.parser import IntentParser
from agent_voice.transport.http_client import BusinessClient, BusinessResponse
from agent_voice.transport.schema import build_command_payload, generate_request_id


@dataclass(frozen=True)
class CommandOutcome:
    """User-facing result of processing one voice command text."""

    status: str
    message: str
    intent: str | None = None
    feedback: str | None = None
    request_id: str | None = None


class CommandPipeline:
    """Parse recognized text and deliver matched commands to the business endpoint."""

    def __init__(self, device_id: str, app_version: str, client: BusinessClient, parser: IntentParser | None = None) -> None:
        """Create a command pipeline from stable app settings and a transport client."""

        self.device_id = device_id
        self.app_version = app_version
        self.client = client
        self.parser = parser or IntentParser()

    def process_text(self, text: str, asr_confidence: float = 1.0) -> CommandOutcome:
        """Process one ASR text value and return a safe UI/CLI outcome."""

        started = time.perf_counter()
        parse_result = self.parser.parse(text, asr_confidence=asr_confidence)
        parse_ms = int((time.perf_counter() - started) * 1000)
        if not parse_result.matched:
            return CommandOutcome(status="no_match", message=parse_result.reason or "no_rule_matched")

        request_id = generate_request_id(now=datetime.now(timezone.utc))
        payload = build_command_payload(
            parse_result=parse_result,
            device_id=self.device_id,
            app_version=self.app_version,
            request_id=request_id,
            now=datetime.now(timezone.utc),
            duration_ms={"recording": 0, "asr": 0, "parse": parse_ms},
        )
        try:
            response: BusinessResponse = self.client.send_command(payload)
        except Exception as exc:
            return CommandOutcome(status="error", message=str(exc), intent=parse_result.intent, request_id=request_id)

        status = "sent" if response.accepted else "rejected"
        return CommandOutcome(
            status=status,
            message=response.message,
            intent=parse_result.intent,
            feedback=response.feedback,
            request_id=request_id,
        )
