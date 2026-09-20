@echo off
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe atlas_cli.py serve --out atlas-runs --open
) else (
  py -3 atlas_cli.py serve --out atlas-runs --open
)
pause
