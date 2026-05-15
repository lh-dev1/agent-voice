"""Shared runtime status file for showing latest recognized speech in the widget."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _default_status_path() -> Path:
    """Return a writable per-user path shared by the GUI and voice loop."""

    override = os.environ.get("AGENT_VOICE_STATUS_PATH")
    if override:
        return Path(override)
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "AgentVoice" / "last_voice_event.json"
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
        return base / "AgentVoice" / "last_voice_event.json"
    return Path.home() / ".local" / "state" / "agent-voice" / "last_voice_event.json"


DEFAULT_STATUS_PATH = _default_status_path()


def write_voice_status(path: str | Path = DEFAULT_STATUS_PATH, **status: Any) -> None:
    """Write the latest voice pipeline status as UTF-8 JSON."""

    status_path = Path(path)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"updated_at": datetime.now(timezone.utc).isoformat(), **status}
    status_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_voice_status(path: str | Path = DEFAULT_STATUS_PATH) -> dict[str, Any]:
    """Read the latest voice pipeline status, or return empty data if absent."""

    status_path = Path(path)
    if not status_path.exists():
        return {}
    try:
        data = json.loads(status_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"event": "status_error", "message": "last voice status is not valid JSON"}
    return data if isinstance(data, dict) else {}
