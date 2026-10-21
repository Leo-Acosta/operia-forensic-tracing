#requires -Version 7.0
param([Parameter(Mandatory=$true)][string]$Destination)
$ErrorActionPreference='Stop'
# Pinned official artifact, not a mutable latest download. No installation/PATH change.
$version='2.11.7'
$expected='0a1edc0b799512051c57071ce0e798d3f2cf67dc98171366f1d2b326072e3b06'
$Destination=[IO.Path]::GetFullPath($Destination)
if(Test-Path -LiteralPath $Destination){throw 'gateway_new_destination_required'}
New-Item -ItemType Directory -Path $Destination | Out-Null
$archive=Join-Path $Destination 'caddy.zip'
Invoke-WebRequest -Uri "https://github.com/caddyserver/caddy/releases/download/v$version/caddy_${version}_windows_amd64.zip" -OutFile $archive
if((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLower() -ne $expected){throw 'gateway_download_hash_mismatch'}
Expand-Archive -LiteralPath $archive -DestinationPath $Destination
& (Join-Path $Destination 'caddy.exe') version
if($LASTEXITCODE -ne 0){throw 'gateway_binary_check_failed'}
