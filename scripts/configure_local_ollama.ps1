# Configure the current user's existing Ollama installation; never pull a model.
[CmdletBinding()]
param([switch]$Restart)
$ErrorActionPreference = 'Stop'
$executable = Join-Path $env:USERPROFILE 'AppData\Local\Programs\Ollama\ollama.exe'
$configPath = Join-Path $env:USERPROFILE '.ollama\server.json'
if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) { throw 'Install Ollama from its official distribution first.' }
$config = if (Test-Path -LiteralPath $configPath) {
    Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json -AsHashtable
} else { @{} }
if ($config -isnot [System.Collections.IDictionary]) { throw 'Expected an object in server.json.' }
$config['disable_ollama_cloud'] = $true
[IO.Directory]::CreateDirectory((Split-Path $configPath)) | Out-Null
[IO.File]::WriteAllText($configPath, ($config | ConvertTo-Json -Depth 100))
$policy = @{ OLLAMA_HOST='127.0.0.1:11434'; OLLAMA_NO_CLOUD='1'; OLLAMA_NUM_PARALLEL='1'; OLLAMA_MAX_LOADED_MODELS='1' }
foreach ($entry in $policy.GetEnumerator()) {
    [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, 'User')
    [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, 'Process')
}
if ($Restart) {
    $listeners = @(Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue)
    $owners = @($listeners | Select-Object -ExpandProperty OwningProcess -Unique)
    foreach ($ownerId in $owners) {
        if ((Get-Process -Id $ownerId).Path -ne $executable) { throw 'Port belongs to another executable; refusing to stop it.' }
    }
    foreach ($ownerId in $owners) { Stop-Process -Id $ownerId }
    $logDirectory = Join-Path $PSScriptRoot '..\storage\temp'
    [IO.Directory]::CreateDirectory($logDirectory) | Out-Null
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss-ffff'
    Start-Process -FilePath $executable -ArgumentList 'serve' -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logDirectory "ollama-$stamp.stdout.log") `
        -RedirectStandardError (Join-Path $logDirectory "ollama-$stamp.stderr.log")
}
Write-Output 'Local-only policy saved. Verify the listener and cloud-disabled log after restart; OPERIA grants remain explicit.'
