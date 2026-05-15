"""Microphone recording helpers for ASR diagnostics."""

from __future__ import annotations

from typing import Callable

import numpy as np


FrameReader = Callable[[], np.ndarray]


def record_microphone_seconds(sample_rate: int, frame_ms: int, seconds: float, device_index: int | None) -> np.ndarray:
    """Record a fixed duration from a microphone and return mono float32 samples."""

    import sounddevice as sd

    frame_samples = int(sample_rate * frame_ms / 1000)
    frame_count = max(1, int(round(seconds * 1000 / frame_ms)))
    with sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
        blocksize=frame_samples,
        device=device_index,
    ) as stream:
        return collect_fixed_duration(lambda: _read_frame(stream, frame_samples), frame_count=frame_count)


def collect_fixed_duration(read_frame: FrameReader, frame_count: int) -> np.ndarray:
    """Collect a fixed number of audio frames from a frame reader."""

    frames = [_to_mono_float32(read_frame()) for _ in range(max(0, frame_count))]
    if not frames:
        return np.array([], dtype=np.float32)
    return np.concatenate(frames).astype(np.float32, copy=False)


def _read_frame(stream: object, frame_samples: int) -> np.ndarray:
    data, _overflowed = stream.read(frame_samples)
    return _to_mono_float32(np.asarray(data, dtype=np.float32))


def _to_mono_float32(frame: np.ndarray) -> np.ndarray:
    array = np.asarray(frame, dtype=np.float32)
    if array.ndim == 2:
        array = array[:, 0]
    return array.reshape(-1)
