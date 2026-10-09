# Tests the built installer end to end in Windows Sandbox: silent install,
# every athc command and subcommand on the integration-test fixtures (outputs
# compared against the goldens where the tests keep one), upgrade over the
# install, silent uninstall. Prints the sandbox's PASS/FAIL lines and exits
# non-zero on any failure. The sandbox has no network, which also proves the
# installer works offline.
#
# Needs a built installer (run release-build.ps1 first) and the Windows Sandbox
# optional feature. A sandbox window opens and closes by itself.
#
# athc-admin's release-test.ps1 runs this script for the admin setup.exe: it
# passes -SetupExe, plus -ExtraSteps (a script run inside the sandbox after
# athc's command checks) and -ExtraData (its fixtures, mapped in as
# Desktop\extra).
#
# Run from anywhere; paths resolve relative to this script:
#     ./athc/packaging/release-test.ps1

param(
    [string]$SetupExe,
    [string]$ExtraSteps,
    [string]$ExtraData
)

$ErrorActionPreference = 'Stop'

$scriptRoot  = $PSScriptRoot                          # athc/packaging/
$projectRoot = Split-Path $scriptRoot -Parent         # athc/
$pyproject   = Join-Path $projectRoot "pyproject.toml"

$m = (Select-String -Path $pyproject -Pattern '^version\s*=\s*"(.+?)"').Matches[0]
if (-not $m) { throw "Could not read version from $pyproject" }
$version = $m.Groups[1].Value

if (-not $SetupExe) { $SetupExe = Join-Path $projectRoot "dist\athc-$version-setup.exe" }
$distDir    = Split-Path $SetupExe -Parent
$dataDir    = Join-Path $projectRoot 'tests\integration\data'
$expectDir  = Join-Path $projectRoot 'tests\integration\expected'
$sandboxExe = Join-Path $env:windir 'System32\WindowsSandbox.exe'

if (-not (Test-Path $SetupExe)) { throw "$SetupExe not found - run release-build.ps1 first" }
if ($ExtraSteps -and -not (Test-Path $ExtraSteps)) { throw "$ExtraSteps not found" }
if ($ExtraData -and -not (Test-Path $ExtraData)) { throw "$ExtraData not found" }
if (-not (Test-Path $sandboxExe)) { throw 'Windows Sandbox is not enabled (optional Windows feature)' }
if (-not (Get-Command wsb -ErrorAction SilentlyContinue)) {
    throw 'wsb.exe not found - the Windows Sandbox command line needs Windows 11 24H2 or newer'
}
# A sandbox is running only when wsb lists it: WindowsSandboxServer.exe is a
# broker that wsb itself starts and leaves behind, so a process check would
# refuse to run with no sandbox open.
if (wsb list) {
    throw 'A Windows Sandbox is already running - stop it first: wsb list, then wsb stop --id <id>'
}
if (Get-Process -Name 'WindowsSandboxRemoteSession' -ErrorAction SilentlyContinue) {
    throw 'A Windows Sandbox window is still open - close it first'
}
# The window can be gone while the VM lives on, still holding the mapped
# folders. Say so here, rather than failing later on a locked folder.
if (Get-Process -Name 'vmmemWindowsSandbox' -ErrorAction SilentlyContinue) {
    throw 'A sandbox VM is still running with no window. Stop it with: wsb list, then wsb stop --id <id>'
}

# Quick local sanity check before a multi-minute sandbox boot.
$ver = (& (Join-Path $distDir 'athc\athc.exe') --version | Out-String).Trim()
if ($ver -notmatch [regex]::Escape($version)) { throw "dist exe says '$ver', expected $version - stale build?" }

# Stage the work folder the sandbox maps in: the guest scripts, version and
# setup file name in assets (read-only), an empty out (writable) for results.
$work   = Join-Path $env:TEMP 'athc-release-test'
$assets = Join-Path $work 'assets'
$outDir = Join-Path $work 'out'
if (Test-Path $work) { Remove-Item $work -Recurse -Force }
New-Item -ItemType Directory -Force $assets, $outDir | Out-Null
Copy-Item (Join-Path $scriptRoot 'sandbox-steps.ps1') $assets
Set-Content (Join-Path $assets 'version.txt') $version
Set-Content (Join-Path $assets 'setup.txt') (Split-Path $SetupExe -Leaf)
if ($ExtraSteps) { Copy-Item $ExtraSteps (Join-Path $assets 'extra-steps.ps1') }

function Xml([string]$s) { [System.Security.SecurityElement]::Escape($s) }
$desk = 'C:\Users\WDAGUtilityAccount\Desktop'
function Mapping([string]$hostDir, [string]$name, [string]$readOnly) {
@"
    <MappedFolder>
      <HostFolder>$(Xml (Resolve-Path $hostDir).Path)</HostFolder>
      <SandboxFolder>$desk\$name</SandboxFolder>
      <ReadOnly>$readOnly</ReadOnly>
    </MappedFolder>
"@
}
$mappings = @(
    (Mapping $distDir 'dist' 'true'),
    (Mapping $dataDir 'data' 'true'),
    (Mapping $expectDir 'expected' 'true'),
    (Mapping $assets 'assets' 'true'),
    (Mapping $outDir 'out' 'false')
)
if ($ExtraData) { $mappings += Mapping $ExtraData 'extra' 'true' }

$wsb = Join-Path $work 'release-test.wsb'
@"
<Configuration>
  <Networking>Disable</Networking>
  <MappedFolders>
$($mappings -join "`r`n")
  </MappedFolders>
  <LogonCommand>
    <Command>powershell.exe -NoProfile -ExecutionPolicy Bypass -File $desk\assets\sandbox-steps.ps1</Command>
  </LogonCommand>
</Configuration>
"@ | Set-Content $wsb -Encoding ascii

Write-Host "Testing $(Split-Path $SetupExe -Leaf) in Windows Sandbox (about 10 minutes)..."
Start-Process $sandboxExe -ArgumentList "`"$wsb`""

$done     = Join-Path $outDir 'DONE'
$deadline = (Get-Date).AddMinutes(45)
try {
    while (-not (Test-Path $done) -and (Get-Date) -lt $deadline) { Start-Sleep 10 }
} finally {
    # Stop the sandbox from the host: `wsb stop` turns the VM off and closes
    # the window. Shutting the VM down from inside leaves the window open with
    # an error dialog ("The remote environment is shutting down"), and killing
    # the window leaves the VM running and holding the mapped folders. Only
    # this run's sandbox can be listed - the checks above refuse to start
    # beside another one.
    foreach ($id in @(wsb list)) { wsb stop --id $id | Out-Null }
    $vmDeadline = (Get-Date).AddSeconds(90)
    while ((Get-Process -Name 'vmmemWindowsSandbox' -ErrorAction SilentlyContinue) -and
           (Get-Date) -lt $vmDeadline) {
        Start-Sleep 3
    }
    if (Get-Process -Name 'vmmemWindowsSandbox' -ErrorAction SilentlyContinue) {
        Write-Host 'WARNING: the sandbox VM is still running. Stop it with: wsb list, then wsb stop --id <id>'
    }
}
if (-not (Test-Path $done)) { throw "Sandbox test timed out after 45 minutes - logs in $outDir" }

$lines = Get-Content (Join-Path $outDir 'results.txt')
$lines | Write-Host
$failed = @($lines | Where-Object { $_ -like 'FAIL*' }).Count
Write-Host ''
if ($failed -gt 0) {
    Write-Host "FAILED - $failed failing check(s); logs in $outDir"
    exit 1
}
Write-Host "All sandbox checks passed. Logs in $outDir"
# Explicit, so a calling script (athc-admin's) reads this result rather than
# the last native command's.
exit 0
