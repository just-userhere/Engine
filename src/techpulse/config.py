"""Central configuration. No magic numbers elsewhere — import from here."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover (py<3.9 unsupported)
    raise RuntimeError("Python 3.9+ with zoneinfo required")

DEFAULT_TIMEZONE = "Asia/Kolkata"


def get_timezone(name: str | None = None) -> "ZoneInfo":
    return ZoneInfo(name or os.environ.get("TIMEZONE", DEFAULT_TIMEZONE))


@dataclass
class AppConfig:
    timezone_name: str = DEFAULT_TIMEZONE
    news_minimum: int = 1
    news_maximum: int = 5
    freshness_window_hours: int = 72
    duplicate_threshold: float = 0.82
    state_max_entries: int = 2000
    output_repository: str = "just-userhere/Output"
    weights: dict = field(default_factory=lambda: {
        "industry_impact": 0.25,
        "developer_relevance": 0.25,
        "novelty": 0.15,
        "source_reliability": 0.15,
        "freshness": 0.10,
        "trend_momentum": 0.10,
    })
    sources_file: Path = Path("config/sources.yaml")

    @classmethod
    def from_env_and_yaml(cls, engine_root: Path) -> "AppConfig":
        import yaml  # local import so tests can stub

        cfg = cls()
        cfg.timezone_name = os.environ.get("TIMEZONE", DEFAULT_TIMEZONE)
        src_file = engine_root / "config" / "sources.yaml"
        cfg.sources_file = src_file
        if src_file.exists():
            with open(src_file, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            cfg.timezone_name = os.environ.get("TIMEZONE", data.get("timezone", DEFAULT_TIMEZONE))
            cfg.news_minimum = int(os.environ.get("NEWS_MINIMUM") or data.get("news_minimum", 1))
            cfg.news_maximum = int(os.environ.get("NEWS_MAXIMUM") or data.get("news_maximum", 5))
            cfg.freshness_window_hours = int(
                os.environ.get("FRESHNESS_WINDOW_HOURS") or data.get("freshness_window_hours", 72)
            )
            cfg.duplicate_threshold = float(data.get("duplicate_threshold", 0.82))
            cfg.state_max_entries = int(data.get("state_max_entries", 2000))
            cfg.output_repository = os.environ.get("OUTPUT_REPOSITORY") or data.get(
                "output_repository", "just-userhere/Output"
            )
            if data.get("weights"):
                cfg.weights = dict(data["weights"])
        # explicit env overrides
        if os.environ.get("NEWS_MINIMUM"):
            cfg.news_minimum = int(os.environ["NEWS_MINIMUM"])
        if os.environ.get("NEWS_MAXIMUM"):
            cfg.news_maximum = int(os.environ["NEWS_MAXIMUM"])
        if cfg.news_minimum < 1:
            cfg.news_minimum = 1
        if cfg.news_maximum < cfg.news_minimum:
            cfg.news_maximum = cfg.news_minimum
        return cfg
