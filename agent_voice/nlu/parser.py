"""Rule-based intent parser for fixed medical workstation commands."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


MIN_ASR_CONFIDENCE = 0.45


@dataclass(frozen=True)
class ParseResult:
    """Structured output from the fixed-command parser."""

    matched: bool
    text: str
    normalized_text: str
    intent: str | None
    params: dict[str, Any] = field(default_factory=dict)
    asr_confidence: float = 0.0
    parser_confidence: float = 0.0
    reason: str | None = None


class IntentParser:
    """Parse approved short medical workstation voice commands."""

    _fetch_id = re.compile(r"^(?:调取|打开|查看)患者(?P<patient_id>\d{4,32})$")
    _fetch_name = re.compile(r"^(?:调取|打开|查看)患者(?P<patient_name>[\u4e00-\u9fff]{2,8})$")
    _record_actions = {
        "开始录音": "start",
        "暂停录音": "pause",
        "继续录音": "resume",
        "关闭录音": "stop",
    }

    def parse(self, text: str, asr_confidence: float) -> ParseResult:
        """Parse ASR text into an intent and params without side effects."""

        normalized = normalize_text(text)
        if asr_confidence < MIN_ASR_CONFIDENCE:
            return ParseResult(
                matched=False,
                text=text,
                normalized_text=normalized,
                intent=None,
                asr_confidence=asr_confidence,
                reason="low_asr_confidence",
            )

        result = self._parse_fetch_patient(text, normalized, asr_confidence)
        if result:
            return result
        result = self._parse_queue_control(text, normalized, asr_confidence)
        if result:
            return result
        result = self._parse_record_control(text, normalized, asr_confidence)
        if result:
            return result
        return ParseResult(
            matched=False,
            text=text,
            normalized_text=normalized,
            intent=None,
            asr_confidence=asr_confidence,
            reason="no_rule_matched",
        )

    def _parse_fetch_patient(self, text: str, normalized: str, asr_confidence: float) -> ParseResult | None:
        match = self._fetch_id.match(normalized)
        if match:
            return ParseResult(
                matched=True,
                text=text,
                normalized_text=normalized,
                intent="fetch_patient",
                params={"patient_id": match.group("patient_id")},
                asr_confidence=asr_confidence,
                parser_confidence=0.98,
            )

        match = self._fetch_name.match(normalized)
        if match:
            return ParseResult(
                matched=True,
                text=text,
                normalized_text=normalized,
                intent="fetch_patient",
                params={"patient_name": match.group("patient_name")},
                asr_confidence=asr_confidence,
                parser_confidence=0.92,
            )
        return None

    @staticmethod
    def _parse_queue_control(text: str, normalized: str, asr_confidence: float) -> ParseResult | None:
        if normalized == "呼叫下一个患者":
            return ParseResult(
                matched=True,
                text=text,
                normalized_text=normalized,
                intent="call_next_patient",
                params={},
                asr_confidence=asr_confidence,
                parser_confidence=0.96,
            )
        return None

    def _parse_record_control(self, text: str, normalized: str, asr_confidence: float) -> ParseResult | None:
        action = self._record_actions.get(normalized)
        if action:
            return ParseResult(
                matched=True,
                text=text,
                normalized_text=normalized,
                intent="record_control",
                params={"action": action},
                asr_confidence=asr_confidence,
                parser_confidence=0.97,
            )
        return None


def normalize_text(text: str) -> str:
    """Normalize ASR text for deterministic rule matching."""

    cleaned = re.sub(r"[\s，。,.!?！？：:；;、]+", "", text)
    return cleaned.strip()
