"""Configuration loading for the desktop voice assistant."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


WAKE_SENSITIVITY_MIN = 0.1
WAKE_SENSITIVITY_MAX = 0.95
DEFAULT_WAKE_SENSITIVITY = 0.9


@dataclass(frozen=True)
class AppSection:
    """Application identity and logging settings."""

    device_id: str
    app_version: str
    log_level: str = "INFO"
    log_retention_days: int = 7


@dataclass(frozen=True)
class TransportSection:
    """HTTP transport settings for business command delivery."""

    base_url: str
    command_path: str = "/api/voice/commands"
    timeout_ms: int = 3000
    retry: int = 1
    hmac_secret_env: str | None = "AGENT_VOICE_HMAC_SECRET"


@dataclass(frozen=True)
class AudioSection:
    """Microphone capture settings."""

    sample_rate: int = 16000
    channels: int = 1
    device_index: int | None = None
    frame_ms: int = 30


@dataclass(frozen=True)
class WakeSection:
    """Wake-word detector settings."""

    engine: str = "sherpa_onnx"
    model_dir: str = "models/wake/sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01"
    keywords_file: str = "models/wake/keywords.txt"
    sensitivity: float = DEFAULT_WAKE_SENSITIVITY
    cooldown_ms: int = 1500


@dataclass(frozen=True)
class AsrSection:
    """ASR model settings."""

    engine: str = "sensevoice"
    model_dir: str = "models/asr/SenseVoiceSmall"
    mode: str = "warm"
    device: str = "cpu"
    num_threads: int = 4
    timeout_ms: int = 8000


@dataclass(frozen=True)
class RecorderSection:
    """Command recorder endpoint settings."""

    min_duration_ms: int = 800
    max_duration_ms: int = 6000
    end_silence_ms: int = 900
    pre_roll_ms: int = 300
    energy_threshold: float = 0.008


@dataclass(frozen=True)
class AppConfig:
    """Validated subset of the JSON configuration used by the MVP pipeline."""

    app: AppSection
    transport: TransportSection
    audio: AudioSection
    wake: WakeSection
    asr: AsrSection
    recorder: RecorderSection

    @classmethod
    def load(cls, path: str | Path) -> "AppConfig":
        """Load application config from a UTF-8 JSON file."""

        config_path = Path(path)
        try:
            raw = json.loads(config_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"Config file not found: {config_path}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON config: {config_path}") from exc
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "AppConfig":
        """Build a validated config object from decoded JSON data."""

        app = raw.get("app") or {}
        transport = raw.get("transport") or {}
        audio = raw.get("audio") or {}
        wake = raw.get("wake") or {}
        asr = raw.get("asr") or {}
        recorder = raw.get("recorder") or {}
        device_id = str(app.get("device_id") or "").strip()
        app_version = str(app.get("app_version") or "0.1.0").strip()
        base_url = str(transport.get("base_url") or "").strip()

        if not device_id:
            raise ValueError("app.device_id is required")
        if not app_version:
            raise ValueError("app.app_version is required")
        if not base_url:
            raise ValueError("transport.base_url is required")

        return cls(
            app=_build_app_section(app, device_id, app_version),
            transport=_build_transport_section(transport, base_url),
            audio=_build_audio_section(audio),
            wake=_build_wake_section(wake),
            asr=_build_asr_section(asr),
            recorder=_build_recorder_section(recorder),
        )


def _build_app_section(raw: dict[str, Any], device_id: str, app_version: str) -> AppSection:
    return AppSection(
        device_id=device_id,
        app_version=app_version,
        log_level=str(raw.get("log_level") or "INFO"),
        log_retention_days=int(raw.get("log_retention_days") or 7),
    )


def _build_transport_section(raw: dict[str, Any], base_url: str) -> TransportSection:
    return TransportSection(
        base_url=base_url,
        command_path=str(raw.get("command_path") or "/api/voice/commands"),
        timeout_ms=int(raw.get("timeout_ms") or 3000),
        retry=int(raw.get("retry") or 1),
        hmac_secret_env=raw.get("hmac_secret_env"),
    )


def _build_audio_section(raw: dict[str, Any]) -> AudioSection:
    return AudioSection(
        sample_rate=int(raw.get("sample_rate") or 16000),
        channels=int(raw.get("channels") or 1),
        device_index=raw.get("device_index"),
        frame_ms=int(raw.get("frame_ms") or 30),
    )


def _build_wake_section(raw: dict[str, Any]) -> WakeSection:
    return WakeSection(
        engine=str(raw.get("engine") or "sherpa_onnx"),
        model_dir=str(raw.get("model_dir") or "models/wake/sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01"),
        keywords_file=str(raw.get("keywords_file") or "models/wake/keywords.txt"),
        sensitivity=_clamp_float(
            raw.get("sensitivity"),
            default=DEFAULT_WAKE_SENSITIVITY,
            minimum=WAKE_SENSITIVITY_MIN,
            maximum=WAKE_SENSITIVITY_MAX,
        ),
        cooldown_ms=int(raw.get("cooldown_ms") or 1500),
    )


def _build_asr_section(raw: dict[str, Any]) -> AsrSection:
    return AsrSection(
        engine=str(raw.get("engine") or "sensevoice"),
        model_dir=str(raw.get("model_dir") or "models/asr/SenseVoiceSmall"),
        mode=str(raw.get("mode") or "warm"),
        device=str(raw.get("device") or "cpu"),
        num_threads=int(raw.get("num_threads") or 4),
        timeout_ms=int(raw.get("timeout_ms") or 8000),
    )


def _build_recorder_section(raw: dict[str, Any]) -> RecorderSection:
    return RecorderSection(
        min_duration_ms=int(raw.get("min_duration_ms") or 800),
        max_duration_ms=int(raw.get("max_duration_ms") or 6000),
        end_silence_ms=int(raw.get("end_silence_ms") or 900),
        pre_roll_ms=int(raw.get("pre_roll_ms") or 300),
        energy_threshold=float(raw.get("energy_threshold") or 0.008),
    )


def _clamp_float(value: Any, *, default: float, minimum: float, maximum: float) -> float:
    if value is None:
        number = default
    else:
        number = float(value)
    return min(maximum, max(minimum, number))
