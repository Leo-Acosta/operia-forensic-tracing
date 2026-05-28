$ErrorActionPreference = "Stop"

Set-Location (Join-Path (Split-Path -Parent $PSScriptRoot) "apps\web")

if (-not (Test-Path "node_modules")) {
    npm install
}

npm run dev -- --host 127.0.0.1 --port 5173

