$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
if ($env:OPERIA_ENV -ne "production") {
    throw "Set OPERIA_ENV=production explicitly; this launcher does not modify the local configuration."
}
& .\.venv\Scripts\python.exe scripts/production_audit.py
if ($LASTEXITCODE -ne 0) { throw "Minimum production policy rejected. Review finding codes before starting." }
# Single local supervisor behind an independently configured TLS gateway; never --reload.
& .\.venv\Scripts\python.exe -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8020 --workers 1 --no-proxy-headers
exit $LASTEXITCODE
