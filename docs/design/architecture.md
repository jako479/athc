# athc — Architecture

How athc is built, then the conventions every command and library follows.
Precedents for the choices: [reference-projects.md](reference-projects.md).

## What this is

`athc` is the umbrella CLI of tools for Front Page Sports Football Pro '98 coaches and league managers. It's a normal Python package, managed with `uv`, built with `setuptools`, and shipped as a wheel. The umbrella discovers all subcommands at runtime via setuptools entry points, so any package installed in the same environment can extend it.

## Project layout

```
athc/
  pyproject.toml
  docs/                                  # internal docs (markdown, for repo readers)
  config/
    dev/                                 # dev config (ATHC_CONFIG_DIR), mirrors release\
      athc.ini
      leagues/                           # per-league league.toml, rule TOMLs, standings\
    release/                             # source for the end-user release
      docs/                              # user-facing docs (README, COMMANDS, ...)
      athc.ini                           # example config
      leagues/                           # per-league league.toml, rule TOMLs, standings\
  src/athc/
    __init__.py
    __main__.py                          # python -m athc
    config.py                            # base INI reader + config_dir()/config_file()

    # CLI WIRING (Click decorators; no tool logic)
    cli/
      __init__.py                        # AthcGroup + main() + shared decorators
      check_ppp.py                       # athc check-ppp (leaf)
      generate_schedule.py               # athc generate-schedule (leaf)
      convert_pdb.py                     # athc convert-pdb (leaf)
      autocontinue.py                    # athc autocontinue (leaf)
      gameplan/                          # athc gameplan ... (group with leaves)
        __init__.py                      # defines group
        check.py, find_play.py, list_normals.py, list_specials.py,
        replace_play.py, set_normals.py, set_specials.py
      profile/                           # athc profile ... (group with leaves)
        __init__.py
        check.py, copy.py, diff.py
      playpool/                          # athc playpool ... (group with leaves)
        __init__.py
        check.py
      config/                            # athc config ... (group with leaves)
        __init__.py
        path.py, edit.py, reveal.py, set.py

    # TOOLS (logic only; no Click)
    gameplan/        config.py  model.py  rules.py  reader.py  writer.py
    profile/         config.py  model.py  diff.py   display.py
    scheduler/       config.py  main.py   domain/  schedulers/  writers/
    pdbtoexcel/      config.py  core.py
    autocontinue/    config.py  core.py  images/

    # LIBRARIES (importable by tools and by other libs; playpool also has a CLI)
    playpool/                  py.typed  model.py  reader.py  rules.py
    fbpro98_gameplan/          py.typed  model.py  reader.py  writer.py
    fbpro98_lg2/               py.typed  model.py  reader.py
    fbpro98_play/              py.typed  model.py  reader.py
    fbpro98_profile/           py.typed  model.py  reader.py  writer.py
```

## Tools vs libraries

- **Tool**: has a CLI module under `<pkg>/cli/` (Click command or group) and a `pyproject.toml` entry-point registering it under `athc.commands`. Tool logic lives separately under `<pkg>/<tool>/`.
- **Library**: no `cli.py`, no entry-point, has `py.typed` so consumers get types. Imported by tools or by other libraries. Same wheel; nothing special about packaging.

A package can start as a library and grow a `cli/` later (or vice versa).

## What goes where

| Concern                                          | Location                                                        |
| ------------------------------------------------ | --------------------------------------------------------------- |
| Umbrella `AthcGroup` + plugin loader + `main()`  | `athc/cli/__init__.py`                                          |
| Shared option decorators (`league_option`, etc.) | `athc/cli/__init__.py`                                          |
| Leaf command (single action)                     | `<pkg>/cli/<name>.py`                                           |
| Command group + its leaves                       | `<pkg>/cli/<group>/__init__.py` + `<pkg>/cli/<group>/<leaf>.py` |
| Per-tool config reader + `Config` dataclass      | `<pkg>/<tool>/config.py`                                        |
| Per-tool logic (model, readers, writers)         | `<pkg>/<tool>/` (other modules)                                 |

CLI wiring is kept separate from tool logic: Click decorators live under `cli/`, tool code under `<tool>/` and stays free of Click. The umbrella discovers and dispatches; it never imports from a specific tool.

## Library docs

Each library's `docs/<lib>/README.md` is its quickstart and API reference: Features, Setup, Usage, then an API section listing the public functions, classes and exceptions, one short entry each. A file-format spec under `docs/<lib>/specs/` holds only the byte layout, the validity rules and the open questions of the format, never function names or exceptions.

- [playpool](../playpool/README.md)
- [fbpro98_gameplan](../fbpro98_gameplan/README.md)
- [fbpro98_lg2](../fbpro98_lg2/README.md)
- [fbpro98_play](../fbpro98_play/README.md)
- [fbpro98_profile](../fbpro98_profile/README.md)

## Extension mechanism

`athc.cli.AthcGroup` (subclass of `click.Group`) discovers subcommands at runtime via `importlib.metadata.entry_points(group="athc.commands")`. Loading is lazy: the first `--help` or subcommand invocation triggers it once, then caches. A plugin that fails to import fails loudly (Flask's choice) rather than silently disappearing.

Any package, built-in athc tool or third-party extension, registers its commands the same way: under the `athc.commands` group in its own `pyproject.toml`. The umbrella has zero knowledge of any specific tool, including its own built-ins. Installing an extension that depends on `athc` makes new commands appear in `athc --help` automatically; uninstalling makes them disappear. No code changes anywhere. Extensions can mirror athc's `<pkg>/cli/` + `<pkg>/<tool>/` layout, but the umbrella doesn't care.

Extension packages can also extend athc libraries (e.g., a separate package importing from `athc.playpool` and adding behavior). Same Python import rules apply.

## Click and uv

- **Click** is the CLI framework, picked over Typer and argparse: it is the mainstream choice for plugin-extensible Python CLIs (Flask, Poetry, MkDocs, dbt, ruff, Black), its `Group` subclass hook gives lazy plugin discovery in a few lines (Flask's `FlaskGroup._load_plugin_commands`), Typer's plugin story is weaker, and argparse would make every plugin build its own parser. Terminology follows Click: `athc` is the root, `gameplan` a command group, `list-normals` a leaf command; what follows the leaf is arguments (positional) and options (flags); nesting is unlimited.
- **uv** is the package/env manager. Replaces `pip` + `virtualenv` + `pip-tools`. Per-repo `.venv`. `uv sync` creates it and installs everything from the committed `uv.lock`, `uv add` adds a dependency, `uv run` runs a command inside it, `uv build` produces wheels, `uv tool install` installs a wheel as a system-wide CLI tool.

## Running from source

Source runs read a per-machine **dev config** instead of the installed one: `ATHC_CONFIG_DIR`, if set, replaces the whole config dir (resolution: [`athc.config.config_dir()`](../../src/athc/config.py)); else the default `%LOCALAPPDATA%\athc` wins. The dev config is a full `athc.ini` plus league folders in `config/dev/` (mirrors `config/release/`), shared by athc and athc-admin. End users never set the var. Where to set it for VS Code and one-off runs: [README.md](../../README.md#development).

## Windows version support

**Windows 10 / 11 (default target):**
- Python 3.12+ (athc itself only needs 3.10 today; the predecessor codebase used PEP 695 type-alias syntax which requires 3.12, so 3.12 is the forward-looking floor for the eventual port).
- uv (binding constraint — uv requires Windows 10 or newer).
- Distribution: a PyInstaller-built installer `.exe` is the plan ([TODO.md](../../TODO.md)); the `install.bat` + wheel zip is gone.
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
- Per-repo `.venv`: `uv sync`. Dev tools live in the `dev` dependency group and install by default.

**Build wheels**
- `uv build` writes wheel + sdist to `dist/`.

**End-user install**
- The release zip script and `install.bat` are gone; the installer is a TODO ([TODO.md](../../TODO.md)). Config deploy/upgrade rules: [installer.md](installer.md). Versioning and release flow: [release.md](release.md).

## Cross-cutting conventions

Rules that hold across every command and library. Each tool's own behavior is in its `docs/<tool>/` README and ARCHITECTURE.

### CLI

- Every group and command passes `context_settings=CONTEXT_SETTINGS`, so `-h` and `--help` work everywhere and each command shows its own help.
- The usage line is POSIX / argparse style, not Click's `[OPTIONS]`: each option, help first, then the arguments (`athc gameplan list-normals [-h] [--sort slot|name|category] [--league name] gameplan [output_file]`); a long line wraps between options, never inside one. Groups use `CommandGroup` (the root `AthcGroup` builds on it), standalone commands `cls=AthcCommand`; a group's subcommands get it automatically.
- Argument names and option values show in lowercase with underscores (`metavar="pdb_file"`), never Click's capitals.
- Bare `athc` prints help (`no_args_is_help=True`); `--version` reads the installed metadata (`click.version_option(package_name="athc")`), no hard-coded version; `python -m athc` works via `athc/__main__.py`.
- Every command and group has a one-line help, written from the user's side ("Advance the sim to the next decision", not "Read the [autocontinue] section"); `show_default=True` where a default matters.
- `--league name` is an option on each league-aware command (`gameplan check` / `replace-play` / `set-normals` / `set-specials` / `list-normals`, `profile check`, `check-ppp`, `playpool check`, `convert-pdb`, `generate-schedule`), applied with the shared `league_option` decorator and taken as `league: str | None`. It goes after the command name like `aws s3 ls --profile x` and `kubectl get --context x`; it is not on the root group because Click only takes a group's options before the subcommand name. Commands that never read league data don't have it. Selection: `--league` → `[athc] league` → an error naming `athc config set league` and listing the league folders.
- All dependencies are required (no opt-in extras): the installer must deliver every tool working. A tool with a heavy dependency (`generate-schedule` / ortools, `autocontinue` / pyautogui) imports it lazily inside the command, so discovery and `--help` survive a broken install; on `ImportError` it logs `missing <module> -- reinstall athc`, exits 1, and has a test for the missing import.

### Exit codes

Whether `1` means findings or error depends on whether the command can report a **finding**: a problem in otherwise-valid input, distinct from the command failing to run. A new command picks its class by that one question.

**Commands with a findings tier** (`gameplan check`, `profile check`, `check-ppp`, `playpool check`, `profile diff`, `find-play`, and the multi-file editors `set-specials`, `replace-play`, `profile copy`) follow the grep/diff convention:

| Exit | Meaning |
|---|---|
| `0` | Clean: no problems (identical; all files updated). |
| `1` | Findings: ran, but found problems (violations, play pool issues, differences, no play found, some files failed). |
| `2` | Error: couldn't run (usage, config, I/O, no rules, a profile/gameplan side mismatch). |

**Commands without** (`list-normals`, `list-specials`, `convert-pdb`, `set-normals`, `generate-schedule`, `autocontinue`, `config`) follow the common end-user-CLI convention (calibre, khal, beets):

| Exit | Meaning |
|---|---|
| `0` | OK. |
| `1` | Error: anything went wrong (I/O, config, missing dependency). |
| `2` | Usage: bad arguments (Click's default). |

Warnings never change the exit code. The code is computed once after the work loop, so a multi-file run processes and reports every file before it exits. Per-tool specifics are in each tool's README.

### Output streams

- **stdout** (`click.echo`, never `print()`): everything the user reads, results and status alike (reports, lists, "Updated …", "Wrote N plays"), with no level prefixes so it pipes cleanly. A command that edits files in place still echoes its status line (the `cp -v` convention). `-q/--quiet`, where offered, skips the success line only.
- **stderr** (`logging`): errors and warnings only. `logger.error` is a failure, fatal or per-item; the exit code comes from control flow, not the log level. CLI commands never call `logger.info` / `logger.warning`.
- **Libraries** never print results and never configure handlers: `logger.warning` for a recoverable "skipped X" notice, `logger.info` for progress, never `logger.error` (the app decides what's fatal). So library progress such as `convert-pdb`'s "Conversion complete" lands on stderr.
- The log level is fixed; there is no option or config key for it.
- An unexpected exception (a bug, not an anticipated error) is caught once in the umbrella `main()`, logged as one line, exit 2, no traceback; `ATHC_DEBUG=1` re-raises it.
- **Not yet as designed.** Handler setup belongs in one place, the root group callback; today each leaf command calls `basicConfig` and output is uncolored. The console, color and run-log rework is the pdf-converter TODO ([pdf-converter-conventions.md](TODO/pdf-converter-conventions.md)); the deviations are listed in [LOGGING-IS-FUCKED.md](TODO/LOGGING-IS-FUCKED.md).

### Output files

- A produced file goes where the user says; by default it lands next to its source (`list-normals` writes `<name>.normals.txt` beside the gameplan) or in the current directory (`generate-schedule`), never in a fixed app folder (`platformdirs` is for config, not output). `-` means stdout where a command offers it.
- An existing file at the path is replaced.
- Missing folders in the path are created in full, the way pandoc, 7-Zip and yt-dlp do it; never one level only.
- Whatever writes the file makes that call, CLI or library, so the rule holds for every caller.
- A command that edits a file in place (`set-normals`, `set-specials`, `replace-play`, `profile copy`) never creates its target; a missing path is an error.
- **Not yet as designed.** Today `convert-pdb`, `list-normals`, `list-specials` and `profile diff -o` all stop with an error when the folder is missing.

### Config

- `athc.ini` is INI via stdlib `configparser`, the Windows convention a user edits in Notepad; `%LOCALAPPDATA%\athc\athc.ini`, resolved with `platformdirs`, or the whole dir replaced by `ATHC_CONFIG_DIR` ([Running from source](#running-from-source)). Each league's `league.toml` and rule files are TOML via stdlib `tomllib`: nested tables, quoted keys with spaces, comments. `configparser` is the only mainstream option with native `[DEFAULT]` cascade and `%(key)s` interpolation; pydantic-settings, dynaconf and confuse don't fit. If load-site validation ever hurts, the upgrade is `pydantic.dataclasses.dataclass` on each `Config` class, keeping `configparser` as the loader.
- `athc.ini` holds only app-wide sections (`[athc] league`, `[autocontinue]`, `[convert-pdb]`). Everything per-league lives in one folder per league under `leagues\`, named by the folder, with fixed well-known file names nothing lists in config: `league.toml`, `gameplan.toml`, `profile.toml`, `playpool.toml`, `pdbtoexcel.toml`, `scheduler.toml`, `standings\<season>.league.ini`.
- `[league]` in `league.toml` holds the per-league values that are not files in the folder (`path`, the folder holding the league's files; `play_path`, the plays folder; athc-admin's `db_path`, `log_dir`); values are strings or arrays of strings, relative paths resolve against the league folder.
- `[categories.offense]` / `[categories.defense]` in `league.toml` give the league's short names for the game's play categories, keyed by the game's name (`"Run Right" = "RR"`); the shipped files list every category of each side in the game's order, the unlabeled ones commented out. Rule files, play-pool folders, `replace-play` and `convert-pdb`'s category order all use these labels (game name where the league has none); special-teams categories have no labels. A key that is not a category of its side, an empty or repeated label, or a label equal to a category name is a `ConfigFileError`. Code: `CategoryLabels` in `athc.fbpro98_play`, carried as `LeagueConfig.categories`.
- Each tool reads its one fixed rule file from the league folder; an optional array in `league.toml` (`gameplan_rules`, `profile_rules`) replaces it with an ordered set, later files overriding earlier. No command-line option overrides the league's rules or play pool, and there is no shared default outside the league folders.
- `athc config path | edit | reveal | set` locate, open, reveal and write `athc.ini`; thin wrappers over `click.launch` and ConfigUpdater (so comments survive; `configparser` drops them on write), no `[config]` section. `set league` validates the folder first.
- An unreadable `athc.ini` or `league.toml` (wrong value type, bad label) raises `ConfigFileError`; a missing or unknown league raises `LeagueError`.
- Each tool owns `<tool>/config.py`: a frozen `Config` dataclass with typed defaults and a `load(league)` that asks the resolved `LeagueConfig` for what the tool needs (`path(key)`, `rules_file(name)` / `rule_files(key, default)`, `categories`). `athc.ini` values come back as strings, so type conversion is the tool's job.
- In-code defaults are authoritative: missing file, section or key means defaults; a tool errors only when a value it needs at runtime can't be resolved (`play_path` not on disk). A new tool's `[section]` runs on defaults after an upgrade; the user copies it from the freshly shipped, self-documenting `athc.ini` (the pgcli/mycli model; deploy rules in [installer.md](installer.md)).
- A deprecated key keeps working for 2–3 releases with a one-line stderr warning at startup naming the replacement (VS Code's `deprecationMessage` pattern), then goes.
