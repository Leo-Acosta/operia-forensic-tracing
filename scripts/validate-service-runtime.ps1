param(
    [Parameter(Mandatory=$true)][string]$DeploymentRoot,
    [Parameter(Mandatory=$true)][ValidatePattern('^S-1-5-21-\d+-\d+-\d+-\d+$')][string]$AccountSid
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
foreach ($module in @('Microsoft.PowerShell.Utility','Microsoft.PowerShell.Security')) {
    Import-Module (Join-Path $PSHOME ('Modules/'+$module+'/'+$module+'.psd1'))
}
function NoLinks([string]$Path) {
    $item=Get-Item -LiteralPath $Path -Force
    while ($null -ne $item) {
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'runtime_reparse_rejected' }
        if ($item -is [IO.FileInfo]) { $item=$item.Directory } else { $item=$item.Parent }
    }
}
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=[Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'runtime_administrator_required' }
if (-not [Environment]::Is64BitProcess) { throw 'runtime_64bit_powershell_required' }
$base=Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/Modules/Microsoft.PowerShell.LocalAccounts'
$modules=@(Get-ChildItem -LiteralPath $base -Filter Microsoft.PowerShell.LocalAccounts.psd1 -Recurse)
if ($modules.Count -ne 1) { throw 'runtime_localaccounts_module_ambiguous' }
NoLinks $modules[0].FullName
Import-Module $modules[0].FullName
$user=Get-LocalUser -Name OperiaSvc
if ($user.SID.Value -ne $AccountSid -or $user.Enabled -or $user.Description -ne 'OPERIA staged least-privilege identity') {
    throw 'runtime_account_identity_or_state_invalid'
}
$groups=@(Get-LocalGroup | Where-Object { @(Get-LocalGroupMember -SID $_.SID | Where-Object {$_.SID -eq $user.SID}).Count })
if ($groups.Count -ne 1 -or $groups[0].SID.Value -ne 'S-1-5-32-545') { throw 'runtime_account_groups_invalid' }
$root=[IO.Path]::GetFullPath($DeploymentRoot).TrimEnd('\')
NoLinks $root
$layout=Get-Content -LiteralPath (Join-Path $root 'layout.json') -Raw | ConvertFrom-Json
if ($layout.schema -ne 'operia-service-staging/1' -or $layout.live_data_copied -ne $false -or $layout.operational_secret_copied -ne $false) { throw 'runtime_layout_invalid' }
$manifest=Get-Content -LiteralPath (Join-Path $root 'runtime-manifest.json') -Raw | ConvertFrom-Json
if ($manifest.schema -ne 'operia-service-runtime/1') { throw 'runtime_manifest_invalid' }
function VerifyTree([string]$Folder,$Entries) {
    foreach ($item in Get-ChildItem -LiteralPath $Folder -Recurse -Force) { NoLinks $item.FullName }
    $expected=@($Entries.PSObject.Properties)
    if (@(Get-ChildItem -LiteralPath $Folder -Recurse -Force -File).Count -ne $expected.Count) { throw 'runtime_inventory_mismatch' }
    foreach ($entry in $expected) {
        if ($entry.Name -match '(^/|\\|:|(^|/)\.\.?(/|$))') { throw 'runtime_manifest_path_invalid' }
        $file=[IO.Path]::GetFullPath((Join-Path $Folder $entry.Name))
        if (-not $file.StartsWith($Folder+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'runtime_manifest_path_invalid' }
        if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash -ne $entry.Value) { throw 'runtime_file_hash_mismatch' }
    }
}
VerifyTree (Join-Path $root 'code') $layout.code_files
VerifyTree (Join-Path $root 'runtime') $manifest.files
foreach ($name in @('data','secrets')) {
    $folder=Join-Path $root $name
    foreach ($item in Get-ChildItem -LiteralPath $folder -Recurse -Force) { NoLinks $item.FullName }
    if (@(Get-ChildItem -LiteralPath $folder -Recurse -File).Count) { throw 'runtime_trial_requires_empty_data_and_secrets' }
}
$adminSid=[Security.Principal.SecurityIdentifier]::new('S-1-5-32-544')
$systemSid=[Security.Principal.SecurityIdentifier]::new('S-1-5-18')
$appSid=[Security.Principal.SecurityIdentifier]::new('S-1-15-2-1')
function ProtectTree([string]$Path,[string]$Rights,[bool]$Private=$false,[bool]$AppContainer=$false) {
    NoLinks $Path
    $acl=[Security.AccessControl.DirectorySecurity]::new()
    $acl.SetAccessRuleProtection($true,$false); $acl.SetOwner($adminSid)
    $privileged=@($adminSid,$systemSid)
    if (-not $Private) { $privileged += $identity.User }
    foreach ($sid in $privileged) {
        $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($sid,'FullControl','ContainerInherit, ObjectInherit','None','Allow'))
    }
    $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($user.SID,$Rights,'ContainerInherit, ObjectInherit','None','Allow'))
    if ($AppContainer) {
        $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($appSid,'ReadAndExecute','ContainerInherit, ObjectInherit','None','Allow'))
    }
    Set-Acl -LiteralPath $Path -AclObject $acl
    # Descendants were created in this fresh, checked tree. Reset only children,
    # preserving the explicitly protected ACL on the named root itself.
    foreach ($child in Get-ChildItem -LiteralPath $Path -Force) {
        & (Join-Path $env:SystemRoot 'System32/icacls.exe') $child.FullName /reset /T /Q | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'runtime_acl_reset_failed' }
    }
}
ProtectTree $root 'ReadAndExecute'
foreach ($name in @('storage','memory_vault','logs','temp')) { ProtectTree (Join-Path $root ('data/'+$name)) 'Modify' }
ProtectTree (Join-Path $root 'secrets') 'ReadAndExecute' $true
$key=Join-Path $root 'secrets/synthetic-signing-key.bin'
$random=[byte[]]::new(32); $rng=[Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($random); $rng.Dispose(); [IO.File]::WriteAllBytes($key,$random); [Array]::Clear($random,0,$random.Length)
$keyAcl=Get-Acl -LiteralPath $key; $keyAcl.SetOwner($adminSid); Set-Acl -LiteralPath $key -AclObject $keyAcl
$python=Join-Path $root 'runtime/python.exe'
$envMap=@{
    'SystemRoot'=$env:SystemRoot; 'WINDIR'=$env:SystemRoot; 'COMSPEC'=(Join-Path $env:SystemRoot 'System32/cmd.exe');
    'PATH'=((Join-Path $root 'runtime')+';'+(Join-Path $env:SystemRoot 'System32'));
    'TEMP'=(Join-Path $root 'data/temp'); 'TMP'=(Join-Path $root 'data/temp');
    'USERPROFILE'=(Join-Path (Split-Path -Parent $env:USERPROFILE) 'OperiaSvc');
    'APPDATA'=(Join-Path (Split-Path -Parent $env:USERPROFILE) 'OperiaSvc/AppData/Roaming');
    'LOCALAPPDATA'=(Join-Path (Split-Path -Parent $env:USERPROFILE) 'OperiaSvc/AppData/Local');
    'OPERIA_ENV'='production'; 'OPERIA_STORAGE_DIR'=(Join-Path $root 'data/storage');
    'OPERIA_DATABASE_URL'=('sqlite:///'+((Join-Path $root 'data/storage/e7-runtime-validation.db').Replace('\','/')));
    'OPERIA_AUTH_SIGNING_KEY_FILE'=$key; 'OPERIA_CORS_ORIGINS'='["https://synthetic-gateway.invalid"]';
    'OPERIA_LOCAL_RECOVERY_ENABLED'='false'; 'OPERIA_LOCAL_AI_ENABLED'='false'; 'OPERIA_LOCAL_AI_GATEWAY_ENABLED'='false';
    'OPERIA_CONNECTOR_ALLOWED_HOSTS'='[]'; 'OPERIA_EXPECTED_SERVICE_SID'=$AccountSid; 'PYTHONDONTWRITEBYTECODE'='1'
}
function NewInfo {
    $info=[Diagnostics.ProcessStartInfo]::new()
    $info.FileName=$python; $info.WorkingDirectory=(Join-Path $root 'code')
    $info.UseShellExecute=$false; $info.CreateNoWindow=$true
    $info.RedirectStandardOutput=$true; $info.RedirectStandardError=$true
    $info.Environment.Clear()
    foreach ($entry in $envMap.GetEnumerator()) { $info.Environment[$entry.Key]=$entry.Value }
    return $info
}
function Execute($Info,[string]$Label,[int]$Timeout) {
    $process=[Diagnostics.Process]::new(); $process.StartInfo=$Info
    try {
        [void]$process.Start()
        $stdout=$process.StandardOutput.ReadToEndAsync(); $stderr=$process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit($Timeout*1000)) { $process.Kill($true); $process.WaitForExit(); throw ('runtime_timeout_'+$Label) }
        [IO.File]::WriteAllText((Join-Path $root ('data/logs/'+$Label+'.stdout')), $stdout.GetAwaiter().GetResult())
        [IO.File]::WriteAllText((Join-Path $root ('data/logs/'+$Label+'.stderr')), $stderr.GetAwaiter().GetResult())
        if ($process.ExitCode -ne 0) { throw ('runtime_process_failed_'+$Label) }
    } finally {
        try { if ($process.Id -and -not $process.HasExited) { $process.Kill($true); $process.WaitForExit() } } catch {}
        $process.Dispose()
    }
}
# Prepare derived runtimes as administrator, then make both complete trees RX.
$prepare=NewInfo; $prepare.ArgumentList.Add('-B'); $prepare.ArgumentList.Add('-m'); $prepare.ArgumentList.Add('scripts.service_runtime_probe'); $prepare.ArgumentList.Add('--prepare')
Execute $prepare 'prepare' 180
foreach ($name in @('sandbox-runtime','static-lab-runtime')) { ProtectTree (Join-Path $root ('data/storage/'+$name)) 'ReadAndExecute' $false $true }
$random=[byte[]]::new(48); $rng=[Security.Cryptography.RandomNumberGenerator]::Create(); $rng.GetBytes($random); $rng.Dispose()
$password=ConvertTo-SecureString ('Aa1!'+[Convert]::ToBase64String($random)) -AsPlainText -Force
[Array]::Clear($random,0,$random.Length)
$result=@{schema='operia-service-runtime-admin/1'; status='incomplete'; account_disabled=$false; service_installed=$false}
try {
    Set-LocalUser -SID $user.SID -Password $password
    Enable-LocalUser -SID $user.SID
    $probe=NewInfo
    $probe.UserName='OperiaSvc'; $probe.Domain='.'; $probe.Password=$password; $probe.LoadUserProfile=$true
    $probe.ArgumentList.Add('-B'); $probe.ArgumentList.Add('-m'); $probe.ArgumentList.Add('scripts.service_runtime_probe')
    Execute $probe 'service' 240
    VerifyTree (Join-Path $root 'code') $layout.code_files
    VerifyTree (Join-Path $root 'runtime') $manifest.files
    $result.status='runtime_and_service_identity_validated'
} finally {
    Disable-LocalUser -SID $user.SID
    $result.account_disabled=-not (Get-LocalUser -SID $user.SID).Enabled
    $result | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $root 'runtime-admin-result.json') -Encoding UTF8
    $password.Dispose()
}
$result | ConvertTo-Json
