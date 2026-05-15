"""Command recording utilities using simple energy-based endpointing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import soundfile as sf


FrameReader = Callable[[], np.ndarray]


@dataclass(frozen=True)
class EnergyCommandRecorder:
    """Collect microphone frames until speech ends or max duration is reached."""

    sample_rate: int
    frame_ms: int
    min_duration_ms: int
    max_duration_ms: int
    end_silence_ms: int
    energy_threshold: float = 0.008

    @property
    def frame_samples(self) -> int:
        """Return the number of samples in one recording frame."""

        return int(self.sample_rate * self.frame_ms / 1000)

    def collect_from_reader(self, read_frame: FrameReader) -> np.ndarray:
        """Read frames until endpoint criteria are met and return mono float32 samples."""

        frames: list[np.ndarray] = []
        elapsed_ms = 0
        trailing_silence_ms = 0

        while elapsed_ms < self.max_duration_ms:
            frame = _to_mono_float32(read_frame())
            frames.append(frame)
            elapsed_ms += self.frame_ms

            if _rms(frame) < self.energy_threshold:
                trailing_silence_ms += self.frame_ms
            else:
                trailing_silence_ms = 0

            if elapsed_ms >= self.min_duration_ms and trailing_silence_ms >= self.end_silence_ms:
                break

        if not frames:
            return np.array([], dtype=np.float32)
        return np.concatenate(frames).astype(np.float32, copy=False)


def write_wav(path: str | Path, samples: np.ndarray, sample_rate: int) -> None:
    """Write mono float samples as a WAV file."""

    sf.write(str(path), _to_mono_float32(samples), sample_rate)


def _to_mono_float32(frame: np.ndarray) -> np.ndarray:
    array = np.asarray(frame, dtype=np.float32)
    if array.ndim == 2:
        array = array[:, 0]
    return array.reshape(-1)


def _rms(frame: np.ndarray) -> float:
    if frame.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(frame))))
