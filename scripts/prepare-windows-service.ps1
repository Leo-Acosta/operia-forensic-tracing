#requires -Version 7.0
param(
    [Parameter(Mandatory=$true)][string]$Root,
    [Parameter(Mandatory=$true)][string]$Staging,
    [Parameter(Mandatory=$true)][string]$RuntimeSource,
    [Parameter(Mandatory=$true)][ValidatePattern('^S-1-5-21-\d+-\d+-\d+-\d+$')][string]$AccountSid,
    [ValidateRange(1024,65535)][int]$Port=29876,
    [ValidatePattern('^Operia[A-Za-z0-9]{1,40}$')][string]$ServiceName='OperiaE7Validation'
)
$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
if (-not ([Security.Principal.WindowsPrincipal]::new($identity)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {throw 'service_administrator_required'}
$Root=[IO.Path]::GetFullPath($Root).TrimEnd('\')
if ((Split-Path -Parent $Root) -ne [Environment]::GetFolderPath('CommonApplicationData') -or (Split-Path -Leaf $Root) -notmatch '^OPERIA-E7-Service-[A-Za-z0-9-]+$' -or (Test-Path -LiteralPath $Root)) {throw 'service_new_programdata_root_required'}
foreach ($source in @($Staging,$RuntimeSource)) {
    $item=Get-Item -LiteralPath $source
    while ($item) {
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {throw 'service_source_link_rejected'}
        $item=if($item -is [IO.FileInfo]){$item.Directory}else{$item.Parent}
    }
    foreach ($item in Get-ChildItem -LiteralPath $source -Recurse -Force) {
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {throw 'service_source_link_rejected'}
    }
}
$id=(Get-FileHash -LiteralPath (Join-Path $Staging 'layout.json') -Algorithm SHA256).Hash.ToLower().Substring(0,24)
if (-not ('OperiaServiceNative' -as [type])) {Add-Type -Path (Join-Path $PSScriptRoot 'ServiceNative.cs')}
# Restrictive ACL at creation, not after populating a potentially writable tree.
[OperiaServiceNative]::PrivateDirectory($Root)
$release=Join-Path $Root ('releases/'+$id)
foreach ($folder in @('host','config','management','backups','secrets','data/control','data/logs','data/temp','data/memory_vault','data/storage/evidence','data/storage/uploads','data/storage/exports','data/storage/maps','data/storage/temp',('releases/'+$id))) {
    [void](New-Item -ItemType Directory -Path (Join-Path $Root $folder) -Force)
}
Copy-Item -LiteralPath (Join-Path $Staging 'code') -Destination $release -Recurse
Copy-Item -LiteralPath (Join-Path $Staging 'layout.json') -Destination $release
Copy-Item -LiteralPath (Join-Path $RuntimeSource 'runtime') -Destination $release -Recurse
Copy-Item -LiteralPath (Join-Path $RuntimeSource 'runtime-manifest.json') -Destination $release
@{schema='operia-windows-service/1';service_name=$ServiceName;account_sid=$AccountSid;port=$Port;synthetic_only=$true} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Root 'config/service.json') -Encoding utf8
[IO.File]::WriteAllText((Join-Path $Root 'config/active-release.txt'),$id,[Text.Encoding]::ASCII)
$compiler=Join-Path $env:SystemRoot 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
& $compiler /nologo /target:exe /reference:System.ServiceProcess.dll /reference:System.Runtime.Serialization.dll ('/out:'+(Join-Path $Root 'host/Operia.Service.exe')) (Join-Path $release 'code/scripts/OperiaService.cs')
if ($LASTEXITCODE -ne 0) {throw 'service_host_compile_failed'}
& (Join-Path $PSScriptRoot 'manage-windows-service.ps1') -Root $Root -Action Install
