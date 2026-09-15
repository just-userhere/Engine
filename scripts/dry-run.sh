#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=src
python -m techpulse --dry-run --output-dir "${1:-/tmp/techpulse-preview}"
