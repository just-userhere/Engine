"""Relevance/importance scoring. Deterministic, configurable weights."""
from __future__ import annotations

import re
from datetime import datetime, timezone

HIGH_IMPACT = re.compile(
    r"\b(openai|anthropic|google|microsoft|aws|azure|nvidia|apple|meta|launch|announc|release|"
    r"vulnerab|cve|zero-?day|breach|kubernetes|llm|gpt|agent|copilot|gemini|claude| Blackwell|"
    r"chip|semiconductor|outage|acqui|ipo|funding|quantum)\b", re.I)
DEV_KEYWORDS = re.compile(
    r"\b(api|sdk|github|devops|ci/cd|docker|kubernetes|python|typescript|rust|go\b|"
    r"database|postgres|cloud|saas|open source|framework|library|cli|ide|vscode)\b", re.I)

CATEGORY_HINTS = [
    (re.compile(r"\b(ai|llm|gpt|agent|ml\b|machine learning|generative|anthropic|openai|gemini|claude)\b", re.I), "Artificial Intelligence"),
    (re.compile(r"\b(cve|vulnerab|ransomware|phish|malware|zero-?day|cisa|breach|exploit)\b", re.I), "Cybersecurity"),
    (re.compile(r"\b(aws|azure|gcp|google cloud|cloud|s3|lambda|bigquery)\b", re.I), "Cloud"),
    (re.compile(r"\b(kubernetes|docker|devops|ci/cd|terraform|github actions|helm)\b", re.I), "DevOps"),
    (re.compile(r"\b(python|typescript|javascript|rust|golang|java\b|sdk|api\b|framework)\b", re.I), "Programming"),
    (re.compile(r"\b(nvidia|chip|semiconductor|gpu|cpu|tpu|blackwell|qualcomm|intel|amd)\b", re.I), "Hardware"),
    (re.compile(r"\b(startup|funding|ipo|acqui|series [abc])\b", re.I), "Startups"),
    (re.compile(r"\b(database|postgres|mysql|mongo|redis|sql)\b", re.I), "Databases"),
]


def categorize(title: str, summary: str, default: str = "Technology") -> str:
    text = f"{title} {summary}"
    for rx, cat in CATEGORY_HINTS:
        if rx.search(text):
            return cat
    return default


def score_item(item: dict, weights: dict, now_utc: datetime, freshness_window_h: int) -> tuple[float, str]:
    text = f"{item.get('title','')} {item.get('summary','')}"
    impact = 0.9 if HIGH_IMPACT.search(text) else (0.6 if len(text) > 200 else 0.4)
    dev = 0.9 if DEV_KEYWORDS.search(text) else 0.5
    novelty = 0.8 if any(w in text.lower() for w in ("announc", "launch", "introduc", "release", "new ")) else 0.5
    reliability = float(item.get("reliability", 0.7))
    pub = item.get("published_at")
    if pub is None:
        fresh = 0.4
    else:
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        age_h = max(0.0, (now_utc - pub.astimezone(timezone.utc)).total_seconds() / 3600)
        if age_h <= freshness_window_h:
            fresh = 1.0 - (age_h / freshness_window_h) * 0.5  # 1.0 → 0.5
        else:
            fresh = max(0.1, 0.5 - (age_h - freshness_window_h) / freshness_window_h * 0.2)
    momentum = 0.6 + min(0.3, len(item.get("supporting_sources", [])) * 0.15)
    score = (
        weights.get("industry_impact", 0.25) * impact
        + weights.get("developer_relevance", 0.25) * dev
        + weights.get("novelty", 0.15) * novelty
        + weights.get("source_reliability", 0.15) * reliability
        + weights.get("freshness", 0.10) * fresh
        + weights.get("trend_momentum", 0.10) * momentum
    )
    category = categorize(item.get("title", ""), item.get("summary", ""), item.get("category_default", "Technology"))
    return round(score, 4), category
