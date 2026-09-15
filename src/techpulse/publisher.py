"""Idempotent publisher: writes monthly report + README, commits YYYY-MM-DD.

Supports two modes:
- local path mode (tests / dry-run preview / local Output checkout)
- remote mode (CI): clones OUTPUT_REPOSITORY with OUTPUT_TOKEN, pushes.
Never hardcodes credentials; token only from env.
"""
from __future__ import annotations

import logging
import os
import subprocess
from datetime import date
from pathlib import Path

from .formatter import generate_report, month_folder, report_filename, update_output_readme

log = logging.getLogger("techpulse.publisher")


def _run(cmd: list[str], cwd: Path | None = None) -> str:
    r = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed: {r.stderr.strip()}")
    return r.stdout.strip()


def _ensure_git_identity(repo: Path) -> None:
    name = os.environ.get("GIT_AUTHOR_NAME", "just-userhere")
    email = os.environ.get("GIT_AUTHOR_EMAIL", "")
    if not email:
        log.warning("GIT_AUTHOR_EMAIL not set — GitHub may not attribute the commit. "
                    "Set it to your GitHub-verified email (see Engine README).")
        email = f"{name}@users.noreply.github.com"
    _run(["git", "config", "user.name", name], cwd=repo)
    _run(["git", "config", "user.email", email], cwd=repo)


def publish_local(output_root: Path, report_date: date, stories: list[dict]) -> dict:
    """Write report into an existing Output checkout. Safe rerun: skips identical content."""
    month = month_folder(report_date)
    month_dir = output_root / month
    month_dir.mkdir(parents=True, exist_ok=True)
    target = month_dir / report_filename(report_date)
    body = generate_report(report_date, stories)
    if target.exists() and target.read_text(encoding="utf-8") == body:
        log.info("report %s already up to date — no write", target)
        changed = False
    else:
        target.write_text(body, encoding="utf-8")
        changed = True
    readme = update_output_readme(output_root)
    readme_path = output_root / "README.md"
    if not readme_path.exists() or readme_path.read_text(encoding="utf-8") != readme:
        readme_path.write_text(readme, encoding="utf-8")
        changed = True
    # dashboard data (source of truth stays the markdown files)
    try:
        from .dashboard import refresh_dashboard_data
        refresh_dashboard_data(output_root)
    except Exception as e:  # noqa: BLE001
        log.warning("dashboard refresh skipped: %s", e)
    return {"path": str(target), "changed": changed, "commit": report_date.isoformat()}


def commit_and_push(output_root: Path, report_date: date, suffix: str = "") -> str:
    _ensure_git_identity(output_root)
    _run(["git", "add", "-A"], cwd=output_root)
    status = _run(["git", "status", "--porcelain"], cwd=output_root)
    if not status:
        log.info("nothing to commit")
        return ""
    msg = report_date.isoformat() + (suffix or "")
    _run(["git", "commit", "-m", msg], cwd=output_root)
    # push only when a token/remote is configured (CI); local runs may have no remote
    try:
        _run(["git", "push", "origin", "HEAD"], cwd=output_root)
    except Exception as e:  # noqa: BLE001
        log.warning("push skipped/failed (ok for local runs): %s", e)
    return msg


def publish_remote(engine_root: Path, report_date: date, stories: list[dict], workdir: Path) -> dict:
    token = os.environ.get("OUTPUT_TOKEN", "")
    repo = os.environ.get("OUTPUT_REPOSITORY", "just-userhere/Output")
    if not token:
        raise RuntimeError("OUTPUT_TOKEN secret is not set")
    clone_url = f"https://x-access-token:{token}@github.com/{repo}.git"
    dest = workdir / "Output"
    if dest.exists():
        _run(["git", "fetch", "origin"], cwd=dest)
        _run(["git", "checkout", "main"], cwd=dest)
        _run(["git", "pull", "--rebase", "origin", "main"], cwd=dest)
    else:
        _run(["git", "clone", "--depth", "1", "--branch", "main", clone_url, str(dest)])
    # mask token in any stored remote
    _run(["git", "remote", "set-url", "origin", f"https://github.com/{repo}.git"], cwd=dest)
    res = publish_local(dest, report_date, stories)
    if res["changed"]:
        # handle same-date reruns: if date commit exists, suffix -01/-02
        suffix = ""
        try:
            existing = _run(["git", "log", "--format=%s"], cwd=dest)
            if report_date.isoformat() in existing.splitlines():
                n = 1
                while f"{report_date.isoformat()}-{n:02d}" in existing:
                    n += 1
                suffix = f"-{n:02d}"
        except Exception:
            pass
        res["commit"] = commit_and_push(dest, report_date, suffix)
    # restore authenticated push URL just for push, then mask again
    try:
        _run(["git", "remote", "set-url", "origin", clone_url], cwd=dest)
        _run(["git", "push", "origin", "HEAD:main"], cwd=dest)
    finally:
        try:
            _run(["git", "remote", "set-url", "origin", f"https://github.com/{repo}.git"], cwd=dest)
        except Exception:
            pass
    return res
