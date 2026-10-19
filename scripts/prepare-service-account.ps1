param(
    [Parameter(Mandatory=$true)][string]$DeploymentRoot,
    [ValidatePattern('^[A-Za-z][A-Za-z0-9_-]{2,19}$')][string]$AccountName = 'OperiaSvc',
    [switch]$Apply,
    [switch]$ValidateModule,
    [ValidatePattern('^S-1-5-21-\d+-\d+-\d+-\d+$')][string]$ResumeAccountSid
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
foreach ($module in @('Microsoft.PowerShell.Utility', 'Microsoft.PowerShell.Security')) {
    Import-Module (Join-Path $PSHOME ('Modules/' + $module + '/' + $module + '.psd1'))
}

function Assert-NoReparse([string]$Path) {
    $item = Get-Item -LiteralPath $Path -Force
    while ($null -ne $item) {
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'service_reparse_rejected' }
        if ($item -is [IO.FileInfo]) { $item = $item.Directory } else { $item = $item.Parent }
    }
}
function Import-TrustedLocalAccounts {
    if (-not [Environment]::Is64BitProcess) { throw 'service_64bit_powershell_required' }
    $base = Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/Modules/Microsoft.PowerShell.LocalAccounts'
    Assert-NoReparse $base
    $candidates = @()
    if (Test-Path -LiteralPath (Join-Path $base 'Microsoft.PowerShell.LocalAccounts.psd1')) {
        $candidates += [pscustomobject]@{Version=[version]'0.0'; Path=(Join-Path $base 'Microsoft.PowerShell.LocalAccounts.psd1')}
    }
    foreach ($directory in Get-ChildItem -LiteralPath $base -Directory) {
        if ($directory.Name -match '^\d+\.\d+(\.\d+){0,2}$') {
            $manifest = Join-Path $directory.FullName 'Microsoft.PowerShell.LocalAccounts.psd1'
            if (Test-Path -LiteralPath $manifest) {
                Assert-NoReparse $manifest
                $candidates += [pscustomobject]@{Version=[version]$directory.Name; Path=$manifest}
            }
        }
    }
    if (-not $candidates.Count) { throw 'service_localaccounts_module_missing' }
    $selected = $candidates | Sort-Object Version -Descending | Select-Object -First 1
    Assert-NoReparse $selected.Path
    Import-Module -Name $selected.Path -Force
    if (-not (Get-Command New-LocalUser -Module Microsoft.PowerShell.LocalAccounts -ErrorAction SilentlyContinue)) {
        throw 'service_localaccounts_module_invalid'
    }
}
$root = [IO.Path]::GetFullPath($DeploymentRoot).TrimEnd('\')
Assert-NoReparse $root
$layout = Get-Content -LiteralPath (Join-Path $root 'layout.json') -Raw | ConvertFrom-Json
if ($layout.schema -ne 'operia-service-staging/1' -or $layout.live_data_copied -ne $false -or
    $layout.operational_secret_copied -ne $false) { throw 'service_staging_invalid' }
$code = Join-Path $root 'code'
foreach ($child in Get-ChildItem -LiteralPath $code -Recurse -Force) { Assert-NoReparse $child.FullName }
$expected = @($layout.code_files.PSObject.Properties)
$actual = @(Get-ChildItem -LiteralPath $code -Recurse -Force -File)
if ($actual.Count -ne $expected.Count) { throw 'service_code_inventory_mismatch' }
foreach ($entry in $expected) {
    if ($entry.Name -match '(^/|\\|:|(^|/)\.\.?(/|$))') { throw 'service_manifest_path_rejected' }
    $file = [IO.Path]::GetFullPath((Join-Path $code $entry.Name))
    if (-not $file.StartsWith($code + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'service_manifest_path_rejected' }
    Assert-NoReparse $file
    if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash -ne $entry.Value) { throw 'service_code_hash_mismatch' }
}
# Never apply this policy to an existing data set or a populated Python runtime.
foreach ($directory in @('data','secrets','runtime')) {
    $path = Join-Path $root $directory
    Assert-NoReparse $path
    foreach ($child in Get-ChildItem -LiteralPath $path -Recurse -Force) { Assert-NoReparse $child.FullName }
    if (@(Get-ChildItem -LiteralPath $path -Recurse -Force -File).Count) { throw 'service_staging_not_empty' }
}
if ($ValidateModule) { Import-TrustedLocalAccounts }
if (-not $Apply) {
    @{schema='operia-service-account-plan/1'; account=$AccountName; code_access='ReadAndExecute';
      data_access='Modify on selected subtrees'; secrets_access='ReadAndExecute'; runtime_access='ReadAndExecute';
      final_account_state='disabled'; apply_requires_administrator=$true; code_files=$expected.Count;
      localaccounts_module_validated=[bool]$ValidateModule} | ConvertTo-Json
    return
}
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'service_administrator_required' }
Import-TrustedLocalAccounts
$existing = Get-LocalUser -Name $AccountName -ErrorAction SilentlyContinue
if ($existing) {
    if (-not $ResumeAccountSid -or $existing.SID.Value -ne $ResumeAccountSid -or $existing.Enabled -or
        $existing.Description -ne 'OPERIA staged least-privilege identity') { throw 'service_account_already_exists' }
} elseif ($ResumeAccountSid) { throw 'service_resume_account_missing' }

function Set-ServiceAcl([string]$Path, [string]$Rights) {
    Assert-NoReparse $Path
    $isDirectory = (Get-Item -LiteralPath $Path -Force).PSIsContainer
    if ($isDirectory) { $acl = New-Object Security.AccessControl.DirectorySecurity }
    else { $acl = New-Object Security.AccessControl.FileSecurity }
    $acl.SetAccessRuleProtection($true, $false)
    $acl.SetOwner($identity.User)
    $inherit = [Security.AccessControl.InheritanceFlags]::None
    if ($isDirectory) { $inherit = [Security.AccessControl.InheritanceFlags]'ContainerInherit, ObjectInherit' }
    foreach ($sid in @($identity.User.Value, 'S-1-5-18', 'S-1-5-32-544') | Select-Object -Unique) {
        $rule = New-Object Security.AccessControl.FileSystemAccessRule(
            (New-Object Security.Principal.SecurityIdentifier($sid)), 'FullControl', $inherit, 'None', 'Allow')
        $acl.AddAccessRule($rule)
    }
    $rule = New-Object Security.AccessControl.FileSystemAccessRule($script:serviceSid, $Rights, $inherit, 'None', 'Allow')
    $acl.AddAccessRule($rule)
    Set-Acl -LiteralPath $Path -AclObject $acl
}

# No password in arguments, environment, transcript, report or disk. Final account
# is disabled; activation requires a managed credential reset and separate review.
$random = New-Object byte[] 48
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($random); $rng.Dispose()
$password = ConvertTo-SecureString ('Aa1!' + [Convert]::ToBase64String($random)) -AsPlainText -Force
[Array]::Clear($random, 0, $random.Length)
$created = $false
$result = [ordered]@{schema='operia-service-account-result/1'; account=$AccountName; status='incomplete'; account_disabled=$false}
try {
    if ($existing) {
        # Explicit SID-bound retry for this disabled staging identity only.
        Set-LocalUser -SID $existing.SID -Password $password
        $user = Get-LocalUser -SID $existing.SID
    } else {
        $user = New-LocalUser -Name $AccountName -Password $password -Disabled -Description 'OPERIA staged least-privilege identity'
    }
    $created = $true
    $result['account_sid'] = $user.SID.Value
    $script:serviceSid = $user.SID
    $standardMembers = @(Get-LocalGroupMember -SID 'S-1-5-32-545' | Where-Object { $_.SID -eq $user.SID })
    if (-not $standardMembers.Count) { Add-LocalGroupMember -SID 'S-1-5-32-545' -Member $user }
    $memberships = @(Get-LocalGroup | Where-Object {
        @(Get-LocalGroupMember -SID $_.SID | Where-Object { $_.SID -eq $user.SID }).Count -gt 0
    })
    if ($memberships.Count -ne 1 -or $memberships[0].SID.Value -ne 'S-1-5-32-545') { throw 'service_group_policy_failed' }
    Set-ServiceAcl $root 'ReadAndExecute'
    foreach ($child in Get-ChildItem -LiteralPath $root -Recurse -Force) { Set-ServiceAcl $child.FullName 'ReadAndExecute' }
    foreach ($name in @('storage','memory_vault','logs','temp')) {
        $path = Join-Path (Join-Path $root 'data') $name
        Set-ServiceAcl $path 'Modify'
        foreach ($child in Get-ChildItem -LiteralPath $path -Recurse -Force) { Set-ServiceAcl $child.FullName 'Modify' }
    }
    # Probe only synthetic objects under this fresh staging root, never live data.
    Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Runtime.InteropServices;
public static class OperiaAccountProbe {
 [DllImport("advapi32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
 public static extern bool LogonUser(string user,string domain,IntPtr password,int type,int provider,out IntPtr token);
 [DllImport("advapi32.dll", SetLastError=true)] public static extern bool ImpersonateLoggedOnUser(IntPtr token);
 [DllImport("advapi32.dll", SetLastError=true)] public static extern bool RevertToSelf();
 [DllImport("kernel32.dll")] public static extern bool CloseHandle(IntPtr token);
 public static bool Denied(string path, bool create) {
   try { using(var f = new FileStream(path, create ? FileMode.CreateNew : FileMode.Open, FileAccess.Write)) {} return false; }
   catch(UnauthorizedAccessException) { return true; }
 }
 public static string Probe(string root, IntPtr token) {
   if(!ImpersonateLoggedOnUser(token)) throw new Exception("service_impersonation_failed");
   try {
     var id = System.Security.Principal.WindowsIdentity.GetCurrent();
     var principal = new System.Security.Principal.WindowsPrincipal(id);
     if(principal.IsInRole(System.Security.Principal.WindowsBuiltInRole.Administrator)) return "service_probe_admin";
     var code = Path.Combine(root,"code","readonly-canary.txt");
     if(File.ReadAllText(code).TrimEnd('\r','\n') != "OPERIA ACL canary") return "service_probe_read";
     if(!Denied(code,false) || !Denied(Path.Combine(root,"code","forbidden.tmp"),true)) return "service_probe_code_write";
     if(!Denied(Path.Combine(root,"runtime","forbidden.tmp"),true)) return "service_probe_runtime_write";
     if(!Denied(Path.Combine(root,"secrets","forbidden.tmp"),true)) return "service_probe_secret_write";
     foreach(var name in new[]{"storage","memory_vault","logs","temp"}) {
       var p = Path.Combine(root,"data",name,"acl-probe.tmp");
       File.WriteAllText(p,"synthetic");
       if(File.ReadAllText(p)!="synthetic") return "service_probe_data_read";
       File.Delete(p);
     }
     try { File.Delete(code); return "service_probe_code_delete"; } catch(UnauthorizedAccessException) {}
     return "ok";
   } finally { if(!RevertToSelf()) Environment.FailFast("service_revert_failed"); }
 }
}
'@
    $token = [IntPtr]::Zero
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToGlobalAllocUnicode($password)
    try {
        Enable-LocalUser -SID $user.SID
        if (-not [OperiaAccountProbe]::LogonUser($AccountName, '.', $pointer, 2, 0, [ref]$token)) {
            throw ('service_logon_failed_' + [Runtime.InteropServices.Marshal]::GetLastWin32Error())
        }
        $probe = [OperiaAccountProbe]::Probe($root, $token)
        if ($probe -ne 'ok') { throw $probe }
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeGlobalAllocUnicode($pointer)
        if ($token -ne [IntPtr]::Zero) { [void][OperiaAccountProbe]::CloseHandle($token) }
        Disable-LocalUser -SID $user.SID
    }
    $result.status = 'prepared_and_acl_probed'
    $result['code_read_verified'] = $true
    $result['code_write_and_delete_denied'] = $true
    $result['selected_data_write_verified'] = $true
    $result['runtime_and_secrets_write_denied'] = $true
    $result['administrator_membership'] = $false
} finally {
    if ($created) {
        Disable-LocalUser -Name $AccountName
        $result.account_disabled = -not (Get-LocalUser -Name $AccountName).Enabled
        $result | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $root 'account-result.json') -Encoding UTF8
    }
    $password.Dispose()
}
$result | ConvertTo-Json
