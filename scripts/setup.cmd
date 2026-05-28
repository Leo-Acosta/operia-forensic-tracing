@echo off
setlocal
cd /d "%~dp0.."
if not exist ".venv" python -m venv .venv
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
cd apps\web
if not exist "node_modules" npm install
cd /d "%~dp0.."
echo OPERIA setup completed.

