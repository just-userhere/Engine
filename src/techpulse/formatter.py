"""Markdown report generation + Output README/stats updater."""
from __future__ import annotations

import re
from collections import Counter
from datetime import date
from pathlib import Path

MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]

def month_folder(report_date: date) -> str:
    return MONTH_NAMES[report_date.month]


def report_filename(report_date: date) -> str:
    return report_date.isoformat() + ".md"


def pretty_date(report_date: date) -> str:
    return f"{MONTH_NAMES[report_date.month]} {report_date.day}, {report_date.year}"


def generate_report(report_date: date, stories: list[dict]) -> str:
    """Daily technology-news report. One item per real story; never fabricate to fill a quota."""
    lines = [
        f"# TechPulse — {pretty_date(report_date)}",
        "",
        "A concise daily technology news briefing covering the most relevant developments "
        "in AI, software, cloud, cybersecurity, developer tools, hardware, open source, "
        "and the broader technology ecosystem.",
        "",
        "---",
        "",
    ]
    if not stories:
        lines += ["No qualifying technology developments met the quality bar today.", ""]
        return "\n".join(lines)
    for i, s in enumerate(stories, 1):
        lines += [
            f"## {i}. {s['title']}",
            "",
            f"**Category:** {s.get('category', 'Technology')}",
            "",
            "### What happened",
            "",
            s.get("summary", ""),
            "",
            "### Why it matters",
            "",
            s.get("why_it_matters", ""),
            "",
            f"**Source:** [{s.get('source', 'Source')}]({s.get('url', '#')})"
            + (f" — {s['published_at']}" if s.get("published_at") else ""),
            "",
            "---",
            "",
        ]
    return "\n".join(lines)


def update_output_readme(output_root: Path) -> str:
    """Rebuild Output README from actual archive files. All counts come from real data."""
    month_dirs = sorted([d for d in output_root.iterdir()
                         if d.is_dir() and not d.name.startswith(".")])
    total_items = 0
    cats: Counter = Counter()
    rows = []
    latest = None  # (date_str, path)
    for m in month_dirs:
        files = sorted(m.glob("20*.md"))
        count = 0
        for f in files:
            text = f.read_text(encoding="utf-8", errors="ignore")
            n = len(re.findall(r"^## \d+\. ", text, re.M))
            count += n
            total_items += n
            for c in re.findall(r"\*\*Category:\*\* (.+)", text):
                cats[c.strip()] += 1
            ds = f.stem
            if latest is None or ds > latest[0]:
                latest = (ds, f"{m.name}/{f.name}")
        rows.append((m.name, len(files), count))
    latest_block = "No reports published yet — the first run publishes at 07:00 IST."
    if latest:
        ds, rel = latest
        try:
            y, mo, d = map(int, ds.split("-"))
            pretty = f"{MONTH_NAMES[mo]} {d}, {y}"
        except Exception:
            pretty = ds
        latest_block = (f"### {pretty}\n\n"
                        f"{total_items} technology news items archived across "
                        f"{sum(r[1] for r in rows)} publication days.\n\n"
                        f"[Read the latest report →]({rel})")
    archive = "\n".join(f"| [{m}]({m}/) | {days} | {items} |" for m, days, items in rows) or \
        "| — | 0 | 0 |"
    top_cats = "\n".join(f"- {c}: {n}" for c, n in cats.most_common(8)) or "- No data yet"
    return f"""# TechPulse

Your automated daily technology newspaper.

TechPulse is an automated daily technology-news archive. Every morning it collects
important developments across AI, software, cloud, cybersecurity, developer tools,
hardware, and open source — then filters duplicates, ranks by relevance, and publishes
a concise, source-grounded briefing.

## Latest report

{latest_block}

## Monthly archive

Reports are organized by month, one Markdown file per publication date (`YYYY-MM-DD.md`):

| Month | Reports | News items |
|---|---:|---:|
{archive}

## Technology categories

{top_cats}

Full category list: Artificial Intelligence, Cybersecurity, Cloud, DevOps, Programming,
Hardware, Startups, Databases, Web, Open Source, Technology.

## How it works

1. The [Engine](https://github.com/just-userhere/Engine) fetches configured RSS sources.
2. Stories are normalized, deduplicated (canonical URL + title similarity), and filtered by quality and freshness.
3. Remaining stories are scored, ranked, and summarized strictly from retrieved source content.
4. The report is published here idempotently — reruns never duplicate content.

## Automation schedule

- Target publication: 07:00 AM IST (`Asia/Kolkata`) daily.
- GitHub Actions cron: `30 1 * * *` (01:30 UTC). GitHub scheduling is best-effort and may start slightly later.
- Report dates always use `Asia/Kolkata`, never naive UTC. Manual reruns accept a `target_date` override.

## Statistics

- Total news items: {total_items}
- Publication days: {sum(r[1] for r in rows)}
"""
