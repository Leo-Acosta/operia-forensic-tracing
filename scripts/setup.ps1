$ErrorActionPreference = "Stop"

Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

Push-Location apps\web
if (-not (Test-Path "node_modules")) {
    npm install
}
Pop-Location

Write-Host "OPERIA setup completed." -ForegroundColor Green
Write-Host "Backend: .\scripts\start-api.ps1"
Write-Host "Frontend: .\scripts\start-web.ps1"

