# athc — Architecture Overview

## What this is

`athc` is the umbrella CLI for Front Page Sports Football Pro '98 (FbPro98) league management. It's a normal Python package, managed with `uv`, built with `setuptools`, and shipped as a wheel. The umbrella discovers all subcommands at runtime via setuptools entry points, so any package installed in the same environment can extend it.

## Project layout

```
athc/
  pyproject.toml
  docs/                                  # internal docs (markdown, for repo readers)
  release/                               # source for end-user release bundle
    README.txt                           # user-facing readme
    COMMANDS.txt                         # per-command reference
    athc.ini                             # example config
    install.bat                          # end-user install script
    release-build.ps1                    # builds wheel + assembles zip into ../dist/
  src/athc/
    __init__.py
    __main__.py                          # python -m athc
    config.py                            # base INI reader + config_dir()

    # CLI WIRING (Click decorators; no tool logic)
    cli/
      __init__.py                        # AthcGroup + main() + shared decorators
      hello.py                           # athc hello (leaf)
      generate_schedule.py               # athc generate-schedule (leaf)
      convert_pdb.py                     # athc convert-pdb (leaf)
      autocontinue.py                    # athc autocontinue (leaf)
      gameplan/                          # athc gameplan ... (group with leaves)
        __init__.py                      # defines group
        check.py, list_plays.py, ...
      profile/                           # athc profile ... (group with leaves)
        __init__.py
        check.py, copy.py, diff.py

    # TOOLS (logic only; no Click)
    hello/           core.py
    gameplan/        config.py  model.py  rules.py  reader.py  writer.py
    profile/         config.py  model.py  diff.py   display.py
    scheduler/       config.py  main.py   domain/  schedulers/  writers/
    pdbtoexcel/      config.py  core.py
    autocontinue/    config.py  core.py  images/

    # LIBRARIES (no CLI; importable by tools and by other libs)
    playpool/                  py.typed  pool.py  records.py
    fbpro98_gameplan/          py.typed  model.py  reader.py  writer.py
    fbpro98_play/              py.typed  model.py  reader.py
    fbpro98_profile/           py.typed  model.py  reader.py  writer.py

    tools/                               # standalone scripts (non-subcommand)
      helloworld.py                      # demo; real standalones land here if needed
```

## Tools vs libraries

- **Tool**: has a CLI module under `<pkg>/cli/` (Click command or group) and a `pyproject.toml` entry-point registering it under `athc.commands`. Tool logic lives separately under `<pkg>/<tool>/`.
- **Library**: no `cli.py`, no entry-point, has `py.typed` so consumers get types. Imported by tools or by other libraries. Same wheel; nothing special about packaging.

A package can start as a library and grow a `cli/` later (or vice versa).

## Config handling

- Single shared INI file at `%LOCALAPPDATA%\athc\athc.ini`, read by `configparser`.
- Three section flavors: tool sections (lowercase, e.g. `[hello]`), league sections (UPPERCASE, e.g. `[PNFL]`), and `[DEFAULT]` for cross-cutting keys.
- Each tool owns its own `config.py` with a `Config` dataclass; missing keys/sections fall back to in-code defaults.
- Tools that operate on league-specific data take a `--league NAME` option.
- Dev override: set `ATHC_CONFIG_DIR` to point at a local `dev/` folder when running from source (matches `llm`, `httpie`, `tmuxp` pattern).
- Full structure, multi-league selection rules, dev override details, and deprecation: [config.md](config.md). File deploy/upgrade behavior: [installer.md](installer.md). CLI/run-from-source details: [cli.md](cli.md).

## Extension mechanism

`athc.cli.AthcGroup` (subclass of `click.Group`) discovers subcommands at runtime via `importlib.metadata.entry_points(group="athc.commands")`. Loading is lazy: first call to `list_commands` / `get_command` triggers it once, then caches.

Any package — built-in athc tool or third-party extension — registers its commands under the same `athc.commands` group in its `pyproject.toml`. The umbrella has zero knowledge of any specific tool, including its own built-ins. Installing an extension that depends on `athc` makes new commands appear in `athc --help` automatically; uninstalling makes them disappear. No code changes anywhere.

Extension packages can also extend athc libraries (e.g., a separate package importing from `athc.playpool` and adding behavior). Same Python import rules apply.

## Click and uv

- **Click** is the CLI framework. A custom `AthcGroup` (subclass of `click.Group`) lazy-loads subcommands via entry points. Built-in and extension commands register through the same `athc.commands` entry-point group. Full design + per-tool patterns: [cli.md](cli.md). Terminology cheat-sheet: [cli-terminology.md](cli-terminology.md).
- **uv** is the package/env manager. Replaces `pip` + `virtualenv` + `pip-tools`. Per-repo `.venv`. `uv venv` creates it, `uv pip install -e .` is editable install, `uv build` produces wheels, `uv tool install` installs a wheel as a system-wide CLI tool.

## Windows version support

**Windows 10 / 11 (default target):**
- Python 3.12+ (athc itself only needs 3.10 today; the predecessor codebase used PEP 695 type-alias syntax which requires 3.12, so 3.12 is the forward-looking floor for the eventual port).
- uv (binding constraint — uv requires Windows 10 or newer).
- Distribution: wheels installed via `install.bat` (current plan) or an Inno Setup `.exe` later.
- No package-version pins required for this path; all athc deps have modern wheels.

**Windows 7 (special-case path, not currently planned):**
- Python 3.8 — last version to support Windows 7. EOL October 2024, no security updates.
- No uv (Windows 10+ only).
- Distribution: PyInstaller-bundled `.exe` that embeds Python 3.8; Inno Setup wraps it. End user installs nothing.
- Heavy deps need these pinned versions (last to ship cp38 / Win7-compatible wheels on PyPI):
  - `ortools==9.12.4544` — next release (9.13) dropped cp38.
  - `opencv-python==4.6.0.66` — 4.7+ depends on newer UCRT, reported broken on Win7. Conservative choice; 4.7–4.9 may load with the Win7 Media Feature Pack installed but requires real-hardware verification.
  - `Pillow==10.4.0` — 11.0.0 release notes removed Python 3.8 support.
- No known conflicts among these three on Python 3.8 (`ortools` 9.12 needs `protobuf>=5.29,<6.0` and `numpy>=1.13.3`; both compatible with the pinned `opencv-python` / `Pillow`).
- Build only if a Windows 7 holdout actually appears.

## Build / install / release

**Development**
- Per-repo `.venv`: `uv venv && uv pip install -e ".[dev]"`.

**Build wheels**
- `uv build` writes wheel + sdist to `dist/`.

**Release zip + end-user install**
- `release/release-build.ps1` produces a self-contained release zip in `dist/` containing the wheel + bundled transitive deps + docs + install.bat. Full pipeline and `install.bat` behavior in [installer.md](installer.md). Versioning and release flow: [release.md](release.md).
