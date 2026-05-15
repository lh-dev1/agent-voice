"""ASR interface definitions used by concrete offline engines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AsrResult:
    """Text and confidence returned by an ASR engine."""

    text: str
    confidence: float
    elapsed_ms: int


class AsrEngine(Protocol):
    """Protocol implemented by offline ASR engines such as SenseVoice."""

    def transcribe(self, pcm16_mono: bytes, sample_rate: int) -> AsrResult:
        """Transcribe 16-bit mono PCM bytes to text."""
