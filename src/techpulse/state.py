"""Persistent state: previously published story IDs. Capped to avoid unbounded growth."""
from __future__ import annotations

import json
from pathlib import Path


def load_seen(state_file: Path) -> dict:
    if not state_file.exists():
        return {}
    try:
        return json.loads(state_file.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def save_seen(state_file: Path, seen: dict, max_entries: int = 2000) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    items = sorted(seen.items(), key=lambda kv: str(kv[1]), reverse=True)[:max_entries]
    state_file.write_text(json.dumps(dict(items), indent=2), encoding="utf-8")


def filter_unseen(items: list[dict], seen: dict) -> list[dict]:
    return [x for x in items if x.get("id") not in seen]
