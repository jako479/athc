# Runs INSIDE Windows Sandbox; release-test.ps1 maps it in and launches it via
# the sandbox LogonCommand. Installs the setup.exe silently, runs every athc
# command and subcommand on the integration-test fixtures (outputs compared
# against the goldens where the tests keep one), upgrades over the install,
# uninstalls, and writes PASS/FAIL lines to Desktop\out (a writable mapping
# back to the host).

$ErrorActionPreference = 'Continue'
$desk      = 'C:\Users\WDAGUtilityAccount\Desktop'
$out       = Join-Path $desk 'out'
$results   = Join-Path $out 'results.txt'
$expected  = Join-Path $desk 'expected'
$version   = (Get-Content (Join-Path $desk 'assets\version.txt')).Trim()
$setupName = (Get-Content (Join-Path $desk 'assets\setup.txt')).Trim()
$setup     = Join-Path $desk "dist\$setupName"
$extra     = Join-Path $desk 'assets\extra-steps.ps1'
$app       = Join-Path $env:LOCALAPPDATA 'Programs\Assistant to the Head Coach'
$exe       = Join-Path $app 'athc.exe'
$cfgDir    = Join-Path $env:LOCALAPPDATA 'athc'
$leagues   = Join-Path $cfgDir 'leagues'
$lnk       = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Assistant to the Head Coach README.lnk'
# Writable copies of the fixtures; every command runs in $work.
$data      = 'C:\test\data'
$work      = 'C:\test\work'

Start-Transcript -Path (Join-Path $out 'transcript.log') | Out-Null
Set-Content $results "sandbox installer test v$version ($setupName) $(Get-Date -Format s)"

function Check([string]$name, [bool]$ok) {
    if ($ok) { $script:pass++ } else { $script:fail++ }
    $tag = if ($ok) { 'PASS' } else { 'FAIL' }
    Add-Content $results "$tag  $name"
}
$pass = 0; $fail = 0

# Runs athc.exe with $argv in $cwd. Each run's stdout and stderr land in
# out\cmd-NN.out.txt and .err.txt; out\commands.txt lists the runs.
$runs = 0
function Athc([string[]]$argv, [string]$cwd = $work) {
    $script:runs++
    $base = Join-Path $out ('cmd-{0:D2}' -f $script:runs)
    $line = ($argv | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join ' '
    Add-Content (Join-Path $out 'commands.txt') ('{0:D2}  athc {1}' -f $script:runs, $line)
    $p = Start-Process $exe -ArgumentList $line -WorkingDirectory $cwd `
        -RedirectStandardOutput "$base.out.txt" -RedirectStandardError "$base.err.txt" `
        -NoNewWindow -Wait -PassThru
    $stdout = [IO.File]::ReadAllText("$base.out.txt")
    $stderr = [IO.File]::ReadAllText("$base.err.txt")
    [pscustomobject]@{ Code = $p.ExitCode; Out = $stdout; All = $stdout + $stderr }
}

# Text compared line by line: the goldens are stored with LF, athc writes CRLF.
function Lines([string]$text) { ($text -replace "`r`n", "`n").TrimEnd("`n") }
function Raw([string]$name) { [IO.File]::ReadAllText((Join-Path $expected $name)) -replace "`r`n", "`n" }
function Golden([string]$name) { Lines (Raw $name) }
# Full fixture paths shortened to file names, as the tests do before comparing.
function Short([string]$text, [string[]]$paths) {
    foreach ($p in $paths) { $text = $text.Replace($p, (Split-Path $p -Leaf)) }
    Lines $text
}

# --- install -----------------------------------------------------------
Start-Process $setup -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/LOG=$out\install1.log" -Wait
Check 'install: athc.exe present' (Test-Path $exe)
foreach ($doc in 'README.txt', 'COMMANDS.txt', 'SCHEDULER-COMMANDS.txt', 'CHANGELOG.txt', 'LICENSE.txt') {
    Check "install: $doc in the install folder" (Test-Path (Join-Path $app $doc))
}
foreach ($file in 'athc.ini', 'leagues\PNFL\league.toml', 'leagues\PNFL\gameplan.toml',
                  'leagues\PNFL\standings\2049.league.ini', 'leagues\PCFL\league.toml',
                  'leagues\PCFL\standings\2029.league.ini') {
    Check "install: $file seeded" (Test-Path (Join-Path $cfgDir $file))
}
Check 'install: start-menu shortcut present' (Test-Path $lnk)
$regPath = (Get-ItemProperty 'HKCU:\Environment' -ErrorAction SilentlyContinue).Path
Check 'install: install folder on user PATH' ($regPath -like "*$app*")
$ver = ''
if (Test-Path $exe) { $ver = (& $exe --version 2>&1 | Out-String).Trim() }
Check "install: --version reports $version (got '$ver')" ($ver -match [regex]::Escape($version))
# This console predates the install; a new one reads PATH from the registry.
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
            [Environment]::GetEnvironmentVariable('Path', 'User')
$byName = (cmd /c 'athc --version' 2>&1 | Out-String).Trim()
Check "install: athc runs by name from PATH (got '$byName')" ($byName -match "^athc, version $([regex]::Escape($version))$")

# --- fixtures ------------------------------------------------------------
New-Item -ItemType Directory -Force $work | Out-Null
Copy-Item (Join-Path $desk 'data') 'C:\test' -Recurse
# The copies may carry the read-only mapping's attribute; the edits need them writable.
Get-ChildItem 'C:\test' -Recurse -File | ForEach-Object { $_.IsReadOnly = $false }
foreach ($name in 'offense.pln', 'offense2.pln', 'offense3.pln') {
    Copy-Item (Join-Path $data 'offense.pln') (Join-Path $work $name)
}
Copy-Item (Join-Path $data 'TST-OFF1.prf') $work
Set-Content (Join-Path $work 'normals.txt') 'OR45RL01'
Set-Content (Join-Path $work 'specials.txt') 'LIONKICK'

# League TEST: the seeded PNFL league.toml (its category labels are the ones
# the goldens use) with play_path at the fixture pool, plus the tests' rule
# files and the seeded PNFL pdbtoexcel.toml.
$testLeague = Join-Path $leagues 'TEST'
New-Item -ItemType Directory -Force (Join-Path $testLeague 'standings') | Out-Null
(Get-Content (Join-Path $leagues 'PNFL\league.toml')) -replace '^play_path = .*', "play_path = '$data\plays'" |
    Set-Content (Join-Path $testLeague 'league.toml')
Copy-Item (Join-Path $data 'profile_rules.toml') (Join-Path $testLeague 'profile.toml')
Copy-Item (Join-Path $data 'gameplan_rules.toml') (Join-Path $testLeague 'gameplan.toml')
Copy-Item (Join-Path $data 'playpool_rules.toml') (Join-Path $testLeague 'playpool.toml')
Copy-Item (Join-Path $leagues 'PNFL\pdbtoexcel.toml') (Join-Path $testLeague 'pdbtoexcel.toml')

# Leagues divisions and conferences: the scheduler goldens' standings and rules.
$schedules = @(@{ League = 'divisions'; Season = 2026 }, @{ League = 'conferences'; Season = 2029 })
foreach ($case in $schedules) {
    $folder = Join-Path $leagues $case.League
    New-Item -ItemType Directory -Force (Join-Path $folder 'standings') | Out-Null
    Copy-Item (Join-Path $data "$($case.League).$($case.Season).ini") (Join-Path $folder "standings\$($case.Season).league.ini")
    Copy-Item (Join-Path $data "$($case.League).scheduler.toml") (Join-Path $folder 'scheduler.toml')
}

# --- every command and group answers -h ----------------------------------
# generate-schedule is hidden from the list on purpose; it is called below.
$r = Athc @('--help')
$missing = @('autocontinue', 'check-ppp', 'config', 'convert-pdb', 'gameplan', 'playpool', 'profile' |
    Where-Object { $r.Out -notmatch "(?m)^\s+$([regex]::Escape($_))\s" })
Check "athc --help lists every command (missing: $($missing -join ', '))" (($r.Code -eq 0) -and ($missing.Count -eq 0))
$commands = @(
    'config', 'config edit', 'config path', 'config reveal', 'config set',
    'gameplan', 'gameplan check', 'gameplan find-play', 'gameplan list-normals',
    'gameplan list-specials', 'gameplan replace-play', 'gameplan set-normals',
    'gameplan set-specials', 'playpool', 'playpool check',
    'profile', 'profile check', 'profile copy', 'profile diff',
    'autocontinue', 'check-ppp', 'convert-pdb', 'generate-schedule'
)
foreach ($command in $commands) {
    $r = Athc (($command -split ' ') + '-h')
    Check "athc $command -h" (($r.Code -eq 0) -and ($r.Out -match 'Usage:'))
}

# --- config --------------------------------------------------------------
$r = Athc @('config', 'set', 'league', 'TEST')
Check 'config set league TEST' (($r.Code -eq 0) -and ($r.All -match 'Set league = TEST'))
$r = Athc @('config', 'path')
Check 'config path prints athc.ini' (($r.Code -eq 0) -and ($r.Out.Trim() -eq (Join-Path $cfgDir 'athc.ini')))
$r = Athc @('config', 'edit')
Check 'config edit opens athc.ini' ($r.Code -eq 0)
$r = Athc @('config', 'reveal')
Check 'config reveal shows athc.ini' ($r.Code -eq 0)

# --- profile -------------------------------------------------------------
foreach ($name in 'TST-OFF1', 'TST-DEF1') {
    $prf = Join-Path $data "$name.prf"
    $r = Athc @('profile', 'check', $prf)
    Check "profile check $name.prf: exit 1, report matches golden" (
        ($r.Code -eq 1) -and (Short $r.Out @($prf)).StartsWith((Golden "$name.report.txt")))
}
$base = Join-Path $data 'diff_base.prf'
$modified = Join-Path $data 'diff_modified.prf'
foreach ($ext in 'txt', 'csv') {
    $report = Join-Path $work "diff.$ext"
    $r = Athc @('profile', 'diff', $base, $modified, '-o', $report)
    $text = ''
    if (Test-Path $report) { $text = Short ([IO.File]::ReadAllText($report)) @($base, $modified) }
    Check "profile diff -o .${ext}: exit 1, report matches golden" (
        ($r.Code -eq 1) -and ($text -ceq (Golden "diff_all_fields.$ext")))
}
$r = Athc @('profile', 'copy', (Join-Path $data 'TST-OFF2.prf'), (Join-Path $work 'TST-OFF1.prf'), '--stop-clock')
Check 'profile copy --stop-clock: updated' (($r.Code -eq 0) -and ($r.All -match 'updated \(stop-clock\)'))

# --- gameplan ------------------------------------------------------------
foreach ($side in 'offense', 'defense') {
    $pln = Join-Path $data "$side.pln"
    $r = Athc @('gameplan', 'check', $pln)
    Check "gameplan check ${side}.pln: exit 1, report matches golden" (
        ($r.Code -eq 1) -and (Short $r.Out @($pln)).StartsWith((Golden "$side.report.txt")))
    $r = Athc @('gameplan', 'list-specials', $pln, '-')
    Check "gameplan list-specials ${side}.pln: matches golden" (
        ($r.Code -eq 0) -and ((Lines $r.Out) -ceq (Golden "${side}_specials.txt")))
}
$sorts = @(@('offense', 'slot'), @('offense', 'name'), @('offense', 'category'),
           @('defense', 'slot'), @('defense', 'category'))
foreach ($sort in $sorts) {
    $r = Athc @('gameplan', 'list-normals', (Join-Path $data "$($sort[0]).pln"), '-', '--sort', $sort[1])
    Check "gameplan list-normals $($sort[0]).pln --sort $($sort[1]): matches golden" (
        ($r.Code -eq 0) -and ((Lines $r.Out) -ceq (Golden "$($sort[0])_normals_$($sort[1]).txt")))
}
$target = Join-Path $work 'offense.pln'
$r = Athc @('gameplan', 'find-play', 'OR45RL01', $target)
Check 'gameplan find-play: found in slot 1-1' (($r.Code -eq 0) -and ($r.Out -match "'OR45RL01' found in slot 1-1"))
$r = Athc @('gameplan', 'replace-play', 'OR45RL01', 'DN28RM01', $target)
Check 'gameplan replace-play: replaced' (
    ($r.Code -eq 0) -and ($r.All -match "'OR45RL01' \(RL\) replaced with 'DN28RM01' \(RM\) \[1-1\]"))
$r = Athc @('gameplan', 'find-play', 'OR45RL01', $target)
Check 'gameplan find-play after replace-play: not found' (($r.Code -eq 1) -and ($r.Out -match 'not found'))
$r = Athc @('gameplan', 'set-normals', (Join-Path $work 'offense2.pln'), (Join-Path $work 'normals.txt'))
Check 'gameplan set-normals: updated' (($r.Code -eq 0) -and ($r.All -match 'Updated .*: 1 normal play'))
$r = Athc @('gameplan', 'set-specials', (Join-Path $work 'offense3.pln'), (Join-Path $work 'specials.txt'))
Check 'gameplan set-specials: updated' (($r.Code -eq 0) -and ($r.All -match '1 updated, 0 failed'))

# --- playpool, check-ppp, convert-pdb ----------------------------------------
$r = Athc @('playpool', 'check')
Check "playpool check (league play_path): 128 plays, 0 issues" (
    ($r.Code -eq 0) -and ($r.Out -match "128 play\(s\) checked in '.*', 0 issue\(s\)\."))
$prf = Join-Path $data 'TST-OFF1.prf'
$pln = Join-Path $data 'offense.pln'
$r = Athc @('check-ppp', $prf, $pln)
$want = Lines ((Raw 'compat_offense.report.txt') + (Raw 'offense.report.txt') +
               "`n2 file(s) checked, 22 violation(s) across 2 file(s).`n")
Check 'check-ppp profile + gameplan: exit 1, reports match goldens' (
    ($r.Code -eq 1) -and ((Short $r.Out @($prf, $pln)) -ceq $want))
$xlsx = Join-Path $work 'pdb.xlsx'
$r = Athc @('convert-pdb', (Join-Path $data '2045-2047.pdb'), $xlsx,
            '-o', (Join-Path $data 'offense.pln'), '-d', (Join-Path $data 'defense.pln'))
Check 'convert-pdb: exit 0, workbook written' (
    ($r.Code -eq 0) -and (Test-Path $xlsx) -and ((Get-Item $xlsx).Length -gt 0))
# An .xlsm carries the macros athc keeps as package data, so this proves the
# bundle has them.
$xlsm = Join-Path $work 'pdb.xlsm'
$r = Athc @('convert-pdb', (Join-Path $data '2045-2047.pdb'), $xlsm)
$macros = $false
if (($r.Code -eq 0) -and (Test-Path $xlsm)) {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [IO.Compression.ZipFile]::OpenRead($xlsm)
    try { $macros = [bool]($zip.Entries | Where-Object { $_.FullName -eq 'xl/vbaProject.bin' }) }
    finally { $zip.Dispose() }
}
Check 'convert-pdb .xlsm: exit 0, workbook carries the macros' $macros

# --- generate-schedule: a fixed seed reproduces the goldens -------------------
# The report's run-info fields vary by machine and run; blanked as the test does.
function Report([string]$html) {
    $html = Lines $html
    foreach ($label in 'CPU', 'Command line', 'Config path', 'Elapsed (s)') {
        $html = [regex]::Replace($html, '(<b>' + [regex]::Escape($label) + ':</b> ).*?(</p>)', '$1<normalized>$2')
    }
    $html
}
foreach ($case in $schedules) {
    $dir = Join-Path $work "schedule-$($case.League)"
    New-Item -ItemType Directory -Force $dir | Out-Null
    $r = Athc @('generate-schedule', '--league', $case.League, '--season', $case.Season, '--seed', '0') $dir
    $files = @(Get-ChildItem $dir -Filter "schedule_$($case.Season)_*")
    $txt = $files | Where-Object { $_.Extension -eq '.txt' }
    $html = $files | Where-Object { ($_.Extension -eq '.html') -and ($_.Name -notlike '*_report.html') }
    $report = $files | Where-Object { $_.Name -like '*_report.html' }
    $ok = ($r.Code -eq 0) -and ($files.Count -eq 3)
    if ($ok) {
        $ok = ((Lines ([IO.File]::ReadAllText($txt.FullName))) -ceq (Golden "schedule_$($case.Season).txt")) -and
              ((Lines ([IO.File]::ReadAllText($html.FullName))) -ceq (Golden "schedule_$($case.Season).html")) -and
              ((Report ([IO.File]::ReadAllText($report.FullName))) -ceq (Golden "schedule_$($case.Season)_report.html"))
    }
    Check "generate-schedule --league $($case.League): exit 0, three files match goldens" $ok
}

# --- autocontinue: watches the screen until stopped ----------------------------
$watch = Join-Path $out 'autocontinue'
$p = Start-Process $exe -ArgumentList 'autocontinue' -WorkingDirectory $work `
    -RedirectStandardOutput "$watch.out.txt" -RedirectStandardError "$watch.err.txt" `
    -NoNewWindow -PassThru
Start-Sleep 10
$alive = -not $p.HasExited
if ($alive) { Stop-Process -Id $p.Id -Force }
Check 'autocontinue: still watching after 10 s' $alive
# It looks for the Continue button only while the game has focus, which never
# happens here, so check the image it would load is in the bundle.
Check 'autocontinue: Continue button image bundled' (
    Test-Path (Join-Path $app '_internal\athc\autocontinue\images\continue_button.png'))

# Close what config edit and config reveal opened.
Get-Process notepad -ErrorAction SilentlyContinue | Stop-Process -Force
(New-Object -ComObject Shell.Application).Windows() | ForEach-Object { $_.Quit() }

# --- extra steps: the admin build's own commands ------------------------------
if (Test-Path $extra) { . $extra }

# --- upgrade (same setup.exe over the install) -------------------------------
$marker  = Join-Path $app '_internal\STALE_MARKER.txt'
$ini     = Join-Path $cfgDir 'athc.ini'
$rules   = Join-Path $leagues 'PNFL\gameplan.toml'
$deleted = Join-Path $leagues 'PNFL\standings\2049.league.ini'
$readme  = Join-Path $app 'README.txt'
$commands = Join-Path $app 'COMMANDS.txt'
Set-Content $marker 'left over from an older bundle'
Add-Content $ini '; user-edit-marker'
Add-Content $rules '# user-edit-marker'
Add-Content $commands 'old-doc-marker'
Remove-Item $deleted, $readme
Start-Process $setup -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/LOG=$out\install2.log" -Wait
Check 'upgrade: stale file wiped from _internal'  (-not (Test-Path $marker))
Check 'upgrade: edited athc.ini left alone'       ((Get-Content $ini -Raw) -match 'user-edit-marker')
Check 'upgrade: edited rule TOML left alone'      ((Get-Content $rules -Raw) -match 'user-edit-marker')
Check 'upgrade: missing seeded file added back'   (Test-Path $deleted)
Check 'upgrade: deleted README.txt added back'    (Test-Path $readme)
Check 'upgrade: docs refreshed (old COMMANDS.txt replaced)' (
    (Test-Path $commands) -and -not ((Get-Content $commands -Raw) -match 'old-doc-marker'))
Check 'upgrade: user-added league left alone'     (Test-Path (Join-Path $testLeague 'league.toml'))
$ver2 = (& $exe --version 2>&1 | Out-String).Trim()
Check "upgrade: athc still runs (got '$ver2')"    ($ver2 -match [regex]::Escape($version))

# --- uninstall ---------------------------------------------------------------
Start-Process (Join-Path $app 'unins000.exe') -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART' -Wait
$limit = (Get-Date).AddSeconds(20)   # the uninstaller's final cleanup is async
while (((Test-Path $app) -or (Test-Path $cfgDir)) -and (Get-Date) -lt $limit) { Start-Sleep 1 }
Check 'uninstall: install folder removed'         (-not (Test-Path $app))
Check 'uninstall: %LOCALAPPDATA%\athc removed'    (-not (Test-Path $cfgDir))
Check 'uninstall: start-menu shortcut removed'    (-not (Test-Path $lnk))
$regPath2 = (Get-ItemProperty 'HKCU:\Environment' -ErrorAction SilentlyContinue).Path
Check 'uninstall: install folder off user PATH'   (-not ($regPath2 -like "*$app*"))
Check 'uninstall: no admin-edition marker left'   (-not (Test-Path 'HKCU:\Software\Assistant to the Head Coach'))

Add-Content $results "SUMMARY  $pass pass, $fail fail"
Stop-Transcript | Out-Null
# The host stops the sandbox once it sees this file (release-test.ps1).
Set-Content (Join-Path $out 'DONE') 'done'
