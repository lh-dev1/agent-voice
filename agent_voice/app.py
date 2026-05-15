"""Command-line entry point for the MVP command pipeline."""

from __future__ import annotations

import argparse
import json
import os
import sys

from agent_voice.config import AppConfig
from agent_voice.mock_server import BusinessMockServer
from agent_voice.pipeline import CommandPipeline
from agent_voice.transport.http_client import BusinessClient


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""

    parser = argparse.ArgumentParser(prog="agent-voice")
    parser.add_argument("--config", default="config.example.json", help="Path to config JSON.")
    parser.add_argument("--text", help="ASR text to parse and send.")
    parser.add_argument("--asr-confidence", type=float, default=1.0, help="ASR confidence between 0 and 1.")
    parser.add_argument("--dry-run", action="store_true", help="Print payload without sending HTTP.")
    parser.add_argument("--gui", action="store_true", help="Start the floating desktop widget.")
    parser.add_argument("--mock-server", action="store_true", help="Start a local mock business endpoint.")
    parser.add_argument("--asr-file", help="Transcribe an audio file with the local SenseVoice model.")
    parser.add_argument("--asr-mic-seconds", type=float, help="Record microphone audio for N seconds and transcribe it.")
    parser.add_argument("--voice-loop", action="store_true", help="Listen for wake word, record speech, transcribe, and send.")
    parser.add_argument("--list-audio-devices", action="store_true", help="Print available audio devices and exit.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse one recognized utterance and optionally send it to the business endpoint."""

    args = build_parser().parse_args(argv)
    config = AppConfig.load(args.config)
    if args.list_audio_devices:
        return _list_audio_devices()

    if args.mock_server:
        return _run_mock_server()

    pipeline = _build_pipeline(config)

    if args.gui:
        from agent_voice.ui.qt_widget import run_qt_widget

        return run_qt_widget(pipeline, config=config, config_path=args.config)

    if args.asr_file:
        return _transcribe_file(config, args.asr_file)

    if args.asr_mic_seconds:
        return _transcribe_microphone(config, args.asr_mic_seconds)

    if args.voice_loop:
        from agent_voice.voice_loop import VoiceLoop

        return VoiceLoop(config=config, pipeline=pipeline).run_forever()

    if not args.text:
        print("必须提供 --text，或使用 --voice-loop / --asr-file / --asr-mic-seconds / --gui / --mock-server。", file=sys.stderr)
        return 2

    if args.dry_run:
        return _dry_run_text(config, args.text, args.asr_confidence)

    outcome = pipeline.process_text(args.text, asr_confidence=args.asr_confidence)
    print(json.dumps(outcome.__dict__, ensure_ascii=False))
    return 0 if outcome.status == "sent" else 3


def _build_pipeline(config: AppConfig) -> CommandPipeline:
    hmac_secret = None
    if config.transport.hmac_secret_env:
        hmac_secret = os.environ.get(config.transport.hmac_secret_env)
    client = BusinessClient(
        base_url=config.transport.base_url,
        command_path=config.transport.command_path,
        timeout_ms=config.transport.timeout_ms,
        retry=config.transport.retry,
        app_version=config.app.app_version,
        hmac_secret=hmac_secret,
    )
    return CommandPipeline(device_id=config.app.device_id, app_version=config.app.app_version, client=client)


def _list_audio_devices() -> int:
    from agent_voice.voice_loop import list_audio_devices

    print(json.dumps(list_audio_devices(), ensure_ascii=False, indent=2))
    return 0


def _run_mock_server() -> int:
    server = BusinessMockServer(host="127.0.0.1", port=18080)
    print("Agent Voice mock server listening on http://127.0.0.1:18080", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


def _transcribe_file(config: AppConfig, audio_file: str) -> int:
    from agent_voice.asr.sensevoice import SenseVoiceAsr

    engine = SenseVoiceAsr(model_dir=config.asr.model_dir, device=config.asr.device)
    result = engine.transcribe_file(audio_file)
    print(json.dumps(result.__dict__, ensure_ascii=False))
    return 0


def _transcribe_microphone(config: AppConfig, seconds: float) -> int:
    import tempfile
    from pathlib import Path

    from agent_voice.asr.microphone import record_microphone_seconds
    from agent_voice.asr.sensevoice import SenseVoiceAsr
    from agent_voice.audio.recorder import write_wav
    from agent_voice.voice_status import DEFAULT_STATUS_PATH, write_voice_status

    if seconds <= 0:
        print("--asr-mic-seconds 必须大于 0。", file=sys.stderr)
        return 2
    print(f"开始录音 {seconds:g} 秒，请现在说话。", flush=True)
    write_voice_status(DEFAULT_STATUS_PATH, event="mic_recording", seconds=seconds)
    samples = record_microphone_seconds(
        sample_rate=config.audio.sample_rate,
        frame_ms=config.audio.frame_ms,
        seconds=seconds,
        device_index=config.audio.device_index,
    )
    handle = tempfile.NamedTemporaryFile(prefix="agent_voice_mic_", suffix=".wav", delete=False)
    handle.close()
    wav_path = Path(handle.name)
    try:
        write_wav(wav_path, samples, config.audio.sample_rate)
        engine = SenseVoiceAsr(model_dir=config.asr.model_dir, device=config.asr.device)
        try:
            result = engine.transcribe_file(wav_path)
        except ValueError as exc:
            message = "未识别到文字"
            write_voice_status(DEFAULT_STATUS_PATH, event="mic_asr_empty", message=message)
            print(json.dumps({"event": "mic_asr_empty", "message": message, "detail": str(exc)}, ensure_ascii=False))
            return 3
    finally:
        wav_path.unlink(missing_ok=True)
    write_voice_status(DEFAULT_STATUS_PATH, event="mic_asr_result", asr_text=result.text, asr_elapsed_ms=result.elapsed_ms)
    print(json.dumps({"event": "mic_asr_result", **result.__dict__}, ensure_ascii=False))
    return 0


def _dry_run_text(config: AppConfig, text: str, asr_confidence: float) -> int:
    from datetime import datetime, timezone

    from agent_voice.nlu.parser import IntentParser
    from agent_voice.transport.schema import build_command_payload, generate_request_id

    parse_result = IntentParser().parse(text, asr_confidence=asr_confidence)
    if not parse_result.matched:
        print(json.dumps({"matched": False, "reason": parse_result.reason}, ensure_ascii=False))
        return 2
    payload = build_command_payload(
        parse_result=parse_result,
        device_id=config.app.device_id,
        app_version=config.app.app_version,
        request_id=generate_request_id(now=datetime.now(timezone.utc)),
        now=datetime.now(timezone.utc),
        duration_ms={"recording": 0, "asr": 0, "parse": 0},
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
