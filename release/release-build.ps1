# athc release builder.
# Produces athc/dist/athc-<ver>/ (staged folder) and
# athc/dist/athc-<ver>.zip (release artifact, ready to ship).
#
# The zip bundles the project wheel; install.bat installs it with uv and pulls
# dependencies from PyPI at install time (needs internet).
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
$zipPath     = Join-Path $distDir "$bundleName.zip"

Write-Host "Building athc v$version release..."

if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
New-Item -ItemType Directory -Path $staging | Out-Null

# Build wheel. Pass $projectRoot explicitly so the build runs against this
# project regardless of the caller's working directory.
Write-Host "  Building wheel via uv build..."
& uv build --wheel --out-dir $distDir $projectRoot
if ($LASTEXITCODE -ne 0) { throw "uv build failed" }

$wheel = Get-ChildItem -Path $distDir -Filter "athc-$version-*.whl" |
         Sort-Object LastWriteTime -Descending |
         Select-Object -First 1
if (-not $wheel) { throw "Wheel 'athc-$version-*.whl' not found in $distDir" }

# Stage the project wheel; install.bat installs it and uv pulls deps from PyPI.
Write-Host "  Staging wheel: $($wheel.Name)"
Copy-Item $wheel.FullName $staging

# Stage root-level end-user files.
foreach ($name in "athc.ini", "install.bat") {
    Write-Host "  Staging: $name"
    Copy-Item (Join-Path $scriptRoot $name) $staging
}

# Stage season config files: <season>.league.ini / <season>.nonconf_history.json.
foreach ($pattern in "*.league.ini", "*.nonconf_history.json") {
    Get-ChildItem -Path $scriptRoot -Filter $pattern | ForEach-Object {
        Write-Host "  Staging: $($_.Name)"
        Copy-Item $_.FullName $staging
    }
}

# Stage the docs\ folder (README + per-command references) and the rules\ folder.
foreach ($dir in "docs", "rules") {
    Write-Host "  Staging: $dir\"
    Copy-Item (Join-Path $scriptRoot $dir) $staging -Recurse
}

# Zip the staging folder so extracting produces a named folder.
Write-Host "  Creating zip..."
Compress-Archive -Path $staging -DestinationPath $zipPath

Write-Host ""
Write-Host "Done."
Write-Host "  Staged: $staging"
Write-Host "  Zip:    $zipPath"
