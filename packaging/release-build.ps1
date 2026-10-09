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

# The exact versions in uv.lock, the ones the tests ran against, plus the build
# group's PyInstaller. --locked stops the build when uv.lock is out of date.
# athc itself goes in after, with nothing left to resolve.
Write-Host "  Installing the locked dependencies, PyInstaller and athc..."
$requirements = Join-Path $buildDir "requirements.txt"
& uv export --project $projectRoot --locked --no-dev --group build --no-emit-project `
    --quiet --output-file $requirements
if ($LASTEXITCODE -ne 0) { throw "uv export failed - is uv.lock up to date?" }
& uv pip install --python $buildPython --requirement $requirements
if ($LASTEXITCODE -ne 0) { throw "uv pip install (locked dependencies) failed" }
& uv pip install --python $buildPython --no-deps $projectRoot
if ($LASTEXITCODE -ne 0) { throw "uv pip install (athc) failed" }
& uv pip check --python $buildPython
if ($LASTEXITCODE -ne 0) { throw "the build venv is missing a dependency" }

# onedir, not onefile: onefile unpacks itself to a temp folder on every run.
# athc finds its subcommands through entry points, which need athc's metadata
# and every athc module (no import reaches them); its package data (the
# autocontinue images, the pdbtoexcel resources) is not found by import
# scanning either. ortools keeps its native DLLs in ortools\.libs, which
# PyInstaller cannot resolve on its own and ships no hook for.
Write-Host "  Freezing with PyInstaller..."
& $buildPython -m PyInstaller `
    --onedir --console --name athc --noconfirm `
    --distpath $distDir --workpath (Join-Path $buildDir "pyinstaller") `
    --specpath $buildDir `
    --copy-metadata athc --collect-submodules athc --collect-data athc `
    --collect-binaries ortools `
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
    (Join-Path $scriptRoot "athc.iss")
if ($LASTEXITCODE -ne 0) { throw "Inno Setup compile failed - see its messages above" }
if (-not (Test-Path $setupExe)) { throw "Installer not found at $setupExe" }

$sizeMb = [math]::Round((Get-Item $setupExe).Length / 1MB, 1)

Write-Host ""
Write-Host "Done."
Write-Host "  Bundle:    $staging"
Write-Host "  Installer: $setupExe ($sizeMb MB)"
