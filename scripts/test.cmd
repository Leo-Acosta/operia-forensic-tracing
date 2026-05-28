@echo off
setlocal
cd /d "%~dp0.."
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m pytest -q -p no:cacheprovider
) else (
  python -m pytest -q -p no:cacheprovider
)

