"""Ranking + selection within configurable [minimum, maximum]."""
from __future__ import annotations


def rank_and_select(items: list[dict], minimum: int = 1, maximum: int = 5,
                    min_score: float = 0.35) -> list[dict]:
    ranked = sorted(items, key=lambda x: x.get("importance_score", 0), reverse=True)
    eligible = [x for x in ranked if x.get("importance_score", 0) >= min_score]
    if not eligible:
        eligible = ranked[:1] if ranked else []  # publish 1 rather than an empty brief, if anything exists
    selected = eligible[:maximum]
    # If fewer than minimum but items exist, keep what we have (never fabricate)
    return selected
