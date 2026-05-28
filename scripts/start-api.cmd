@echo off
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
  echo Virtualenv not found. Run scripts\setup.cmd first.
  exit /b 1
)
".venv\Scripts\python.exe" -m uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8020

