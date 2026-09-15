"""Markdown report generation + Output README/stats updater."""
from __future__ import annotations

import re
from collections import Counter
from datetime import date
from pathlib import Path

MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]

IMPACT_LABELS = [(0.75, "High"), (0.55, "Medium")]


def impact_label(score: float) -> str:
    for thresh, label in IMPACT_LABELS:
        if score >= thresh:
            return label
    return "Notable"


def month_folder(report_date: date) -> str:
    return MONTH_NAMES[report_date.month]


def report_filename(report_date: date) -> str:
    return report_date.isoformat() + ".md"


def pretty_date(report_date: date) -> str:
    return f"{MONTH_NAMES[report_date.month]} {report_date.day}, {report_date.year}"


def generate_report(report_date: date, stories: list[dict]) -> str:
    lines = [
        f"# ⚡ TechPulse — {pretty_date(report_date)}",
        "",
        "> Your daily technology intelligence brief.",
        "",
        "## 🔥 Today's Technology Updates",
        "",
    ]
    if not stories:
        lines += ["No qualifying technology developments met the quality bar today.", ""]
        return "\n".join(lines)
    for i, s in enumerate(stories, 1):
        lines += [
            f"### {i}. {s['title']}",
            "",
            f"**Category:** {s.get('category', 'Technology')}",
            "",
            f"**Impact:** {impact_label(s.get('importance_score', 0))}",
            "",
            s.get("summary", ""),
            "",
            "### Why it matters",
            "",
            s.get("why_it_matters", ""),
            "",
            "### Source",
            "",
            f"[{s.get('source', 'Source')}]({s.get('url', '#')})"
            + (f" — {s['published_at']}" if s.get("published_at") else ""),
            "",
            "---",
            "",
        ]
    return "\n".join(lines)


def update_output_readme(output_root: Path) -> str:
    """Rebuild Output README from actual files. Returns new README text."""
    month_dirs = sorted([d for d in output_root.iterdir()
                         if d.is_dir() and not d.name.startswith(".") and d.name != "dashboard"])
    total_stories = 0
    cats: Counter = Counter()
    rows = []
    latest = None  # (date_str, path)
    for m in month_dirs:
        files = sorted(m.glob("20*.md"))
        count = 0
        for f in files:
            text = f.read_text(encoding="utf-8", errors="ignore")
            n = len(re.findall(r"^### \d+\. ", text, re.M))
            count += n
            total_stories += n
            for c in re.findall(r"\*\*Category:\*\* (.+)", text):
                cats[c.strip()] += 1
            ds = f.stem
            if latest is None or ds > latest[0]:
                latest = (ds, f"{m.name}/{f.name}")
        rows.append((m.name, len(files), count))
    latest_block = ""
    if latest:
        ds, rel = latest
        try:
            y, mo, d = map(int, ds.split("-"))
            pretty = f"{MONTH_NAMES[mo]} {d}, {y}"
        except Exception:
            pretty = ds
        latest_block = (f"## 📰 Latest Update\n\n### {pretty}\n\n"
                        f"[Read today's update →]({rel})\n")
    archive = "\n".join(f"| [{m}]({m}/) | {days} | {stories} |" for m, days, stories in rows) or \
        "| — | 0 | 0 |"
    top_cats = "\n".join(f"- {c}: {n}" for c, n in cats.most_common(8)) or "- No data yet"
    return f"""# ⚡ TechPulse

### Your automated daily technology newspaper.

Important technology developments,
filtered, ranked, and organized automatically.

> Technology news is spread across many websites, blogs, company announcements, and technical sources. Manually checking all of them every morning takes time and often results in repetitive or low-value information. TechPulse automates this — collecting relevant developments, filtering duplicates, ranking by importance, and publishing a concise daily briefing.

## 📰 Latest Update

{latest_block if latest_block else "No reports published yet."}

## 📚 Monthly Archive

| Month | Days | Stories |
|---|---:|---:|
{archive}

## 📊 Statistics

- Total stories: {total_stories}
- Publication days: {sum(r[1] for r in rows)}

### Top categories

{top_cats}

## 🔧 Engine

Built by the [Engine](https://github.com/just-userhere/Engine) repository — automated daily at 07:00 IST (01:30 UTC cron). See Engine README for architecture.
"""
