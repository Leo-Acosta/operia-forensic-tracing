$ErrorActionPreference = "Stop"

Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Backend dependency installation failed" }
.\.venv\Scripts\python.exe scripts\prepare_worker_sandbox.py
if ($LASTEXITCODE -ne 0) { throw "Windows worker isolation could not be prepared" }

Push-Location apps\web
if (-not (Test-Path "node_modules")) {
    npm install
}
Pop-Location

Write-Host "OPERIA setup completed." -ForegroundColor Green
Write-Host "Backend: .\scripts\start-api.ps1"
Write-Host "Frontend: .\scripts\start-web.ps1"

