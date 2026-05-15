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

    _fetch_id = re.compile(
        r"^(?:帮我|请|麻烦)?"
        r"(?:(?:调取|打开|查看|查询|显示|找一下))?"
        r"(?:患者|病人)"
        r"(?P<patient_id>[0-9零〇一二三四五六七八九幺]{4,32})"
        r"(?:的?(?:病历|信息|资料|档案))?$"
    )
    _fetch_name = re.compile(
        r"^(?:帮我|请|麻烦)?"
        r"(?:(?:调取|打开|查看|查询|显示|找一下))?"
        r"(?:患者|病人)"
        r"(?P<patient_name>[\u4e00-\u9fff]{2,8})"
        r"(?:的?(?:病历|信息|资料|档案))?$"
    )
    _record_actions = {
        "开始录音": "start",
        "暂停录音": "pause",
        "继续录音": "resume",
        "关闭录音": "stop",
        "停止录音": "stop",
        "结束录音": "stop",
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
            patient_id = _normalize_spoken_digits(match.group("patient_id"))
            return ParseResult(
                matched=True,
                text=text,
                normalized_text=normalized.replace(match.group("patient_id"), patient_id, 1),
                intent="fetch_patient",
                params={"patient_id": patient_id},
                asr_confidence=asr_confidence,
                parser_confidence=0.98,
            )

        match = self._fetch_name.match(normalized)
        if match:
            patient_name = match.group("patient_name")
            if _is_spoken_digits(patient_name):
                return None
            return ParseResult(
                matched=True,
                text=text,
                normalized_text=normalized,
                intent="fetch_patient",
                params={"patient_name": patient_name},
                asr_confidence=asr_confidence,
                parser_confidence=0.92,
            )
        return None

    @staticmethod
    def _parse_queue_control(text: str, normalized: str, asr_confidence: float) -> ParseResult | None:
        if normalized in {"呼叫下一个患者", "呼叫下一位患者", "叫下一个患者", "叫下一位患者", "下一位患者"}:
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
    return _strip_command_prefix(cleaned.strip())


_SPOKEN_DIGITS = {
    "零": "0",
    "〇": "0",
    "一": "1",
    "二": "2",
    "三": "3",
    "四": "4",
    "五": "5",
    "六": "6",
    "七": "7",
    "八": "8",
    "九": "9",
    "幺": "1",
}


def _strip_command_prefix(text: str) -> str:
    """Remove wake-word residue that may be included by manual input or ASR."""

    return re.sub(r"^(?:小图小图|小兔小兔|小涂小涂)+", "", text)


def _normalize_spoken_digits(text: str) -> str:
    """Convert common spoken Chinese digits in patient identifiers."""

    return "".join(_SPOKEN_DIGITS.get(char, char) for char in text)


def _is_spoken_digits(text: str) -> bool:
    """Return whether text is made only of spoken digit characters."""

    return all(char in _SPOKEN_DIGITS for char in text)
