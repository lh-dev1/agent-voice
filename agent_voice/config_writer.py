"""Safe JSON configuration updates for the desktop settings UI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def update_config(path: str | Path, updates: dict[str, Any]) -> None:
    """Update dotted JSON config paths while preserving unrelated keys."""

    config_path = Path(path)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    for dotted_key, value in updates.items():
        _set_dotted_value(data, dotted_key, value)
    config_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _set_dotted_value(data: dict[str, Any], dotted_key: str, value: Any) -> None:
    parts = dotted_key.split(".")
    if len(parts) < 2:
        raise ValueError(f"Config update key must be dotted: {dotted_key}")
    current = data
    for part in parts[:-1]:
        child = current.setdefault(part, {})
        if not isinstance(child, dict):
            raise ValueError(f"Cannot set nested config under non-object key: {part}")
        current = child
    current[parts[-1]] = value
