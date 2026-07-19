# athc installer

How the athc release zip is built and how `install.bat` behaves on disk.

## End-user flow

1. Download release zip.
2. Extract.
3. Double-click `install.bat`.

Prerequisites (covered in the bundled `docs\README.txt`): Windows 10+, Python 3.12+, uv.

## Release zip

One wheel + docs + example config + season config + `install.bat` → `athc-<ver>.zip`. Produced by `release/release-build.ps1`, written to `dist/`. Dependencies are pulled from PyPI by `install.bat` (needs internet), not bundled.

## What lands on disk

All files deploy into `%LOCALAPPDATA%\athc\`.

| File | First install | Reinstall |
|---|---|---|
| `athc.ini` | seeded | **preserved** (user edits survive) |
| `<season>.league.ini`, `<season>.nonconf_history.json` | seeded | **preserved** (commish edits survive) |
| `rules\*.toml` | created | overwritten |
| `docs\*.txt` | created | overwritten |

The seeded `athc.ini` is a ready-to-run PNFL config: it points at the bundled `rules\` set with config-relative paths (`rules\PNFL.gameplan.toml`, resolved against the config dir — see [config.md](config.md#rule-file-paths)), so the only value a user must edit is `[league.PNFL] PlayPath` (their FbPro98 plays folder). It's a single self-documenting file — every setting is commented inline; there's no separate `.example` reference (the pgcli/mycli model).

The wheel goes into a uv-managed tool venv; executables on PATH at `%USERPROFILE%\.local\bin\`.

## Config evolution

In-code defaults are authoritative. Every section/key in `athc.ini` is optional; missing → tool uses the default from its own `config.py`.

Adding a new tool's `[logparser]` section in a release:

1. Tool runs with code defaults — user does nothing.
2. To customize, the user looks at the freshly-extracted `athc.ini` in the new zip (always the current commented reference), copies the new section into their own `athc.ini`, and edits.

`athc.ini` is never touched after first install. No migration step, no merge prompts, no clobber risk.

Pattern follows pgcli/mycli: a single self-documenting config, seeded once and left alone; defaults live in code, so new keys take effect without editing.

## Deprecation

When a tool sees a deprecated key: log a one-line startup warning, keep reading it for 2–3 releases, then drop. Pattern follows VS Code's `deprecationMessage`.

## Build pipeline

`release/` contains: `release-build.ps1`, `install.bat`, `athc.ini`, the season config files (`<season>.league.ini` / `<season>.nonconf_history.json`), and the `docs\` + `rules\` folders.

`release-build.ps1`:

1. Reads version from `pyproject.toml`.
2. Runs `uv build --wheel` to produce the project wheel.
3. Stages the wheel, `install.bat`, `athc.ini`, the season config files (`<season>.league.ini` / `<season>.nonconf_history.json`), and the `docs\` + `rules\` folders into `dist/<bundle-name>/`.
4. Zips to `dist/<bundle-name>.zip`.

Final user-facing artifact lands in `dist/` (standard Python build output).

`install.bat`:

1. Checks `uv` is on PATH (fails with the winget install command if not).
2. `uv tool install <bundled-wheel> --reinstall` — installs athc from the bundled wheel; **uv resolves the dependencies from PyPI** (needs internet).
3. `uv tool update-shell` so the tool's bin dir is on PATH.
4. Copies docs and the `rules\` folder into `%LOCALAPPDATA%\athc\` (overwrite).
5. Conditionally copies `athc.ini` and each season config file if missing.

Dependencies resolve from PyPI at install time (the normal approach), so uv picks wheels matching the user's Python — no pre-bundled compiled wheels (ortools, opencv) to mismatch. Trade-off: install needs internet.
