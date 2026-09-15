"""Deduplication: exact canonical-URL + fuzzy title match. Prefer primary source."""
from __future__ import annotations

import difflib
import logging

log = logging.getLogger("techpulse.dedup")


def title_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def deduplicate(items: list[dict], threshold: float = 0.82) -> tuple[list[dict], int]:
    seen_urls: set[str] = set()
    kept: list[dict] = []
    removed = 0
    # Prefer higher reliability first so the primary source wins
    ordered = sorted(items, key=lambda x: x.get("reliability", 0.7), reverse=True)
    for it in ordered:
        url = it.get("canonical_url", "")
        if url in seen_urls:
            removed += 1
            continue
        dup = False
        for k in kept:
            if title_similarity(it.get("norm_title", ""), k.get("norm_title", "")) >= threshold:
                dup = True
                # retain supporting source link
                srcs = k.setdefault("supporting_sources", [])
                srcs.append({"source": it.get("source"), "url": it.get("url")})
                removed += 1
                break
        if not dup:
            seen_urls.add(url)
            kept.append(it)
    # restore chronological-ish order for downstream ranking (ranking re-sorts anyway)
    log.info("deduplicated: %d kept, %d removed", len(kept), removed)
    return kept, removed
