"""CLI: python -m techpulse --dry-run [--target-date YYYY-MM-DD] [--output-dir PATH]"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    ap = argparse.ArgumentParser(prog="techpulse")
    ap.add_argument("--dry-run", action="store_true", help="fetch/process/generate but do not publish")
    ap.add_argument("--target-date", default=None, help="YYYY-MM-DD in Asia/Kolkata (testing/recovery)")
    ap.add_argument("--output-dir", default=None, help="local Output checkout path (preview/publish-local)")
    ap.add_argument("--live", action="store_true", help="publish via OUTPUT_TOKEN to OUTPUT_REPOSITORY")
    args = ap.parse_args(argv)
    engine_root = Path(__file__).resolve().parents[2]
    from .pipeline import run
    out = Path(args.output_dir) if args.output_dir else None
    if args.dry_run and out is None:
        import tempfile
        out = Path(tempfile.mkdtemp(prefix="techpulse-preview-"))
    res = run(engine_root, dry_run=args.dry_run or not args.live, target_date=args.target_date,
              output_dir=out if (args.dry_run or not args.live) else None)
    print(f"report_date={res['report_date']} selected={res['stats']['selected']} "
          f"collected={res['stats']['collected']}")
    if res.get("preview"):
        print(f"preview: {res['preview']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
