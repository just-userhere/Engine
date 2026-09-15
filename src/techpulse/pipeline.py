"""Pipeline: SOURCE DISCOVERY → FETCH → PARSE → NORMALIZE → DEDUP → FILTER → SCORE → RANK → SELECT → SUMMARIZE → VALIDATE → GENERATE → PUBLISH."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from . import config as config_mod
from .deduplicator import deduplicate
from .fetcher import fetch_url
from .normalizer import normalize_title, normalize_url, stable_id
from .parser import parse_feed
from .ranker import rank_and_select
from .scorer import score_item
from .sources import load_sources
from .state import filter_unseen, load_seen, save_seen
from .summarizer import extractive_summary, maybe_llm_polish, why_it_matters

log = logging.getLogger("techpulse")


def report_date_ist(cfg, override: str | None = None):
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(cfg.timezone_name)
    if override:
        y, m, d = map(int, override.split("-"))
        from datetime import date
        return date(y, m, d)
    return datetime.now(tz).date()


def is_valid(item: dict) -> tuple[bool, str]:
    if not item.get("title") or len(item["title"]) < 15:
        return False, "title too short"
    url = item.get("url", "")
    if not (url.startswith("http://") or url.startswith("https://")):
        return False, "bad url"
    if not item.get("summary"):
        return False, "empty summary"
    return True, ""


def run(engine_root: Path, dry_run: bool = False, target_date: str | None = None,
        output_dir: Path | None = None) -> dict:
    cfg = config_mod.AppConfig.from_env_and_yaml(engine_root)
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(cfg.timezone_name)
    rdate = report_date_ist(cfg, target_date)
    now_utc = datetime.now(timezone.utc)
    log.info("Starting TechPulse | tz=%s target=07:00 IST report=%s", cfg.timezone_name, rdate)

    sources = load_sources(engine_root)
    log.info("Fetching %d sources", len(sources))
    raw_items = []
    for s in sources:
        blob = fetch_url(s.url)
        if not blob:
            continue
        raw_items.extend(parse_feed(blob, s.name, s.category_default, s.reliability))
    log.info("Collected %d articles", len(raw_items))

    # normalize
    normed = []
    for r in raw_items:
        curl = normalize_url(r.url)
        nt = normalize_title(r.title)
        normed.append({
            "id": stable_id(curl, nt),
            "title": r.title.strip(), "url": r.url.strip(), "canonical_url": curl,
            "norm_title": nt, "summary": r.summary, "source": r.source,
            "published_at": r.published_at.isoformat() if r.published_at else "",
            "published_dt": r.published_at, "category_default": r.category_default,
            "reliability": r.reliability,
        })
    # freshness window
    fresh = []
    for it in normed:
        dt = it.pop("published_dt")
        it["published_at_dt"] = dt
        if dt is None:
            fresh.append(it)
            continue
        age_h = (now_utc - dt).total_seconds() / 3600
        if age_h <= cfg.freshness_window_hours + 24:  # small grace for slow feeds
            fresh.append(it)
    # dedupe
    uniq, n_dup = deduplicate(fresh, cfg.duplicate_threshold)
    log.info("Removed %d duplicates, %d candidates remain", n_dup, len(uniq))
    # state filter (skip already published)
    state_file = engine_root / "state" / "seen.json"
    seen = load_seen(state_file)
    unseen = filter_unseen(uniq, seen)
    log.info("%d unseen after state filter", len(unseen))
    # score + validate
    scored = []
    for it in unseen:
        pub = it.pop("published_at_dt")
        it["published_at"] = pub.isoformat() if pub else ""
        score, cat = score_item({**it, "published_at": pub}, cfg.weights, now_utc, cfg.freshness_window_hours)
        it["importance_score"] = score
        it["category"] = cat
        ok, reason = is_valid(it)
        if not ok:
            log.info("skip %s: %s", it["title"][:60], reason)
            continue
        # summarize (deterministic first, optional LLM polish of retrieved content only)
        summ = extractive_summary(it["summary"])
        if summ.startswith("Article URL:") or summ.startswith("Comments URL:"):
            # hnrss-style metadata is not a summary — fall back to the headline itself
            summ = it["title"].strip()
        it["summary"] = maybe_llm_polish(summ) or summ
        it["why_it_matters"] = why_it_matters(cat, it["title"], it["summary"])
        it["published_at"] = pub.strftime("%Y-%m-%d") if pub else ""
        scored.append(it)
    selected = rank_and_select(scored, cfg.news_minimum, cfg.news_maximum)
    log.info("Selected %d stories", len(selected))

    result: dict = {"report_date": rdate.isoformat(), "selected": selected,
                    "stats": {"collected": len(raw_items), "dups": n_dup, "selected": len(selected)}}
    if dry_run:
        log.info("dry-run: not publishing")
        if output_dir:
            from .publisher import publish_local
            r = publish_local(output_dir, rdate, selected)
            result["preview"] = r["path"]
        return result
    # record state (only on real runs)
    for s in selected:
        seen[s["id"]] = rdate.isoformat()
    save_seen(state_file, seen, cfg.state_max_entries)
    if output_dir:  # local output checkout mode
        from .publisher import commit_and_push, publish_local
        r = publish_local(output_dir, rdate, selected)
        result.update(r)
        if r["changed"]:
            result["commit"] = commit_and_push(output_dir, rdate)
    else:  # CI remote mode
        from pathlib import Path as _P
        import tempfile
        from .publisher import publish_remote
        with tempfile.TemporaryDirectory() as td:
            r = publish_remote(engine_root, rdate, selected, _P(td))
            result.update(r)
    log.info("Completed successfully")
    return result
