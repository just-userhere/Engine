"""Deterministic extractive summarizer. LLM optional, fallback always safe.

The LLM (if configured) only rewrites retrieved source content — it must never
invent news. On any failure we fall back to the extractive summary.
"""
from __future__ import annotations

import logging
import os
import re

log = logging.getLogger("techpulse.summarizer")
SENT = re.compile(r"(?<=[.!?])\s+")


def extractive_summary(text: str, max_sentences: int = 2, max_chars: int = 500) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return ""
    parts = [p.strip() for p in SENT.split(text) if p.strip()]
    out = " ".join(parts[:max_sentences]).strip()
    if len(out) > max_chars:
        out = out[: max_chars - 1].rstrip() + "…"
    return out


WHY_TEMPLATES = {
    "Artificial Intelligence": "Relevant to teams building or buying AI features — models, agents, and tooling here tend to change what is practical to ship.",
    "Cybersecurity": "Patch and prioritize accordingly — advisories and disclosed flaws in this category often require near-term action.",
    "Cloud": "Affects architecture and cost choices on AWS/Azure/GCP — worth noting for platform and DevOps planning.",
    "DevOps": "Affects delivery pipelines and operations — useful for platform engineers standardizing builds and deploys.",
    "Programming": "Affects daily development work — libraries, languages, and tooling changes worth knowing before adopting.",
    "Hardware": "Affects AI capacity and cost — chip and infra moves shape what workloads are economical.",
    "Startups": "Signals where funding and competition are moving — useful context for build-vs-buy calls.",
    "Databases": "Affects data-layer choices — version and feature changes can alter performance and migration plans.",
    "Technology": "Worth knowing for general planning — assess fit to your stack before acting.",
}


def why_it_matters(category: str, title: str, summary: str) -> str:
    base = WHY_TEMPLATES.get(category, WHY_TEMPLATES["Technology"])
    # Keep it grounded: reference the story, no invented consequences.
    first = extractive_summary(summary, max_sentences=1, max_chars=200)
    if first:
        return f"{base} In this case: {first}"
    return base


def maybe_llm_polish(text: str) -> str:
    """Optional LLM rewrite of already-retrieved content. Disabled unless OPENAI_API_KEY set."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key or not text:
        return text
    try:
        import json
        import urllib.request
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": "Rewrite the tech news summary concisely in 1-2 neutral sentences. Do not add facts."},
                {"role": "user", "content": text[:1500]},
            ],
            "max_tokens": 150,
            "temperature": 0.2,
        }).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        return data["choices"][0]["message"]["content"].strip() or text
    except Exception as e:  # noqa: BLE001
        log.warning("LLM polish failed, using deterministic summary: %s", e)
        return text
