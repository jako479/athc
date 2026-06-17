# athc release builder.
# Produces athc/dist/athc-<ver>/ (staged folder) and
# athc/dist/athc-<ver>.zip (release artifact, ready to ship).
#
# The zip bundles the project wheel + all transitive PyPI deps in packages/
# so install.bat can install offline (--no-index --find-links --offline).
#
# Run from anywhere; paths resolve relative to this script:
#     ./release/release-build.ps1

$ErrorActionPreference = "Stop"

$scriptRoot  = $PSScriptRoot                          # athc/release/
$projectRoot = Split-Path $scriptRoot -Parent         # athc/
$pyproject   = Join-Path $projectRoot "pyproject.toml"

$m = (Select-String -Path $pyproject -Pattern '^version\s*=\s*"(.+?)"').Matches[0]
if (-not $m) { throw "Could not read version from $pyproject" }
$version = $m.Groups[1].Value

$bundleName  = "athc-$version"
$distDir     = Join-Path $projectRoot "dist"
$staging     = Join-Path $distDir $bundleName
$packagesDir = Join-Path $staging "packages"
$zipPath     = Join-Path $distDir "$bundleName.zip"

Write-Host "Building athc v$version release..."

if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
New-Item -ItemType Directory -Path $packagesDir | Out-Null

# Build wheel. Pass $projectRoot explicitly so the build runs against this
# project regardless of the caller's working directory.
Write-Host "  Building wheel via uv build..."
& uv build --wheel --out-dir $distDir $projectRoot
if ($LASTEXITCODE -ne 0) { throw "uv build failed" }

$wheel = Get-ChildItem -Path $distDir -Filter "athc-$version-*.whl" |
         Sort-Object LastWriteTime -Descending |
         Select-Object -First 1
if (-not $wheel) { throw "Wheel 'athc-$version-*.whl' not found in $distDir" }

# Drop the project wheel into packages/, then download transitive deps into
# the same folder. install.bat installs from this dir via --find-links.
Write-Host "  Staging wheel: $($wheel.Name)"
Copy-Item $wheel.FullName $packagesDir

Write-Host "  Downloading transitive deps into packages/..."
# uv has no 'pip download' subcommand; use stdlib pip via Python.
# Python on PATH is required for this step (matches pnfl's prior approach).
# --find-links lets pip resolve athc itself from dist/; transitive deps come
# from PyPI. Both end up in packages/.
& python -m pip download --dest $packagesDir --find-links $distDir "athc==$version"
if ($LASTEXITCODE -ne 0) { throw "pip download failed" }

# Stage end-user-facing files at the staging root (sibling to packages/).
foreach ($name in "README.txt", "COMMANDS.txt", "SCHEDULER-COMMANDS.txt", "athc.ini", "athc.ini.example", "install.bat") {
    $src = Join-Path $scriptRoot $name
    Write-Host "  Staging: $name"
    Copy-Item $src $staging
}

# Stage the rules\ folder (shipped PNFL rule sets).
Write-Host "  Staging: rules\"
Copy-Item (Join-Path $scriptRoot "rules") $staging -Recurse

# Zip the staging folder so extracting produces a named folder.
Write-Host "  Creating zip..."
Compress-Archive -Path $staging -DestinationPath $zipPath

Write-Host ""
Write-Host "Done."
Write-Host "  Staged: $staging"
Write-Host "  Zip:    $zipPath"
