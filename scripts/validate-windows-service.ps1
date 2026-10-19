#requires -Version 7.0
param([Parameter(Mandatory=$true)][string]$Root,[switch]$IncludeFaultInjection,
    [ValidateSet('Full','CredentialRollback')][string]$Scenario='Full')
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if (-not $IncludeFaultInjection) {throw 'service_validation_requires_explicit_synthetic_fault_injection_switch'}
$repo=Split-Path -Parent $PSScriptRoot
$Root=[IO.Path]::GetFullPath($Root).TrimEnd('\')
$manager=Join-Path $repo 'scripts/manage-windows-service.ps1'
$python=Join-Path $repo '.venv/Scripts/python.exe'
$result=@{schema='operia-scm-lifecycle/1';status='incomplete';checks=@{}}
function State {return (Get-Content -LiteralPath (Join-Path $Root 'data/logs/service-state.json') -Raw | ConvertFrom-Json)}
function Manage([string]$Action,[string]$Release='') {
    if ($Release) {& $manager -Root $Root -Action $Action -Release $Release | Out-Null}
    else {& $manager -Root $Root -Action $Action | Out-Null}
}
function History {
    & $python -B -m scripts.windows_service_trial $Root history | Out-Null
    if ($LASTEXITCODE -ne 0) {throw 'scm_history_verification_failed'}
}
function Candidate([string]$Base,[string]$Marker,[bool]$Broken=$false,[bool]$FailMigration=$false) {
    if ($Base -notmatch '^[a-f0-9]{24}$') {throw 'service_validation_release_invalid'}
    $id=([Guid]::NewGuid().ToString('N')).Substring(0,24)
    $destination=Join-Path $Root ('releases/'+$id)
    New-Item -ItemType Directory -Path $destination | Out-Null
    foreach ($part in @('code','runtime','layout.json','runtime-manifest.json')) {Copy-Item -LiteralPath (Join-Path $Root ('releases/'+$Base+'/'+$part)) -Destination $destination -Recurse}
    $layoutPath=Join-Path $destination 'layout.json'; $layout=Get-Content -LiteralPath $layoutPath -Raw | ConvertFrom-Json
    $file=Join-Path $destination 'code/service-version-marker.py'; [IO.File]::WriteAllText($file,('# '+$Marker))
    $layout.code_files | Add-Member -MemberType NoteProperty -Name 'service-version-marker.py' -Value (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLower() -Force
    if ($Broken) {
        $file=Join-Path $destination 'code/scripts/windows_service_supervisor.py'
        [IO.File]::WriteAllText($file,'raise SystemExit(23)')
        $layout.code_files.'scripts/windows_service_supervisor.py'=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLower()
    }
    if ($FailMigration) {
        $file=Join-Path $destination 'code/operia/security/service_dpapi.py'
        $content=[IO.File]::ReadAllText($file)
        $needle='raw=c.create_string_buffer(length.value+2);read_into(raw,length.value)'
        if (-not $content.Contains($needle)) {throw 'service_validation_injection_context_missing'}
        [IO.File]::WriteAllText($file,$content.Replace($needle,$needle+"`n        raise RuntimeError('service_synthetic_migration_failure')"))
        $layout.code_files.'operia/security/service_dpapi.py'=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLower()
    }
    $layout | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $layoutPath -Encoding utf8
    return $id
}
function TestMigrationRollback {
    $canary=(Get-FileHash -LiteralPath (Join-Path $Root 'data/control/credential-canary-v3.dpapi') -Algorithm SHA256).Hash
    $result.stage='migration_failure_rollback'; $original=(State).release
    $failureCandidate=Candidate $original 'Synthetic migration failure' $false $true
    Manage Update $failureCandidate
    $rejected=$false
    try {Manage Rotate} catch {$rejected=$true}
    if (-not $rejected) {throw 'scm_migration_fault_did_not_block_rotation'}
    $recovered=& $manager -Root $Root -Action RecoverCredential | ConvertFrom-Json
    if ($recovered.recovery_outcome -ne 'rolled_back_previous_preserving_dpapi') {throw 'scm_previous_credential_not_recovered'}
    Manage Start; History
    if ($canary -ne (Get-FileHash -LiteralPath (Join-Path $Root 'data/control/credential-canary-v3.dpapi') -Algorithm SHA256).Hash) {throw 'scm_rollback_canary_changed'}
    Manage Update $original; History
    $result.checks.failed_migration_previous_credential_and_same_dpapi_recovered=$true
}
Manage Status  # Checks elevation, synthetic-only config, SID, groups and SCM binding.
$config=Get-Content -LiteralPath (Join-Path $Root 'config/service.json') -Raw | ConvertFrom-Json
$credentialTarget='OPERIA/service/'+$config.service_name
$activeId=[IO.File]::ReadAllText((Join-Path $Root 'config/active-release.txt')).Trim()
if ($activeId -notmatch '^[a-f0-9]{24}$') {throw 'service_validation_release_invalid'}
foreach ($file in @('operia/security/service_control.py','operia/security/service_dpapi.py','operia/security/private_desktop.py',
    'operia/security/windows_sandbox.py','operia/security/sandbox_runtime.py','operia/static_lab/runtime.py',
    'scripts/sandbox_probe.py','scripts/windows_service_supervisor.py','scripts/windows_service_worker.py','scripts/windows_service_admin.py')) {
    if ((Get-FileHash -LiteralPath (Join-Path $repo $file) -Algorithm SHA256).Hash -ne
        (Get-FileHash -LiteralPath (Join-Path $Root ('releases/'+$activeId+'/code/'+$file)) -Algorithm SHA256).Hash) {
        throw 'service_validation_publish_current_snapshot_first'
    }
}
function CrashOwnSupervisor($State) {
    $processId=[int]$State.pid
    if ($processId -le 0) {throw 'service_validation_pid_invalid'}
    $svc=Get-CimInstance Win32_Service -Filter ("Name='"+$config.service_name+"'")
    $process=Get-CimInstance Win32_Process -Filter ('ProcessId='+$processId)
    $expected=Join-Path $Root ('releases/'+$activeId+'/runtime/python.exe')
    if (-not $process -or $process.ExecutablePath -ne $expected -or $process.ParentProcessId -ne $svc.ProcessId -or
        $process.CommandLine -notmatch ' -B -m scripts\.windows_service_supervisor$') {throw 'service_validation_process_scope_rejected'}
    $owner=Invoke-CimMethod -InputObject $process -MethodName GetOwnerSid
    if ($owner.ReturnValue -ne 0 -or $owner.Sid -ne $config.account_sid) {throw 'service_validation_process_owner_rejected'}
    Stop-Process -Id $processId -Force
}
try {
    Push-Location -LiteralPath $repo
    Manage Start
    if ($Scenario -eq 'CredentialRollback') {TestMigrationRollback}
    else {
    $result.stage='acceptance'
    if (Test-Path -LiteralPath (Join-Path $Root 'management/acceptance.json')) {History}
    else {
        & $python -B -m scripts.windows_service_trial $Root 1> (Join-Path $Root 'management/acceptance.stdout') 2> (Join-Path $Root 'management/acceptance.stderr')
        if ($LASTEXITCODE -ne 0) {throw 'scm_api_acceptance_failed'}
    }
    $result.checks.api_case_custody_workers=$true
    $result.stage='restart'; $before=State; Manage Restart; $after=State
    if ($before.generation -eq $after.generation) {throw 'scm_restart_generation_unchanged'}
    foreach ($processId in @($before.pid)+@($before.workers)) {if (Get-Process -Id $processId -ErrorAction SilentlyContinue) {throw 'scm_old_process_survived_restart'}}
    History; $result.checks.graceful_restart_and_tree_cleanup=$true
    $result.stage='crash_recovery'; $before=State
    # Isolate this synthetic crash from the accumulated failures of earlier probes.
    # The normal bounded 24h recovery policy is always restored, including on error.
    try {
        [OperiaServiceNative]::SetRecoveryReset($config.service_name,0)
        CrashOwnSupervisor $before
        $deadline=[DateTime]::UtcNow.AddSeconds(100)
        do {Start-Sleep -Milliseconds 500; $after=State} while (($after.generation -eq $before.generation -or $after.state -ne 'ready') -and [DateTime]::UtcNow -lt $deadline)
        if ($after.generation -eq $before.generation -or $after.state -ne 'ready') {throw 'scm_recovery_timeout'}
    } finally {[OperiaServiceNative]::SetRecoveryReset($config.service_name,86400)}
    History; $result.checks.scm_automatic_crash_recovery=$true
    $result.stage='rotation'; $canary=(Get-FileHash -LiteralPath (Join-Path $Root 'data/control/credential-canary-v3.dpapi') -Algorithm SHA256).Hash
    Manage Rotate; $after=State
    if ($canary -ne (Get-FileHash -LiteralPath (Join-Path $Root 'data/control/credential-canary-v3.dpapi') -Algorithm SHA256).Hash -or $after.state -ne 'ready') {throw 'scm_dpapi_rotation_failed'}
    History; $result.checks.credential_rotation_and_dpapi_preservation=$true
    $result.stage='pending_credential_recovery'; Manage Stop
    $active=[OperiaServiceNative]::Read($credentialTarget+'/active')
    if (-not $active) {throw 'service_validation_active_credential_missing'}
    $next=[OperiaServiceNative]::NewPassword()
    try {
        [OperiaServiceNative]::Store($credentialTarget+'/previous','.\OperiaSvc',$active)
        [OperiaServiceNative]::Store($credentialTarget+'/pending','.\OperiaSvc',$next)
        Enable-LocalUser -Name OperiaSvc
        [OperiaServiceNative]::ChangePassword('OperiaSvc',$active,$next)
    } finally {$active.Dispose(); $next.Dispose(); Disable-LocalUser -Name OperiaSvc}
    $rejected=$false
    try {Manage Start} catch {if ($_.Exception.Message -notlike '*pending_credential*') {throw}; $rejected=$true}
    if (-not $rejected) {throw 'scm_pending_credential_did_not_block'}
    Manage RecoverCredential; Manage Start; History; $result.checks.pending_credential_recovery=$true
    TestMigrationRollback
    $result.stage='update'; $original=(State).release
    $candidate=Candidate $original 'Synthetic accepted update'
    Manage Update $candidate
    if ((State).release -ne $candidate) {throw 'scm_update_not_selected'}
    History; $result.checks.version_update_with_verified_backup=$true
    $result.stage='tampered_candidate'; $tampered=Candidate $original 'Synthetic tamper rejection'
    [IO.File]::AppendAllText((Join-Path $Root ('releases/'+$tampered+'/code/service-version-marker.py')),'tamper')
    $generation=(State).generation; $rejected=$false
    try {Manage Update $tampered} catch {if ($_.Exception.Message -notlike '*integrity*' -and $_.Exception.Message -notlike '*hash*') {throw}; $rejected=$true}
    if (-not $rejected -or (State).generation -ne $generation) {throw 'scm_tampered_update_not_rejected_before_stop'}
    $result.checks.tampered_update_rejected_before_stop=$true
    $result.stage='failed_candidate_rollback'; $broken=Candidate $original 'Synthetic invalid startup' $true
    $rejected=$false
    try {Manage Update $broken} catch {if ($_.Exception.Message -notlike '*previous_release_restarted*') {throw}; $rejected=$true}
    if (-not $rejected -or (State).release -ne $candidate) {throw 'scm_update_rollback_failed'}
    History; $result.checks.failed_startup_rollback_preserves_database=$true
    $result.stage='interrupted_update_recovery'
    @{schema='operia-service-update-pending/1';previous=$candidate;candidate=$broken;backup_sha256=('0'*64)} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Root 'management/update-pending.json') -Encoding utf8
    [IO.File]::WriteAllText((Join-Path $Root 'config/active-release.txt'),$broken,[Text.Encoding]::ASCII)
    $rejected=$false
    try {Manage Start} catch {if ($_.Exception.Message -notlike '*pending_update*') {throw}; $rejected=$true}
    if (-not $rejected) {throw 'scm_interrupted_update_did_not_block'}
    Manage RecoverUpdate
    if ((State).release -ne $candidate) {throw 'scm_interrupted_update_not_recovered'}
    History; $result.checks.interrupted_update_recovery=$true
    }
    $result.stage='final'; $result.status='passed'
} catch {
    $result.status='failed'; $result.error=$_.Exception.Message; $result.line=$_.InvocationInfo.ScriptLineNumber; $result.script=$_.InvocationInfo.ScriptName
} finally {
    try {Manage Stop; $result.service_stopped=$true} catch {$result.stop_error=$_.Exception.Message}
    $result.account_disabled=-not (Get-LocalUser -Name OperiaSvc).Enabled
    $report=if($Scenario -eq 'Full'){'lifecycle-validation.json'}else{'credential-rollback-validation.json'}
    $result.scenario=$Scenario
    $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $Root ('management/'+$report)) -Encoding utf8
    Pop-Location
}
if ($result.status -ne 'passed') {throw 'service_lifecycle_validation_failed_check_report'}
$result | ConvertTo-Json -Depth 8
