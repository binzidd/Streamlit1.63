"""Saved-view presets — persist named filter snapshots to a local JSON file."""
from __future__ import annotations

import json
from pathlib import Path

PRESETS_FILE = Path(__file__).parent.parent / "presets.json"


def load_presets() -> dict[str, dict]:
    if not PRESETS_FILE.exists():
        return {}
    try:
        return json.loads(PRESETS_FILE.read_text())
    except Exception:
        return {}


def save_preset(name: str, data: dict) -> None:
    presets = load_presets()
    presets[name] = data
    PRESETS_FILE.write_text(json.dumps(presets, indent=2))


def delete_preset(name: str) -> None:
    presets = load_presets()
    if name in presets:
        del presets[name]
        PRESETS_FILE.write_text(json.dumps(presets, indent=2))
