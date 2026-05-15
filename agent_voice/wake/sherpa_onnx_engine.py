"""sherpa-onnx keyword spotting adapter."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

import numpy as np


SpotterFactory = Callable[..., Any]


class SherpaOnnxWakeDetector:
    """Detect configured wake keywords from streaming mono audio samples."""

    def __init__(
        self,
        model_dir: str | Path,
        keywords_file: str | Path,
        spotter_factory: SpotterFactory | None = None,
        cooldown_ms: int = 1500,
        num_threads: int = 2,
        sample_rate: int = 16000,
        keywords_score: float = 1.0,
        keywords_threshold: float = 0.25,
        provider: str = "cpu",
    ) -> None:
        """Create a sherpa-onnx wake detector from local model files."""

        self.model_dir = Path(model_dir)
        self.keywords_file = Path(keywords_file)
        self.cooldown_ms = cooldown_ms
        self.last_detected_ms = -cooldown_ms
        factory = spotter_factory or _default_spotter_factory
        self.spotter = factory(
            tokens=str(self.model_dir / "tokens.txt"),
            encoder=str(self.model_dir / "encoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx"),
            decoder=str(self.model_dir / "decoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx"),
            joiner=str(self.model_dir / "joiner-epoch-12-avg-2-chunk-16-left-64.int8.onnx"),
            keywords_file=str(self.keywords_file),
            num_threads=num_threads,
            sample_rate=sample_rate,
            keywords_score=keywords_score,
            keywords_threshold=keywords_threshold,
            provider=provider,
        )
        self.stream = self.spotter.create_stream()

    def accept_samples(self, samples: np.ndarray, sample_rate: int, now_ms: int | None = None) -> str | None:
        """Feed audio samples and return the keyword text when detected."""

        current_ms = now_ms if now_ms is not None else int(time.monotonic() * 1000)
        mono = np.asarray(samples, dtype=np.float32).reshape(-1)
        self.stream.accept_waveform(sample_rate, mono)
        while self.spotter.is_ready(self.stream):
            self.spotter.decode_stream(self.stream)

        keyword = self.spotter.get_result(self.stream)
        if not keyword:
            return None
        self.spotter.reset_stream(self.stream)
        if current_ms - self.last_detected_ms < self.cooldown_ms:
            return None
        self.last_detected_ms = current_ms
        return keyword


def _default_spotter_factory(**kwargs: Any) -> Any:
    import sherpa_onnx

    return sherpa_onnx.KeywordSpotter(**kwargs)
