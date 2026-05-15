"""Live microphone wake-word and ASR command loop."""

from __future__ import annotations

import json
import tempfile
from time import monotonic
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from agent_voice.asr.sensevoice import SenseVoiceAsr
from agent_voice.audio.recorder import EnergyCommandRecorder, write_wav
from agent_voice.config import AppConfig
from agent_voice.pipeline import CommandPipeline
from agent_voice.voice_status import DEFAULT_STATUS_PATH, read_voice_status, write_voice_status
from agent_voice.wake.sherpa_onnx_engine import SherpaOnnxWakeDetector


class VoiceLoop:
    """Run live wake detection, command recording, ASR, and business delivery."""

    def __init__(self, config: AppConfig, pipeline: CommandPipeline) -> None:
        """Create the live voice command loop from app config."""

        self.config = config
        self.pipeline = pipeline
        self.detector = SherpaOnnxWakeDetector(
            model_dir=config.wake.model_dir,
            keywords_file=config.wake.keywords_file,
            cooldown_ms=config.wake.cooldown_ms,
            sample_rate=config.audio.sample_rate,
            keywords_threshold=max(0.05, 1.0 - config.wake.sensitivity),
        )
        self.recorder = EnergyCommandRecorder(
            sample_rate=config.audio.sample_rate,
            frame_ms=config.audio.frame_ms,
            min_duration_ms=config.recorder.min_duration_ms,
            max_duration_ms=config.recorder.max_duration_ms,
            end_silence_ms=config.recorder.end_silence_ms,
            energy_threshold=config.recorder.energy_threshold,
        )
        self.asr = SenseVoiceAsr(model_dir=config.asr.model_dir, device=config.asr.device)
        self.status_path = DEFAULT_STATUS_PATH
        self._last_mic_status_at = 0.0

    def run_forever(self) -> int:
        """Start microphone listening until interrupted."""

        import sounddevice as sd

        frame_samples = self.recorder.frame_samples
        print("Agent Voice listening. Say: 小图小图", flush=True)
        try:
            with sd.InputStream(
                samplerate=self.config.audio.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=frame_samples,
                device=self.config.audio.device_index,
            ) as stream:
                self._run_stream_loop(stream, frame_samples)
        except KeyboardInterrupt:
            print("Agent Voice stopped.", flush=True)
            return 0
        return 0

    def _run_stream_loop(self, stream: Any, frame_samples: int) -> None:
        while True:
            frame = _read_frame(stream, frame_samples)
            self._maybe_write_microphone_level(frame)
            keyword = self.detector.accept_samples(frame, sample_rate=self.config.audio.sample_rate)
            if keyword:
                print(json.dumps({"event": "wake_detected", "keyword": keyword}, ensure_ascii=False), flush=True)
                write_voice_status(self.status_path, event="wake_detected", keyword=keyword)
                self._record_transcribe_and_send(stream)

    def _maybe_write_microphone_level(self, frame: np.ndarray) -> None:
        now = monotonic()
        if now - self._last_mic_status_at < 1.0:
            return
        self._last_mic_status_at = now
        status = read_voice_status(self.status_path)
        if not _should_write_mic_level(status, now=datetime.now(timezone.utc), hold_seconds=6):
            return
        payload = _microphone_status_payload(frame, threshold=self.config.recorder.energy_threshold)
        write_voice_status(self.status_path, **payload)

    def _record_transcribe_and_send(self, stream: Any) -> None:
        samples = self.recorder.collect_from_reader(lambda: _read_frame(stream, self.recorder.frame_samples))
        if samples.size == 0:
            print(json.dumps({"event": "empty_recording"}, ensure_ascii=False), flush=True)
            write_voice_status(self.status_path, event="empty_recording")
            return
        write_voice_status(self.status_path, event="recording_complete", samples=int(samples.size))
        wav_path = _write_temp_wav(samples, self.config.audio.sample_rate)
        try:
            asr_result = self.asr.transcribe_file(wav_path)
        finally:
            wav_path.unlink(missing_ok=True)
        write_voice_status(self.status_path, event="asr_result", asr_text=asr_result.text, asr_elapsed_ms=asr_result.elapsed_ms)
        outcome = self.pipeline.process_text(asr_result.text, asr_confidence=asr_result.confidence)
        write_voice_status(
            self.status_path,
            event="command_result",
            asr_text=asr_result.text,
            asr_elapsed_ms=asr_result.elapsed_ms,
            outcome_status=outcome.status,
            outcome_message=outcome.message,
            intent=outcome.intent,
        )
        print(
            json.dumps({"event": "command_result", "asr": asr_result.__dict__, "outcome": outcome.__dict__}, ensure_ascii=False),
            flush=True,
        )


def list_audio_devices() -> list[dict[str, Any]]:
    """Return available audio devices with indices and channel counts."""

    import sounddevice as sd

    devices = sd.query_devices()
    result = []
    for index, device in enumerate(devices):
        result.append(
            {
                "index": index,
                "name": device.get("name"),
                "max_input_channels": int(device.get("max_input_channels") or 0),
                "max_output_channels": int(device.get("max_output_channels") or 0),
            }
        )
    return result


def _read_frame(stream: Any, frame_samples: int) -> np.ndarray:
    data, overflowed = stream.read(frame_samples)
    if overflowed:
        print(json.dumps({"event": "audio_overflow"}, ensure_ascii=False), flush=True)
    array = np.asarray(data, dtype=np.float32)
    if array.ndim == 2:
        array = array[:, 0]
    return array.reshape(-1)


def _microphone_status_payload(frame: np.ndarray, threshold: float) -> dict[str, Any]:
    """Build the widget status payload for current microphone input level."""

    if frame.size == 0:
        level = 0.0
    else:
        level = float(np.sqrt(np.mean(np.square(frame, dtype=np.float32))))
    return {
        "event": "mic_level",
        "active": level >= threshold,
        "level": round(level, 4),
        "level_percent": min(100, int(round(level * 1000))),
    }


def _should_write_mic_level(status: dict[str, Any], now: datetime, hold_seconds: int) -> bool:
    """Return whether a microphone level update may replace the current status."""

    held_events = {
        "wake_detected",
        "recording_complete",
        "asr_result",
        "command_result",
        "empty_recording",
        "mic_recording",
        "mic_asr_result",
        "mic_asr_empty",
    }
    if status.get("event") not in held_events:
        return True
    updated_at = status.get("updated_at")
    if not isinstance(updated_at, str):
        return True
    try:
        updated = datetime.fromisoformat(updated_at)
    except ValueError:
        return True
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    return (now - updated).total_seconds() >= hold_seconds


def _write_temp_wav(samples: np.ndarray, sample_rate: int) -> Path:
    handle = tempfile.NamedTemporaryFile(prefix="agent_voice_", suffix=".wav", delete=False)
    handle.close()
    path = Path(handle.name)
    write_wav(path, samples, sample_rate)
    return path
