#requires -Version 7.0
param(
    [Parameter(Mandatory=$true)][string]$Root,
    [Parameter(Mandatory=$true)][ValidateSet('Install','Harden','Start','Stop','Restart','Rotate','RecoverCredential','Update','RecoverUpdate','Status')][string]$Action,
    [ValidatePattern('^[a-f0-9]{24}$')][string]$Release
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
Import-Module (Join-Path $PSHOME 'Modules/Microsoft.PowerShell.Security/Microsoft.PowerShell.Security.psd1')
if (-not [Environment]::Is64BitProcess) { throw 'service_64bit_required' }
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
if (-not ([Security.Principal.WindowsPrincipal]::new($identity)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'service_administrator_required' }
function NoLinks([string]$Path) {
    $item=Get-Item -LiteralPath $Path -Force
    while ($null -ne $item) {
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'service_reparse_rejected' }
        $item=if ($item -is [IO.FileInfo]) {$item.Directory} else {$item.Parent}
    }
}
$Root=[IO.Path]::GetFullPath($Root).TrimEnd('\'); NoLinks $Root
if ((Split-Path -Parent $Root) -ne [Environment]::GetFolderPath('CommonApplicationData') -or (Split-Path -Leaf $Root) -notmatch '^OPERIA-E7-Service-[A-Za-z0-9-]+$') {throw 'service_programdata_root_required'}
$config=Get-Content -LiteralPath (Join-Path $Root 'config/service.json') -Raw | ConvertFrom-Json
if ($config.schema -ne 'operia-windows-service/1' -or $config.synthetic_only -ne $true -or $config.service_name -notmatch '^Operia[A-Za-z0-9]{1,40}$' -or $config.account_sid -notmatch '^S-1-5-21-\d+-\d+-\d+-\d+$') { throw 'service_config_invalid' }
$name=$config.service_name; $sid=$config.account_sid
$expectedBinary='"'+(Join-Path $Root 'host/Operia.Service.exe')+'" "'+$Root+'" '+$name
if ($Action -ne 'Install') {
    $registered=Get-CimInstance Win32_Service -Filter ("Name='"+$name+"'")
    if ($registered -and ($registered.PathName -ne $expectedBinary -or $registered.StartName -ne '.\OperiaSvc')) {throw 'service_registration_mismatch'}
    if (-not $registered -and $Action -notin @('Status','RecoverCredential')) {throw 'service_not_installed'}
}
$base=Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/Modules/Microsoft.PowerShell.LocalAccounts'
$modules=@(Get-ChildItem -LiteralPath $base -Filter Microsoft.PowerShell.LocalAccounts.psd1 -Recurse)
if ($modules.Count -ne 1) { throw 'service_localaccounts_module_ambiguous' }
Import-Module $modules[0].FullName
$user=Get-LocalUser -Name OperiaSvc
if ($user.SID.Value -ne $sid -or $user.Description -ne 'OPERIA staged least-privilege identity') { throw 'service_account_identity_invalid' }
$groups=@(Get-LocalGroup | Where-Object {@(Get-LocalGroupMember -SID $_.SID | Where-Object {$_.SID -eq $user.SID}).Count})
if ($groups.Count -ne 1 -or $groups[0].SID.Value -ne 'S-1-5-32-545') { throw 'service_account_groups_invalid' }
$others=@(Get-CimInstance Win32_Service | Where-Object {$_.StartName -match '(^|\\)OperiaSvc$' -and $_.Name -ne $name})
if ($others.Count) { throw 'service_account_shared_rejected' }
if (-not ('OperiaServiceNative' -as [type])) { Add-Type -Path (Join-Path $PSScriptRoot 'ServiceNative.cs') }
if (-not ('OperiaMigrationPipe' -as [type])) { Add-Type -Path (Join-Path $PSScriptRoot 'ServiceMigrationPipe.cs') }
$target='OPERIA/service/'+$name
$admin=[Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'); $system=[Security.Principal.SecurityIdentifier]::new('S-1-5-18')
function ProtectTree([string]$Path,[string]$Rights,[bool]$Private=$false,[bool]$Apps=$false) {
    NoLinks $Path
    foreach ($item in Get-ChildItem -LiteralPath $Path -Recurse -Force) {
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {throw 'service_reparse_rejected'}
    }
    $acl=[Security.AccessControl.DirectorySecurity]::new(); $acl.SetAccessRuleProtection($true,$false); $acl.SetOwner($admin)
    foreach ($principal in @($admin,$system)) { $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($principal,'FullControl','ContainerInherit, ObjectInherit','None','Allow')) }
    if ($Rights) { $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($user.SID,$Rights,'ContainerInherit, ObjectInherit','None','Allow')) }
    if (-not $Private) { $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($identity.User,'FullControl','ContainerInherit, ObjectInherit','None','Allow')) }
    if ($Apps) { $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new('S-1-15-2-1'),'ReadAndExecute','ContainerInherit, ObjectInherit','None','Allow')) }
    Set-Acl -LiteralPath $Path -AclObject $acl
    foreach ($child in Get-ChildItem -LiteralPath $Path -Force) {
        & (Join-Path $env:SystemRoot 'System32/icacls.exe') $child.FullName /reset /T /Q | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'service_acl_failed' }
    }
}
function CurrentRelease {
    $value=[IO.File]::ReadAllText((Join-Path $Root 'config/active-release.txt')).Trim()
    if ($value -notmatch '^[a-f0-9]{24}$') { throw 'service_release_invalid' }; return $value
}
function VerifyRelease([string]$Id) {
    if ($Id -notmatch '^[a-f0-9]{24}$') {throw 'service_release_invalid'}
    $folder=Join-Path $Root ('releases/'+$Id); NoLinks $folder
    $layout=Get-Content -LiteralPath (Join-Path $folder 'layout.json') -Raw | ConvertFrom-Json
    $runtime=Get-Content -LiteralPath (Join-Path $folder 'runtime-manifest.json') -Raw | ConvertFrom-Json
    if ($layout.schema -ne 'operia-service-staging/1' -or $runtime.schema -ne 'operia-service-runtime/1') {throw 'service_manifest_invalid'}
    foreach ($pair in @(@('code',$layout.code_files),@('runtime',$runtime.files))) {
        $tree=Join-Path $folder $pair[0]; $entries=@($pair[1].PSObject.Properties)
        NoLinks $tree
        foreach ($item in Get-ChildItem -LiteralPath $tree -Recurse -Force) {
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {throw 'service_reparse_rejected'}
        }
        if (@(Get-ChildItem -LiteralPath $tree -Recurse -Force -File).Count -ne $entries.Count) {throw 'service_inventory_mismatch'}
        foreach ($entry in $entries) {
            if ($entry.Name -match '(^/|\\|:|(^|/)\.\.?(/|$))' -or $entry.Value -notmatch '^[a-f0-9]{64}$') {throw 'service_manifest_path_invalid'}
            $path=Join-Path $tree $entry.Name
            # Ntfs hardlinks are rejected by the Python verifier before launch too.
            if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $entry.Value) {throw 'service_file_hash_mismatch'}
        }
    }
}
function Python([string]$Id,[string[]]$Arguments) {
    VerifyRelease $Id
    $folder=Join-Path $Root ('releases/'+$Id); NoLinks $folder
    $info=[Diagnostics.ProcessStartInfo]::new(); $info.FileName=Join-Path $folder 'runtime/python.exe'
    $info.WorkingDirectory=Join-Path $folder 'code'; $info.UseShellExecute=$false; $info.CreateNoWindow=$true
    $info.RedirectStandardOutput=$true; $info.RedirectStandardError=$true
    $info.Environment.Clear()
    foreach ($key in @('SystemRoot','WINDIR','USERPROFILE','LOCALAPPDATA','APPDATA')) { $value=[Environment]::GetEnvironmentVariable($key); if ($value) {$info.Environment[$key]=$value} }
    $info.Environment['PATH']=(Join-Path $folder 'runtime')+';'+(Join-Path $env:SystemRoot 'System32')
    $info.Environment['TEMP']=Join-Path $Root 'data/temp'; $info.Environment['TMP']=Join-Path $Root 'data/temp'
    foreach ($arg in @('-B','-m','scripts.windows_service_admin',$Root)+$Arguments) { $info.ArgumentList.Add($arg) }
    $process=[Diagnostics.Process]::new(); $process.StartInfo=$info
    try {
        [void]$process.Start(); $stdout=$process.StandardOutput.ReadToEndAsync(); $stderr=$process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(180000)) { $process.Kill($true); throw 'service_admin_python_timeout' }
        if ($process.ExitCode -ne 0) { throw ('service_admin_python_failed_'+$stderr.GetAwaiter().GetResult()) }
        return ($stdout.GetAwaiter().GetResult() | ConvertFrom-Json)
    } finally {$process.Dispose()}
}
function StopManaged {
    $svc=Get-Service -Name $name -ErrorAction SilentlyContinue
    if ($svc -and $svc.Status -ne 'Stopped') { Stop-Service -Name $name; $svc.WaitForStatus('Stopped',[TimeSpan]::FromSeconds(100)) }
    Disable-LocalUser -SID $user.SID
}
function StartManaged {
    VerifyRelease (CurrentRelease)
    Enable-LocalUser -SID $user.SID
    try {
        $current=Get-Service -Name $name
        if ($current.Status -eq 'Stopped') {Start-Service -Name $name}
        elseif ($current.Status -notin @('Running','StartPending')) {throw 'service_state_not_startable'}
        $svc=Get-Service -Name $name; $svc.WaitForStatus('Running',[TimeSpan]::FromSeconds(120))
        $state=Get-Content -LiteralPath (Join-Path $Root 'data/logs/service-state.json') -Raw | ConvertFrom-Json
        if ($state.state -ne 'ready' -or $state.release -ne (CurrentRelease)) { throw 'service_readiness_invalid' }
        return $state
    } catch { StopManaged; throw }
}
function SelectRelease([string]$Id) {
    $path=Join-Path $Root 'config/active-release.txt'; $temporary=$path+'.new'
    $stream=[IO.FileStream]::new($temporary,[IO.FileMode]::Create,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try { $bytes=[Text.Encoding]::ASCII.GetBytes($Id); $stream.Write($bytes,0,$bytes.Length); $stream.Flush($true) } finally {$stream.Dispose()}
    [IO.File]::Move($temporary,$path,$true)
}
function Journal([string]$Stage) {
    $record=@{schema='operia-service-management/1'; action=$Action; stage=$Stage; utc=[DateTime]::UtcNow.ToString('o')}
    $path=Join-Path $Root 'management/journal.jsonl'
    $bytes=[Text.Encoding]::UTF8.GetBytes(($record | ConvertTo-Json -Compress)+"`n")
    $stream=[IO.FileStream]::new($path,[IO.FileMode]::Append,[IO.FileAccess]::Write,[IO.FileShare]::Read)
    try {$stream.Write($bytes,0,$bytes.Length); $stream.Flush($true)} finally {$stream.Dispose()}
}
$updatePending=Join-Path $Root 'management/update-pending.json'
if ($Action -eq 'Install') {
    if ($user.Enabled -or (Get-Service -Name $name -ErrorAction SilentlyContinue)) { throw 'service_install_requires_disabled_fresh_identity' }
    ProtectTree $Root 'ReadAndExecute'
    foreach ($folder in @('storage','memory_vault','logs','temp','control')) { ProtectTree (Join-Path $Root ('data/'+$folder)) 'Modify' }
    ProtectTree (Join-Path $Root 'secrets') 'ReadAndExecute' $true
}
if ($Action -in @('Install','Harden')) {
    # The DPAPI recovery validator requires the operator's explicit private ACE.
    # Neither directory grants the service SID access.
    ProtectTree (Join-Path $Root 'management') ''
    ProtectTree (Join-Path $Root 'backups') ''
}
$lock=[IO.FileStream]::new((Join-Path $Root 'management/operation.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try {
    Journal 'begun'
    if ((Test-Path -LiteralPath $updatePending) -and $Action -notin @('Stop','RecoverCredential','RecoverUpdate','Status')) {throw 'service_pending_update_requires_recovery'}
    if ($Action -notin @('Install','Stop','RecoverCredential','Status')) {
        # Pending means a crash could have occurred after SAM changed. Do not guess.
        $pending=[OperiaServiceNative]::Read($target+'/pending')
        if ($pending) {$pending.Dispose(); throw 'service_pending_credential_requires_recovery'}
    }
    switch ($Action) {
        Install {
            $id=CurrentRelease
            $verified=Python $id @('verify',$id)
            $prepared=Python $id @('prepare')
            foreach ($folder in @('sandbox-runtime','static-lab-runtime')) { ProtectTree (Join-Path $Root ('data/storage/'+$folder)) 'ReadAndExecute' $false $true }
            $key=Join-Path $Root 'secrets/synthetic-signing-key.bin'
            if (Test-Path -LiteralPath $key) { throw 'service_install_requires_empty_secret' }
            $bytes=[byte[]]::new(32); $rng=[Security.Cryptography.RandomNumberGenerator]::Create(); $rng.GetBytes($bytes); $rng.Dispose(); [IO.File]::WriteAllBytes($key,$bytes); [Array]::Clear($bytes,0,$bytes.Length)
            $acl=Get-Acl -LiteralPath $key; $acl.SetOwner($admin); Set-Acl -LiteralPath $key -AclObject $acl
            [OperiaServiceNative]::Rights($sid)
            $password=[OperiaServiceNative]::NewPassword()
            try {
                [OperiaServiceNative]::Store($target+'/pending','.\OperiaSvc',$password); Journal 'bootstrap_credential_staged'
                Set-LocalUser -SID $user.SID -Password $password
                Set-LocalUser -SID $user.SID -PasswordNeverExpires $true
                [OperiaServiceNative]::Configure($name,$expectedBinary,'OperiaSvc',$password,$true)
                [OperiaServiceNative]::Store($target+'/active','.\OperiaSvc',$password)
                [OperiaServiceNative]::Delete($target+'/pending'); Journal 'installed_manual_disabled'
            } finally {$password.Dispose(); Disable-LocalUser -SID $user.SID}
        }
        Start {$null=StartManaged}
        Harden {
            StopManaged; $password=[OperiaServiceNative]::Read($target+'/active')
            if (-not $password) {throw 'service_active_credential_missing'}
            try {[OperiaServiceNative]::Configure($name,$null,'OperiaSvc',$password,$false)} finally {$password.Dispose()}
        }
        Stop {StopManaged}
        Restart {StopManaged; $null=StartManaged}
        Rotate {
            $canaryPath=Join-Path $Root 'data/control/credential-canary-v3.dpapi'
            if (-not (Test-Path -LiteralPath $canaryPath -PathType Leaf)) {throw 'service_existing_dpapi_canary_required'}
            $canaryHash=(Get-FileHash -LiteralPath $canaryPath -Algorithm SHA256).Hash
            $running=(Get-Service -Name $name).Status -eq 'Running'
            # Keep the old service logon/profile alive through the password change.
            if (-not $running) {$null=StartManaged}
            $old=[OperiaServiceNative]::Read($target+'/active'); $next=[OperiaServiceNative]::NewPassword()
            if (-not $old) {$next.Dispose(); throw 'service_active_credential_missing'}
            if ($old.Length -gt 63) {$old.Dispose();$next.Dispose();throw 'service_legacy_long_credential_requires_controlled_transition'}
            $migration=$null
            try {
                [OperiaServiceNative]::Store($target+'/previous','.\OperiaSvc',$old)
                [OperiaServiceNative]::Store($target+'/pending','.\OperiaSvc',$next); Journal 'rotation_pending_persisted'
                Enable-LocalUser -SID $user.SID
                [OperiaServiceNative]::ChangePassword('OperiaSvc',$old,$next); Journal 'sam_password_changed'
                StopManaged
                $migration=[OperiaMigrationPipe]::new($Root,$user.SID.Value,$old)
                [OperiaServiceNative]::Configure($name,$null,'OperiaSvc',$next,$false)
                try {$null=StartManaged}
                catch {
                    if (-not $migration.Completed -or $migration.Error) {throw}
                    $migration.Dispose()
                    # Retry once in a fresh SCM logon after master-key migration.
                    $null=StartManaged
                }
                if (-not $migration.Completed -or $migration.Error) {throw 'service_dpapi_migration_not_acknowledged'}
                if ($canaryHash -ne (Get-FileHash -LiteralPath $canaryPath -Algorithm SHA256).Hash) {throw 'service_dpapi_canary_replaced'}
                Journal 'dpapi_current_canary_verified'
                [OperiaServiceNative]::Store($target+'/active','.\OperiaSvc',$next)
                [OperiaServiceNative]::Delete($target+'/pending'); Journal 'rotation_committed'
                [OperiaServiceNative]::Delete($target+'/previous')
                if (-not $running) {StopManaged}
            } catch {StopManaged; throw}
            finally {if ($migration) {$migration.Dispose()}; $old.Dispose(); $next.Dispose(); if ((Get-Service -Name $name).Status -ne 'Running') {Disable-LocalUser -SID $user.SID}}
        }
        RecoverCredential {
            VerifyRelease (CurrentRelease)
            StopManaged; Enable-LocalUser -SID $user.SID
            $chosen=$null; $migration=$null; $recoveryOutcome='committed_pending'
            try {
                if ($Release) {
                    ProtectTree (Join-Path $Root ('releases/'+$Release)) 'ReadAndExecute'
                    VerifyRelease $Release; SelectRelease $Release
                    Journal 'credential_recovery_explicit_rescue_release_selected'
                }
                foreach ($suffix in @('pending','active','previous')) {
                    $candidate=[OperiaServiceNative]::Read($target+'/'+$suffix)
                    if (-not $candidate) {continue}
                    if ([OperiaServiceNative]::Valid('OperiaSvc',$candidate)) {$chosen=$candidate; break}; $candidate.Dispose()
                }
                if (-not $chosen) {throw 'service_credential_recovery_no_valid_secret'}
                $previous=[OperiaServiceNative]::Read($target+'/previous')
                if ($previous) {
                    try {
                        $canaryPath=Join-Path $Root 'data/control/credential-canary-v3.dpapi'
                        if (-not (Test-Path -LiteralPath $canaryPath -PathType Leaf)) {throw 'service_existing_dpapi_canary_required'}
                        $canaryHash=(Get-FileHash -LiteralPath $canaryPath -Algorithm SHA256).Hash
                        $migration=[OperiaMigrationPipe]::new($Root,$user.SID.Value,$previous)
                    }
                    finally {$previous.Dispose()}
                }
                $create=-not [bool]$registered
                [OperiaServiceNative]::Configure($name, $(if ($create) {$expectedBinary} else {$null}), 'OperiaSvc',$chosen,$create)
                if ($migration) {
                    try {$null=StartManaged}
                    catch {
                        if (-not $migration.Completed -or $migration.Error) {throw}
                        $migration.Dispose()
                        $null=StartManaged
                    }
                    if (-not $migration.Completed -or $migration.Error) {throw 'service_dpapi_migration_not_acknowledged'}
                    if ($canaryHash -ne (Get-FileHash -LiteralPath $canaryPath -Algorithm SHA256).Hash) {throw 'service_dpapi_canary_replaced'}
                    StopManaged; Journal 'recovered_dpapi_current_canary_verified'
                }
                [OperiaServiceNative]::Store($target+'/active','.\OperiaSvc',$chosen)
                [OperiaServiceNative]::Delete($target+'/pending'); Journal 'credential_recovered_stopped'
                [OperiaServiceNative]::Delete($target+'/previous')
            } catch {
                StopManaged
                if (-not $migration -or -not $chosen) {throw}
                $migration.Dispose()
                $rollback=[OperiaServiceNative]::Read($target+'/previous')
                if (-not $rollback) {throw 'service_recovery_previous_secret_missing'}
                try {
                    Journal 'credential_recovery_rollback_pending'
                    Enable-LocalUser -SID $user.SID
                    [OperiaServiceNative]::ChangePassword('OperiaSvc',$chosen,$rollback)
                    [OperiaServiceNative]::Configure($name,$null,'OperiaSvc',$rollback,$false)
                    $null=StartManaged
                    if ($canaryHash -ne (Get-FileHash -LiteralPath $canaryPath -Algorithm SHA256).Hash) {throw 'service_dpapi_canary_replaced'}
                    StopManaged
                    [OperiaServiceNative]::Store($target+'/active','.\OperiaSvc',$rollback)
                    [OperiaServiceNative]::Delete($target+'/pending')
                    [OperiaServiceNative]::Delete($target+'/previous')
                    $recoveryOutcome='rolled_back_previous_preserving_dpapi'
                    Journal 'previous_credential_and_same_dpapi_canary_recovered'
                } finally {$rollback.Dispose(); StopManaged}
            }
            finally {if ($migration) {$migration.Dispose()}; if ($chosen) {$chosen.Dispose()}; Disable-LocalUser -SID $user.SID}
        }
        Update {
            if (-not $Release) {throw 'service_update_release_required'}
            $old=CurrentRelease
            if ($old -eq $Release) {throw 'service_update_same_release'}
            # Candidate is checked before quiescing; administrator-published tree only.
            ProtectTree (Join-Path $Root ('releases/'+$Release)) 'ReadAndExecute'
            $verified=Python $old @('verify',$Release)
            StopManaged
            $backup=Python $old @('backup'); Journal 'update_backup_verified'
            $prepared=Python $Release @('prepare')
            foreach ($folder in @('sandbox-runtime','static-lab-runtime')) { ProtectTree (Join-Path $Root ('data/storage/'+$folder)) 'ReadAndExecute' $false $true }
            # Persist before changing the pointer; recovery always keeps the DB.
            $bytes=[Text.Encoding]::UTF8.GetBytes((@{schema='operia-service-update-pending/1';previous=$old;candidate=$Release;backup_sha256=$backup.sha256} | ConvertTo-Json -Compress))
            $pendingStream=[IO.FileStream]::new($updatePending,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
            try {$pendingStream.Write($bytes,0,$bytes.Length); $pendingStream.Flush($true)} finally {$pendingStream.Dispose()}
            SelectRelease $Release; Journal 'update_pointer_switched'
            try {$null=StartManaged; Journal 'update_ready'; [IO.File]::Delete($updatePending)}
            catch {
                StopManaged; SelectRelease $old; Journal 'update_rollback_pointer'
                $null=StartManaged
                [IO.File]::Delete($updatePending)
                throw 'service_update_rejected_previous_release_restarted_database_not_restored'
            }
        }
        RecoverUpdate {
            if (-not (Test-Path -LiteralPath $updatePending)) {throw 'service_no_pending_update'}
            $pendingUpdate=Get-Content -LiteralPath $updatePending -Raw | ConvertFrom-Json
            if ($pendingUpdate.schema -ne 'operia-service-update-pending/1' -or $pendingUpdate.previous -notmatch '^[a-f0-9]{24}$') {throw 'service_pending_update_invalid'}
            $recoveryRelease=if ($Release) {$Release} else {$pendingUpdate.previous}
            # Explicit rescue release is integrity checked before selection; no DB restore.
            if ($Release) {ProtectTree (Join-Path $Root ('releases/'+$Release)) 'ReadAndExecute'}
            StopManaged; VerifyRelease $recoveryRelease; SelectRelease $recoveryRelease
            $null=StartManaged; Journal 'interrupted_update_previous_release_ready_database_preserved'
            [IO.File]::Delete($updatePending)
        }
        Status {}
    }
    Journal 'completed'
    $svc=Get-Service -Name $name -ErrorAction SilentlyContinue
    @{schema='operia-service-management-result/1';action=$Action;service=$name;state=if ($svc){[string]$svc.Status}else{'Absent'};account_disabled=-not (Get-LocalUser -SID $user.SID).Enabled;release=(CurrentRelease);recovery_outcome=if($Action -eq 'RecoverCredential'){$recoveryOutcome}else{$null}} | ConvertTo-Json -Compress
} catch {Journal 'failed'; throw} finally {$lock.Dispose()}
