@echo off
setlocal
cd /d "%~dp0..\apps\web"
if not exist "node_modules" npm install
npm run dev -- --host 127.0.0.1 --port 5173

