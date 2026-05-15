"""SenseVoice ASR adapter backed by FunASR."""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any, Callable

from agent_voice.asr.base import AsrResult


ModelFactory = Callable[..., Any]


class SenseVoiceAsr:
    """Load a local SenseVoice model and transcribe audio files."""

    def __init__(self, model_dir: str | Path, device: str = "cpu", model_factory: ModelFactory | None = None) -> None:
        """Create a SenseVoice ASR engine using a local model directory."""

        self.model_dir = Path(model_dir)
        if not self.model_dir.exists():
            raise FileNotFoundError(f"SenseVoice model directory not found: {self.model_dir}")
        factory = model_factory or self._default_model_factory
        self.model = factory(
            model=str(self.model_dir),
            vad_model=None,
            punc_model=None,
            device=device,
            disable_update=True,
        )

    def transcribe_file(self, audio_path: str | Path) -> AsrResult:
        """Transcribe an audio file path and return normalized text."""

        path = Path(audio_path)
        started = time.perf_counter()
        output = self.model.generate(input=str(path), batch_size_s=60, hotword="")
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        text = _extract_text(output)
        if not text:
            raise ValueError(f"ASR returned no text for audio file: {path}")
        return AsrResult(text=text, confidence=1.0, elapsed_ms=elapsed_ms)

    @staticmethod
    def _default_model_factory(**kwargs: Any) -> Any:
        from funasr import AutoModel

        return AutoModel(**kwargs)


def _extract_text(output: Any) -> str:
    if isinstance(output, list) and output:
        first = output[0]
        if isinstance(first, dict):
            return _clean_sensevoice_text(str(first.get("text") or ""))
        return _clean_sensevoice_text(str(first))
    if isinstance(output, dict):
        return _clean_sensevoice_text(str(output.get("text") or ""))
    return _clean_sensevoice_text(str(output or ""))


def _clean_sensevoice_text(text: str) -> str:
    """Remove SenseVoice control tags from recognized text."""

    return re.sub(r"<\|[^|]+?\|>", "", text).strip()
