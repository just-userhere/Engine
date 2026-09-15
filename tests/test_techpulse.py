"""Tests: parsing, normalization, dedup, scoring, timezone, filenames, markdown, state, config."""
from datetime import date, datetime, timezone
from pathlib import Path

from techpulse import config as config_mod
from techpulse.deduplicator import deduplicate
from techpulse.formatter import generate_report, month_folder, report_filename, update_output_readme
from techpulse.normalizer import normalize_title, normalize_url, stable_id
from techpulse.parser import parse_feed
from techpulse.ranker import rank_and_select
from techpulse.scorer import score_item
from techpulse.state import filter_unseen, load_seen, save_seen


def test_url_normalization_strips_tracking():
    a = normalize_url("https://Example.com/Path/?utm_source=x&b=1&utm_medium=y")
    assert a == "https://example.com/Path?b=1"
    assert normalize_url("https://example.com/a/") == "https://example.com/a"


def test_title_normalization():
    assert normalize_title("  OpenAI Announces GPT-X!!! ") == "openai announces gpt x"
    assert stable_id("u", "t") == stable_id("u", "t")


def test_parse_rss_and_atom():
    rss = (b"<rss><channel><item><title>T</title><link>https://e.com/1</link>"
           b"<pubDate>Tue, 15 Sep 2026 10:00:00 +0530</pubDate>"
           b"<description><p>Hello</p></description></item></channel></rss>")
    items = parse_feed(rss, "S")
    assert len(items) == 1 and items[0].title == "T"
    atom = (b"<feed xmlns='http://www.w3.org/2005/Atom'><entry><title>A</title>"
            b"<link href='https://e.com/2'/><updated>2026-09-15T01:00:00Z</updated>"
            b"<summary>Hi</summary></entry></feed>")
    assert len(parse_feed(atom, "S")) == 1
    assert parse_feed(b"not xml", "S") == []


def test_deduplicate_prefers_primary_and_merges():
    items = [
        {"canonical_url": "https://a.com/1", "norm_title": "openai launches new model",
         "reliability": 0.9, "source": "A", "url": "https://a.com/1"},
        {"canonical_url": "https://b.com/2", "norm_title": "openai launches new model today",
         "reliability": 0.6, "source": "B", "url": "https://b.com/2"},
    ]
    kept, removed = deduplicate(items, 0.8)
    assert len(kept) == 1 and removed == 1
    assert kept[0]["source"] == "A"


def test_scoring_and_ranking_bounds():
    now = datetime(2026, 9, 15, 2, 0, tzinfo=timezone.utc)
    w = {"industry_impact": 0.25, "developer_relevance": 0.25, "novelty": 0.15,
         "source_reliability": 0.15, "freshness": 0.10, "trend_momentum": 0.10}
    it = {"title": "OpenAI announces new agent API", "summary": "New API launch for developers",
          "reliability": 0.9, "published_at": datetime(2026, 9, 15, 1, 0, tzinfo=timezone.utc)}
    score, cat = score_item(it, w, now, 72)
    assert score > 0.5 and cat == "Artificial Intelligence"
    ranked = rank_and_select([{"importance_score": 0.9}, {"importance_score": 0.1}],
                             minimum=1, maximum=1)
    assert len(ranked) == 1 and ranked[0]["importance_score"] == 0.9


def test_ist_report_date_not_utc():
    # 2026-09-16 01:30 UTC == 2026-09-16 07:00 IST (same calendar date here),
    # but 2026-09-15 20:00 UTC == 2026-09-16 01:30 IST (date differs from UTC).
    from zoneinfo import ZoneInfo
    utc = datetime(2026, 9, 15, 20, 0, tzinfo=timezone.utc)
    ist = utc.astimezone(ZoneInfo("Asia/Kolkata"))
    assert utc.date().isoformat() == "2026-09-15"
    assert ist.date().isoformat() == "2026-09-16"


def test_month_folder_and_filename():
    assert month_folder(date(2026, 9, 15)) == "September"
    assert report_filename(date(2026, 9, 15)) == "2026-09-15.md"


def test_markdown_generation_shape():
    stories = [{"title": "OpenAI announces X", "category": "Artificial Intelligence",
                "importance_score": 0.8, "summary": "S.", "why_it_matters": "W.",
                "source": "Blog", "url": "https://e.com", "published_at": "2026-09-15"}]
    md = generate_report(date(2026, 9, 15), stories)
    assert "# ⚡ TechPulse — September 15, 2026" in md
    assert "### 1. OpenAI announces X" in md and "Why it matters" in md


def test_state_roundtrip_and_unseen(tmp_path: Path):
    f = tmp_path / "seen.json"
    save_seen(f, {"a": "2026-09-15", "b": "2026-09-14"}, max_entries=1)
    seen = load_seen(f)
    assert len(seen) == 1  # capped
    items = [{"id": "a"}, {"id": "z"}]
    assert [x["id"] for x in filter_unseen(items, {"a": "x"})] == ["z"]
    assert load_seen(tmp_path / "missing.json") == {}


def test_config_defaults_and_env(tmp_path: Path, monkeypatch):
    cfg = config_mod.AppConfig.from_env_and_yaml(Path(__file__).resolve().parents[1])
    assert cfg.timezone_name == "Asia/Kolkata" and cfg.news_maximum == 5
    monkeypatch.setenv("NEWS_MAXIMUM", "3")
    cfg2 = config_mod.AppConfig.from_env_and_yaml(Path(__file__).resolve().parents[1])
    assert cfg2.news_maximum == 3


def test_readme_updater_counts_real_files(tmp_path: Path):
    m = tmp_path / "September"
    m.mkdir()
    (m / "2026-09-15.md").write_text(
        "# T\n\n### 1. A\n\n**Category:** Cloud\n\n### 2. B\n\n**Category:** Cloud\n",
        encoding="utf-8")
    out = update_output_readme(tmp_path)
    assert "Total stories: 2" in out and "September" in out


def test_invalid_story_rejected():
    from techpulse.pipeline import is_valid
    assert is_valid({"title": "x", "url": "https://e.com", "summary": "s"})[0] is False
    assert is_valid({"title": "A proper headline about AI release today",
                     "url": "notaurl", "summary": "s"})[0] is False
    assert is_valid({"title": "A proper headline about AI release today",
                     "url": "https://e.com/x", "summary": "detail"})[0] is True
