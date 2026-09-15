@echo off
REM Dry-run preview on Windows
set PYTHONPATH=src
py -m techpulse --dry-run --output-dir "%TEMP%\techpulse-preview"
