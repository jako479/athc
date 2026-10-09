# Installer as a setup.exe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the zip + `install.bat` + uv flow with `athc-<ver>-setup.exe` (and the admin `athc-admin-<ver>-setup.exe`), tested end to end in Windows Sandbox.

**Architecture:** PyInstaller freezes athc into a onedir bundle in a throwaway Python 3.13 build venv; Inno Setup compiles the bundle, the release docs and the seed config into a per-user setup.exe. A sandbox test installs it silently, runs every command and subcommand on the integration-test fixtures, upgrades, and uninstalls. athc-admin's build and test reuse athc's `packaging/` files by path.

**Tech Stack:** PowerShell 5.1-compatible scripts, PyInstaller (build venv only), Inno Setup 6 (`ISCC.exe`), Windows Sandbox + `wsb`, uv.

**Spec:** `docs/design/TODO/installer-exe.md`

## Global Constraints

- Per-user install, no admin rights: `PrivilegesRequired=lowest`, install folder `%LOCALAPPDATA%\Programs\Assistant to the Head Coach`.
- App name "Assistant to the Head Coach"; command `athc.exe`; setup files `athc-<ver>-setup.exe` and `athc-admin-<ver>-setup.exe`.
- One app identity (AppId) for the public and the admin setup.exe.
- `%LOCALAPPDATA%\athc` files are seeded only if missing; uninstall removes the whole folder.
- Release docs go in the install folder, refreshed on every install.
- Build venv: Python 3.13; PyInstaller never enters the project's `.venv`.
- Scripts live in `packaging/` (both repos); installed files in `config/release/` (both repos).
- Every text file UTF-8, CRLF, final newline; scripts ASCII-only (Windows PowerShell 5.1 reads BOM-less files as ANSI).
- No mention of Claude, Anthropic or AI tools in commits, comments or docs.

## Review Focus

- The frozen exe finds no subcommands (entry points need metadata and every athc module) - Task 2's host smoke run calls each command's `-h`.
- ortools' native libraries missing from the bundle - Task 2 runs `generate-schedule` with the frozen exe on the host.
- An upgrade overwrites a user-edited seeded file - Task 3's upgrade checks edit `athc.ini` and a rule TOML first.
- Uninstall leaves `%LOCALAPPDATA%\athc` or the PATH entry behind - Task 3's uninstall checks.
- A console opened after install cannot run `athc` by name - Task 3 rereads PATH from the registry and runs `athc --version` through `cmd`.

---

### Task 1: Design doc, TODO and plan committed

**Files:**
- Create: `docs/design/TODO/installer-exe.md` (copied from main, plus the life-cycle table)
- Modify: `TODO.md` (copied from main: the installer line links the design)
- Create: `docs/superpowers/plans/2026-10-08-installer-exe.md` (this file)

- [ ] **Step 1:** In the design doc's "What athc needs" table, the Subcommands row also collects every athc module (no import reaches them; entry points load them by name).
- [ ] **Step 2:** Commit: `git add docs/design/TODO/installer-exe.md TODO.md docs/superpowers/plans/2026-10-08-installer-exe.md` then `git commit -m "installer: setup.exe design and plan"`.

### Task 2: athc build (entry script, Inno Setup script, build script)

**Files:**
- Create: `packaging/entry.py`
- Create: `packaging/athc.iss`
- Create: `packaging/release-build.ps1`

**Interfaces:**
- Produces: `dist/athc/athc.exe` (bundle) and `dist/athc-<ver>-setup.exe`.
- `athc.iss` defines: `AppVersion`, `StagingDir`, `ConfigDir`, `DocsDir`, `ChangelogFile`, `LicenseFile`, `OutputDir`, `OutputBaseName` (required); `AdminDocsDir` (optional, admin build).

- [ ] **Step 1: `packaging/entry.py`**

```python
"""PyInstaller entry point.

athc's `main()` lives in the `athc.cli` package, which has no `__main__`
guard, so the frozen build needs a script that calls it.
"""

from athc.cli import main

main()
```

- [ ] **Step 2: `packaging/athc.iss`**

```
; Inno Setup script for the athc installer.
;
; Compiled by packaging\release-build.ps1, which passes AppVersion, StagingDir,
; ConfigDir, DocsDir, ChangelogFile, LicenseFile, OutputDir and OutputBaseName
; with /D. athc-admin's build compiles this same script for the admin setup.exe
; and also passes AdminDocsDir. Running ISCC on this file directly fails on the
; #error checks below.

#ifndef AppVersion
  #error AppVersion must be passed with /DAppVersion=...
#endif
#ifndef StagingDir
  #error StagingDir must be passed with /DStagingDir=...
#endif
#ifndef ConfigDir
  #error ConfigDir must be passed with /DConfigDir=...
#endif
#ifndef DocsDir
  #error DocsDir must be passed with /DDocsDir=...
#endif
#ifndef ChangelogFile
  #error ChangelogFile must be passed with /DChangelogFile=...
#endif
#ifndef LicenseFile
  #error LicenseFile must be passed with /DLicenseFile=...
#endif
#ifndef OutputDir
  #error OutputDir must be passed with /DOutputDir=...
#endif
#ifndef OutputBaseName
  #error OutputBaseName must be passed with /DOutputBaseName=...
#endif

[Setup]
; One identity for the public and the admin setup.exe, so either one installs
; over the other in place.
AppId={{A60A37FC-32E8-41F5-BF9E-C78F8A2C53C2}
AppName=Assistant to the Head Coach
AppVersion={#AppVersion}
AppVerName=Assistant to the Head Coach {#AppVersion}
AppPublisher=Brian Jacobs
DefaultDirName={autopf}\Assistant to the Head Coach
DisableProgramGroupPage=yes
DisableDirPage=yes
; Per-user install: no admin rights needed.
PrivilegesRequired=lowest
OutputDir={#OutputDir}
OutputBaseFilename={#OutputBaseName}
Compression=lzma2
SolidCompression=yes
; The installer edits the user's PATH.
ChangesEnvironment=yes
WizardStyle=modern
UninstallDisplayName=Assistant to the Head Coach {#AppVersion}

[InstallDelete]
; Setup replaces files but never removes ones an older bundle had, and
; PyInstaller renames internals between builds - wipe the old bundle first.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
; The PyInstaller onedir bundle: athc.exe plus its interpreter and libraries.
Source: "{#StagingDir}\*"; DestDir: "{app}"; \
    Flags: recursesubdirs createallsubdirs ignoreversion
; Release docs are program files: refreshed on every install.
Source: "{#DocsDir}\*.txt"; DestDir: "{app}"; Flags: ignoreversion
; Renamed to .txt so double-clicking opens Notepad instead of prompting for an
; app.
Source: "{#ChangelogFile}"; DestDir: "{app}"; DestName: "CHANGELOG.txt"; \
    Flags: ignoreversion
Source: "{#LicenseFile}"; DestDir: "{app}"; DestName: "LICENSE.txt"; \
    Flags: ignoreversion
#ifdef AdminDocsDir
Source: "{#AdminDocsDir}\README.txt"; DestDir: "{app}"; \
    DestName: "README-admin.txt"; Flags: ignoreversion
Source: "{#AdminDocsDir}\COMMANDS.txt"; DestDir: "{app}"; \
    DestName: "COMMANDS-admin.txt"; Flags: ignoreversion
#endif
; User-owned config, in the folder athc reads it from: each file seeded only if
; it is missing, so edits survive an upgrade and a file new in a release is
; still added.
Source: "{#ConfigDir}\athc.ini"; DestDir: "{localappdata}\athc"; \
    Flags: onlyifdoesntexist
Source: "{#ConfigDir}\leagues\*"; DestDir: "{localappdata}\athc\leagues"; \
    Flags: recursesubdirs createallsubdirs onlyifdoesntexist

[Icons]
Name: "{autoprograms}\Assistant to the Head Coach README"; \
    Filename: "{app}\README.txt"

[UninstallDelete]
; The whole config folder, user edits and added files included.
Type: filesandordirs; Name: "{localappdata}\athc"

[Registry]
; Put athc.exe on PATH for this user.
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; \
    ValueData: "{olddata};{app}"; Check: NeedsAddPath(ExpandConstant('{app}'))

[Run]
Filename: "{app}\README.txt"; Description: "Open the README"; \
    Flags: postinstall shellexec skipifsilent nowait

[Code]
{ True when Dir is not already one of the entries in the user's PATH. }
function NeedsAddPath(Dir: string): Boolean;
var
  Existing: string;
begin
  if not RegQueryStringValue(HKCU, 'Environment', 'Path', Existing) then
  begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Uppercase(Dir) + ';', ';' + Uppercase(Existing) + ';') = 0;
end;

{ Drop the install dir from PATH on uninstall, leaving other entries intact. }
procedure RemoveFromPath(Dir: string);
var
  Existing: string;
  Cleaned: string;
  Part: string;
  P: Integer;
begin
  if not RegQueryStringValue(HKCU, 'Environment', 'Path', Existing) then
    exit;
  Cleaned := '';
  Existing := Existing + ';';
  repeat
    P := Pos(';', Existing);
    Part := Trim(Copy(Existing, 1, P - 1));
    Existing := Copy(Existing, P + 1, Length(Existing));
    if (Part <> '') and (Uppercase(Part) <> Uppercase(Dir)) then
    begin
      if Cleaned <> '' then
        Cleaned := Cleaned + ';';
      Cleaned := Cleaned + Part;
    end;
  until Existing = '';
  RegWriteExpandStringValue(HKCU, 'Environment', 'Path', Cleaned);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    RemoveFromPath(ExpandConstant('{app}'));
end;
```

- [ ] **Step 3: `packaging/release-build.ps1`**

```powershell
# athc release builder.
#
# Produces athc/dist/athc/ (the PyInstaller onedir bundle) and
# athc/dist/athc-<ver>-setup.exe (the artifact to ship).
#
# The setup.exe carries its own Python interpreter and every dependency, so the
# user's PC needs nothing installed beforehand and no internet at install time.
#
# Build prerequisites: uv, and Inno Setup 6 (winget install JRSoftware.InnoSetup).
#
# Run from anywhere; paths resolve relative to this script:
#     ./athc/packaging/release-build.ps1

$ErrorActionPreference = "Stop"

$scriptRoot  = $PSScriptRoot                          # athc/packaging/
$projectRoot = Split-Path $scriptRoot -Parent         # athc/
$pyproject   = Join-Path $projectRoot "pyproject.toml"
$release     = Join-Path $projectRoot "config\release"

$m = (Select-String -Path $pyproject -Pattern '^version\s*=\s*"(.+?)"').Matches[0]
if (-not $m) { throw "Could not read version from $pyproject" }
$version = $m.Groups[1].Value

$distDir  = Join-Path $projectRoot "dist"
$buildDir = Join-Path $projectRoot "build"
$staging  = Join-Path $distDir "athc"
$setupExe = Join-Path $distDir "athc-$version-setup.exe"

# Inno Setup installs per-user by default, per-machine when run as admin.
$iscc = @(
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $iscc) {
    throw "Inno Setup 6 not found. Install it with: winget install JRSoftware.InnoSetup"
}

Write-Host "Building athc v$version release..."

foreach ($path in $staging, $setupExe, $buildDir) {
    if (Test-Path $path) { Remove-Item $path -Recurse -Force }
}

# Freeze into a throwaway venv rather than the repo's shared .venv, so the
# bundle carries only the runtime dependencies and never a dev tool.
$buildVenv   = Join-Path $buildDir "venv"
$buildPython = Join-Path $buildVenv "Scripts\python.exe"

Write-Host "  Creating build venv..."
& uv venv --python 3.13 $buildVenv
if ($LASTEXITCODE -ne 0) { throw "uv venv failed" }

Write-Host "  Installing athc and PyInstaller..."
& uv pip install --python $buildPython $projectRoot pyinstaller
if ($LASTEXITCODE -ne 0) { throw "uv pip install failed" }

# onedir, not onefile: onefile unpacks itself to a temp folder on every run.
# athc finds its subcommands through entry points, which need athc's metadata
# and every athc module (no import reaches them); its package data (the
# autocontinue images, the pdbtoexcel resources) is not found by import
# scanning either.
Write-Host "  Freezing with PyInstaller..."
& $buildPython -m PyInstaller `
    --onedir --console --name athc --noconfirm `
    --distpath $distDir --workpath (Join-Path $buildDir "pyinstaller") `
    --specpath $buildDir `
    --copy-metadata athc --collect-submodules athc --collect-data athc `
    (Join-Path $scriptRoot "entry.py")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
if (-not (Test-Path (Join-Path $staging "athc.exe"))) {
    throw "PyInstaller did not produce $staging\athc.exe"
}

Write-Host "  Compiling installer with Inno Setup..."
& $iscc `
    "/DAppVersion=$version" `
    "/DStagingDir=$staging" `
    "/DConfigDir=$release" `
    "/DDocsDir=$(Join-Path $release 'docs')" `
    "/DChangelogFile=$(Join-Path $projectRoot 'CHANGELOG.md')" `
    "/DLicenseFile=$(Join-Path $projectRoot 'LICENSE')" `
    "/DOutputDir=$distDir" `
    "/DOutputBaseName=athc-$version-setup" `
    (Join-Path $scriptRoot "athc.iss") | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Inno Setup compile failed" }
if (-not (Test-Path $setupExe)) { throw "Installer not found at $setupExe" }

$sizeMb = [math]::Round((Get-Item $setupExe).Length / 1MB, 1)

Write-Host ""
Write-Host "Done."
Write-Host "  Bundle:    $staging"
Write-Host "  Installer: $setupExe ($sizeMb MB)"
```

- [ ] **Step 4: Build.** Run `packaging\release-build.ps1` (PowerShell tool). Expected: "Done." and the setup.exe size.
- [ ] **Step 5: Host smoke run of the frozen exe** (`dist\athc\athc.exe`, `ATHC_CONFIG_DIR` pointed at a scratch copy of a test config): `--version`; `-h` on every command and group; `generate-schedule --league divisions --season 2026 --seed 0` (ortools). Note each command's real exit code and output shape for Task 3.
- [ ] **Step 6: ortools.** If `generate-schedule` fails on a missing ortools file, add `--collect-all ortools` to the PyInstaller call (the "project-local hook" the design names), rebuild, rerun Step 5.
- [ ] **Step 7: Commit:** `git add packaging/entry.py packaging/athc.iss packaging/release-build.ps1` then `git commit -m "installer: PyInstaller + Inno Setup build"`.

### Task 3: athc sandbox test

**Files:**
- Create: `packaging/release-test.ps1`
- Create: `packaging/sandbox-steps.ps1`

**Interfaces:**
- Consumes: `dist/athc-<ver>-setup.exe`; `tests/integration/data` and `tests/integration/expected`.
- Produces: `release-test.ps1 [-SetupExe <path>] [-ExtraSteps <ps1>] [-ExtraData <dir>]`. `-ExtraSteps` is dot-sourced inside the sandbox after athc's command checks, so it can call `Check`, `Athc`, `Lines` and use `$work`, `$out`, `$cfgDir`; `-ExtraData` maps in as `Desktop\extra`.

- [ ] **Step 1: `packaging/release-test.ps1`** - pdf-converter's `release-test.ps1` with: the athc setup.exe and bundle paths; the three optional parameters; mapped folders `dist` (the setup.exe's folder), `data` and `expected` (from `tests\integration`), `assets` (`sandbox-steps.ps1`, `version.txt`, `setup.txt`, and `extra-steps.ps1` when given), `extra` (when given), `out` (writable); a 45-minute deadline (two full schedule solves).
- [ ] **Step 2: `packaging/sandbox-steps.ps1`** - pdf-converter's `sandbox-steps.ps1` shape (`Check`, results.txt, transcript, DONE file) with these sections:
  - install: `athc.exe`; the five docs in the install folder; `athc.ini`, PNFL and PCFL `league.toml`, a rule TOML and a standings file seeded; Start-menu shortcut; install folder on the user PATH; `--version`; `athc --version` by name in a console whose PATH is reread from the registry.
  - fixtures: `data` copied to `C:\test\data`; league `TEST` = the seeded PNFL `league.toml` with `play_path` at the fixture pool, plus the test rule files and the seeded PNFL `pdbtoexcel.toml`; leagues `divisions` / `conferences` = the scheduler goldens' standings and rules.
  - every command and group: `--help` lists all eight commands; `-h` on each group and subcommand exits 0 with `Usage:`.
  - real runs: `config set league TEST`, `config path`, `config edit`, `config reveal`; `profile check` (TST-OFF1 / TST-DEF1 golden reports), `profile diff -o .txt/.csv` (goldens), `profile copy --stop-clock`; `gameplan check` (offense / defense goldens), `list-normals -` (slot / name / category goldens), `list-specials -` (goldens), `find-play`, `replace-play`, `set-normals`, `set-specials`; `playpool check`; `check-ppp` (profile + gameplan); `convert-pdb` with `-o`/`-d`; `generate-schedule` for both test leagues (goldens, report normalized as in the test); `autocontinue` still running after 10 s.
  - extra steps (when given).
  - upgrade: stale `_internal` file gone; edited `athc.ini` and rule TOML kept; a deleted seeded file added back; docs refreshed; `--version`.
  - uninstall: install folder, `%LOCALAPPDATA%\athc`, shortcut and PATH entry gone.
- [ ] **Step 3: Run** `packaging\release-test.ps1`. Fix until every line is PASS.
- [ ] **Step 4: Commit:** `git add packaging/release-test.ps1 packaging/sandbox-steps.ps1` then `git commit -m "installer: Windows Sandbox release test"`.

### Task 4: athc-admin build and test (athc-admin worktree)

**Files (athc-admin):**
- Create: `packaging/release-build.ps1`, `packaging/release-test.ps1`, `packaging/sandbox-steps.ps1`
- Move: `release/README.txt` and `release/COMMANDS.txt` to `config/release/docs/`
- Delete: `release/install.bat`, `release/release-build.ps1`

- [ ] **Step 1: `packaging/release-build.ps1`** - athc's build with: `-AthcRoot` (default the sibling `..\athc`); the build venv installs `$AthcRoot`, athc-admin and PyInstaller with `--no-sources` (athc-admin's editable `../athc` source never enters the bundle); PyInstaller also gets `--copy-metadata athc-admin --collect-submodules athc_admin --collect-data athc_admin`; ISCC compiles `$AthcRoot\packaging\athc.iss` with athc's config, docs, changelog and license, `AdminDocsDir` = `config\release\docs`, output `athc-admin-<ver>-setup`.
- [ ] **Step 2: `packaging/sandbox-steps.ps1`** - the admin extra steps: `logparser -h` and each subcommand's `-h`; `rebuild-db`, `seed-coaches`, `import-plays`, `import-logs` on the logparser fixtures into a scratch database; the admin docs in the install folder.
- [ ] **Step 3: `packaging/release-test.ps1`** - runs `$AthcRoot\packaging\release-test.ps1 -SetupExe <admin setup.exe> -ExtraSteps sandbox-steps.ps1 -ExtraData tests\logparser\data`.
- [ ] **Step 4:** Build and run the admin sandbox test; fix until every line is PASS.
- [ ] **Step 5: Commit** in athc-admin: `installer: admin setup.exe from athc's packaging`.

### Task 5: Docs

- [ ] athc: `docs/design/installer.md` rewritten to describe the setup.exe build for athc and athc-admin; `docs/design/TODO/installer-exe.md` retired; `docs/design/release.md` release steps; `config/release/docs/README.txt` requirements and install sections; STATUS.md, CHANGELOG.md, README.md as affected; TODO.md installer task ticked.
- [ ] athc-admin: `docs/design/installer.md` points at athc's `installer.md`; `docs/design/release.md` steps; `config/release/docs/README.txt` install section; STATUS.md / README.md as affected.
- [ ] Commit each repo.

### Task 6: Verify and hand off

- [ ] athc: `uv run pytest`, `uv run ruff check .`, `uv run ruff format .`, `uv run pyright` (one per call).
- [ ] One whole-branch review; fix findings.
- [ ] Close and delete the sandbox and its work folders.
- [ ] Leave the worktree; give the two hand-off code blocks per repo.
