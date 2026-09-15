"""Dashboard data refresh: builds dashboard/data.json from markdown files (Output is source of truth)."""
from __future__ import annotations

import json
import re
from pathlib import Path


def refresh_dashboard_data(output_root: Path) -> Path:
    months = []
    for d in sorted([x for x in output_root.iterdir() if x.is_dir() and not x.name.startswith(".") and x.name != "dashboard"]):
        days = []
        for f in sorted(d.glob("20*.md")):
            text = f.read_text(encoding="utf-8", errors="ignore")
            titles = re.findall(r"^### \d+\. (.+)", text, re.M)
            cats = re.findall(r"\*\*Category:\*\* (.+)", text)
            days.append({"date": f.stem, "file": f"{d.name}/{f.name}", "count": len(titles),
                         "titles": titles[:5], "categories": cats[:5]})
        months.append({"month": d.name, "days": len(days),
                       "stories": sum(x["count"] for x in days), "reports": days})
    out = output_root / "dashboard" / "data.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"months": months}, indent=2), encoding="utf-8")
    return out
