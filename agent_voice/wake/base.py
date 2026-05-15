"""Wake-word detector interfaces."""

from __future__ import annotations

from typing import Protocol


class WakeDetector(Protocol):
    """Protocol implemented by wake engines such as Porcupine."""

    def accept_frame(self, pcm16_mono_frame: bytes) -> bool:
        """Return True when the configured wake word is detected."""
