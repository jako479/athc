# athc installer

How the athc release zip is built and how `install.bat` behaves on disk.

## End-user flow

1. Download release zip.
2. Extract.
3. Double-click `install.bat`.

Prerequisites (covered in the bundled `README.txt`): Windows 10+, Python 3.12+, uv.

## Release zip

One wheel + bundled transitive deps + docs + example config + `install.bat` → `athc-<ver>.zip`. Produced by `release/release-build.ps1`, written to `dist/`.

## What lands on disk

All files deploy into `%LOCALAPPDATA%\athc\`.

| File | First install | Reinstall |
|---|---|---|
| `athc.ini` | seeded | **preserved** (user edits survive) |
| `athc.ini.example` | created | overwritten |
| `README.txt` | created | overwritten |
| `COMMANDS.txt` | created | overwritten |

The wheel goes into a uv-managed tool venv; executables on PATH at `%USERPROFILE%\.local\bin\`.

## Config evolution

In-code defaults are authoritative. Every section/key in `athc.ini` is optional; missing → tool uses the default from its own `config.py`.

Adding a new tool's `[logparser]` section in a release:

1. Tool runs with code defaults — user does nothing.
2. `install.bat` overwrites `athc.ini.example` so the new section is visible there.
3. To customize, user copies the section from `.example` into `athc.ini` and edits.

`athc.ini` is never touched after first install. No migration step, no merge prompts, no clobber risk.

Pattern follows Notepad++ (`config.model.xml`) and Sublime Text (`Default/Preferences.sublime-settings`).

## Deprecation

When a tool sees a deprecated key: log a one-line startup warning, keep reading it for 2–3 releases, then drop. Pattern follows VS Code's `deprecationMessage`.

## Build pipeline

`release/` contains: `release-build.ps1`, `install.bat`, `README.txt`, `COMMANDS.txt`, `athc.ini`.

`release-build.ps1` (requires Python on PATH at build time for `pip download`):

1. Reads version from `pyproject.toml`.
2. Runs `uv build --wheel` to produce the project wheel.
3. Copies the wheel into `dist/<bundle-name>/packages/`.
4. Runs `python -m pip download` to fetch every transitive PyPI dep wheel into the same `packages/` folder.
5. Stages `release/*` (docs, `install.bat`, `athc.ini`) into `dist/<bundle-name>/` alongside `packages/`.
6. Zips to `dist/<bundle-name>.zip`.

Output location matches PyInstaller / Briefcase / Hatch: final user-facing artifact in `dist/`.

`install.bat`:

1. Checks `uv` is on PATH (fails with the winget install command if not).
2. `uv tool install athc --no-index --find-links packages --offline --reinstall` — installs from the bundled `packages/` folder with no PyPI access.
3. `uv tool update-shell` so the tool's bin dir is on PATH.
4. Copies docs and `.example` files into `%LOCALAPPDATA%\athc\` (overwrite).
5. Conditionally copies `athc.ini` if missing.

Offline + bundled wheels was picked over online-resolve-at-install for **reproducibility** (every user gets the same dep versions) and **better failure modes** (PyPI outages, corporate firewalls, antivirus TLS interception still happen). Matches what Calibre, MusicBrainz Picard, BeeWare Briefcase, and python.org's embeddable guidance do for non-dev Windows audiences.
