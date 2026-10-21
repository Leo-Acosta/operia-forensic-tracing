#requires -Version 7.0
param([Parameter(Mandatory=$true)][string]$Root)
$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest
$state=Get-Content -LiteralPath (Join-Path $Root 'data/logs/service-state.json') -Raw | ConvertFrom-Json
if($state.state -ne 'ready'){throw 'network_audit_ready_service_required'}
$supervisor=Get-CimInstance Win32_Process -Filter "ProcessId=$($state.pid)"
if(-not $supervisor -or $supervisor.CommandLine -notmatch 'scripts.windows_service_supervisor'){throw 'network_audit_supervisor_identity_rejected'}
$listeners=@(Get-NetTCPConnection -State Listen)
$owned=@($listeners | Where-Object OwningProcess -eq $state.pid)
if($owned.Count -ne 1 -or $owned[0].LocalAddress -ne '127.0.0.1'){throw 'network_audit_api_not_loopback_only'}
foreach($worker in $state.workers){
    $process=Get-CimInstance Win32_Process -Filter "ProcessId=$worker"
    if(-not $process -or $process.ParentProcessId -ne $state.pid -or $process.CommandLine -notmatch 'scripts.windows_service_worker'){throw 'network_audit_worker_identity_rejected'}
    if(@($listeners | Where-Object OwningProcess -eq $worker).Count -ne 0){throw 'network_audit_worker_tcp_listener'}
    if(@(Get-NetUDPEndpoint | Where-Object OwningProcess -eq $worker).Count -ne 0){throw 'network_audit_worker_udp_listener'}
}
@{schema='operia-network-audit/1';api_loopback_only=$true;workers_without_listeners=$true;generation=$state.generation;port=$owned[0].LocalPort} | ConvertTo-Json
