# ⚡ TechPulse Engine

Automated daily technology newspaper — collection, ranking, and publishing pipeline.
Publishes into [`just-userhere/Output`](https://github.com/just-userhere/Output) every morning (07:00 IST target).

## Architecture

```
SOURCES (config/sources.yaml)
  → FETCH (fetcher.py, retries/backoff)
  → PARSE (parser.py, RSS+Atom stdlib)
  → NORMALIZE (normalizer.py: URL/title/IDs)
  → DEDUPLICATE (deduplicator.py)
  → FILTER (freshness window + state/seen.json)
  → SCORE (scorer.py, configurable weights)
  → RANK/SELECT (ranker.py, min 1 / max 5)
  → SUMMARIZE (summarizer.py, deterministic; optional LLM polish only)
  → VALIDATE (pipeline.is_valid)
  → GENERATE (formatter.py)
  → PUBLISH (publisher.py, idempotent, commit YYYY-MM-DD)
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill OUTPUT_TOKEN etc. — never commit .env
```

## Local run

```bash
# safe preview (no publish)
PYTHONPATH=src python -m techpulse --dry-run --output-dir /tmp/preview
# Windows (PowerShell):
$env:PYTHONPATH="src"; py -m techpulse --dry-run --output-dir "$env:TEMP\preview"
# publish to a local Output checkout:
PYTHONPATH=src python -m techpulse --output-dir ../Output
# CI publish via token:
OUTPUT_TOKEN=... PYTHONPATH=src python -m techpulse --live
```

Manual date override (testing/recovery, interpreted in Asia/Kolkata):

```bash
PYTHONPATH=src python -m techpulse --dry-run --target-date 2026-09-15 --output-dir /tmp/preview
```

## Tests

```bash
python -m pytest tests -q
```

## Configuration

`config/sources.yaml`: sources, `news_minimum/maximum`, `freshness_window_hours`,
`duplicate_threshold`, `weights`, `timezone`, `output_repository`.
Env overrides: `NEWS_MINIMUM`, `NEWS_MAXIMUM`, `FRESHNESS_WINDOW_HOURS`, `TIMEZONE`, `OUTPUT_REPOSITORY`.

## Automation — 07:00 IST

`.github/workflows/techpulse.yml`:

- cron `30 1 * * *` = 01:30 UTC = 07:00 IST.
- GitHub Actions cron is best-effort (may delay); the report date is always computed in `Asia/Kolkata`, never naive UTC.
- `workflow_dispatch` with optional `target_date` for reruns.
- Required secrets: `OUTPUT_TOKEN` (fine-grained PAT, `contents:write` on `just-userhere/Output` only), `GIT_AUTHOR_EMAIL` (your GitHub-verified email so commits attribute to `just-userhere`).

## Attribution

Set `GIT_AUTHOR_NAME=just-userhere` and `GIT_AUTHOR_EMAIL=<your GitHub-verified email>`.
Commit author alone does not guarantee the contribution graph — the email must match your GitHub account, and the push must use your token. See GitHub Docs: “Why are my contributions not showing up?”.

## Security

- No secrets in code. `.env` is gitignored; only `.env.example` is committed.
- External feeds are parsed, never executed. Timeouts + retries + graceful degradation per source.
- Least-privilege token scoped to the Output repo only.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Repository not found` on Output | repo name/visibility wrong, or token lacks access |
| Empty brief | feeds down or freshness window too tight — check logs, widen `freshness_window_hours` |
| Commits not attributed | `GIT_AUTHOR_EMAIL` must be verified on GitHub |
| Cron late | normal GitHub scheduling skew; date logic still uses IST |
