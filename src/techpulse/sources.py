"""Configurable source registry. Add/remove sources in config/sources.yaml only."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Source:
    name: str
    url: str
    type: str = "rss"
    category_default: str = "Technology"
    reliability: float = 0.7
    enabled: bool = True


def load_sources(engine_root: Path) -> list[Source]:
    path = engine_root / "config" / "sources.yaml"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    out: list[Source] = []
    for s in data.get("sources", []):
        src = Source(
            name=s.get("name", "unknown"),
            url=s.get("url", ""),
            type=s.get("type", "rss"),
            category_default=s.get("category_default", "Technology"),
            reliability=float(s.get("reliability", 0.7)),
            enabled=bool(s.get("enabled", True)),
        )
        if src.enabled and src.url:
            out.append(src)
    return out
