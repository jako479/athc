# athc — Architecture

How athc is built, then the conventions every command and library follows.
Precedents for the choices: [reference-projects.md](reference-projects.md).

## What this is

`athc` is the umbrella CLI of tools for Front Page Sports Football Pro '98 coaches and league managers. It's a normal Python package, managed with `uv`, built with `setuptools`, and shipped as a wheel. The umbrella discovers all subcommands at runtime via setuptools entry points, so any package installed in the same environment can extend it.

## Project layout

```
athc/
  pyproject.toml
  docs/
    README.md                            # index, one line per doc
    installer.md                         # the setup.exe
    release.md                           # the release flow
    usage/                               # the end-user docs the installer ships (plain text)
    design/                              # the design docs: architecture, testing, one per tool and library
      TODO/                              # pending designs and plans
    formats/                             # every file-format spec with its patterns
    research/                            # research notes; what the game and the league do
  config/
    dev/                                 # dev config (ATHC_CONFIG_DIR), mirrors release\
      athc.toml
      leagues/                           # per-league league.toml and rule TOMLs
    release/                             # the seed config the installer installs
      athc.toml                           # example config
      leagues/                           # per-league league.toml and rule TOMLs
  src/athc/
    __init__.py
    __main__.py                          # python -m athc
    config.py                            # athc.toml reader + config_dir()/config_file(), league resolution
    errors.py                            # AthcError + the shared config, league and rules errors
    fileio.py                            # atomic_write: a temp file beside the target, swapped in
    console.py                           # the one console: prints every line, logs each status line
    log.py                               # the athc logger and the rotating run log

    # CLI WIRING (Click decorators; no tool logic)
    cli/
      __init__.py                        # AthcGroup / AthcCommand with main(), the one place; shared decorators
      _files.py                          # collect_files for the batch commands
      _team.py                           # the league files, the team resolver, where a team's files are
      check_ppp.py                       # athc check-ppp (leaf)
      generate_schedule.py               # athc generate-schedule (leaf)
      convert_pdb.py                     # athc convert-pdb (leaf)
      autocontinue.py                    # athc autocontinue (leaf)
      standings.py                       # athc standings (leaf)
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
        path.py, edit.py, reveal.py, get.py, set.py

    # TOOLS (logic only; no Click)
    gameplan/        config.py  model.py  rules.py  reader.py  writer.py
    profile/         config.py  model.py  diff.py   display.py
    scheduler/       config.py  main.py   league_files.py  domain/  schedulers/  writers/
    pdbtoexcel/      config.py  main.py  pdb.py  workbook_creator.py  excel_workbook.py
    autocontinue/    config.py  main.py  images/
    standings/       records.py  views.py

    # LIBRARIES (importable by tools and by other libs; playpool also has a CLI)
    playpool/                  py.typed  model.py  reader.py
    fbpro98_gameplan/          py.typed  schema.py  model.py  reader.py  writer.py
    fbpro98_lg2/               py.typed  schema.py  model.py  reader.py
    fbpro98_lge/               py.typed  schema.py  model.py  reader.py  _standings.py
    fbpro98_play/              py.typed  schema.py  model.py  reader.py  labels.py
    fbpro98_profile/           py.typed  schema.py  model.py  reader.py  writer.py
    fbpro98_standings/         py.typed  standings.py  methods.py  steps.py  moves.py  season.py
    fbpro98_stats/             py.typed  schema.py  model.py  reader.py
```

## Tools vs libraries

- **Tool**: has a CLI module under `<pkg>/cli/` (Click command or group) and a `pyproject.toml` entry-point registering it under `athc.commands`. Tool logic lives separately under `<pkg>/<tool>/`.
- **Library**: no `cli.py`, no entry-point, has `py.typed` so consumers get types. Imported by tools or by other libraries. Same wheel; nothing special about packaging.

A package can start as a library and grow a `cli/` later (or vice versa).

## What goes where

| Concern                                          | Location                                                        |
| ------------------------------------------------ | --------------------------------------------------------------- |
| Umbrella `AthcGroup` + plugin loader + `main()`  | `athc/cli/__init__.py`                                          |
| Shared option decorators (`league_option`, `team_option`) | `athc/cli/__init__.py`                                 |
| Leaf command (single action)                     | `<pkg>/cli/<name>.py`                                           |
| Command group + its leaves                       | `<pkg>/cli/<group>/__init__.py` + `<pkg>/cli/<group>/<leaf>.py` |
| Per-tool config reader + `Config` dataclass      | `<pkg>/<tool>/config.py`                                        |
| Per-tool logic (model, readers, writers)         | `<pkg>/<tool>/` (other modules)                                 |

CLI wiring is kept separate from tool logic: Click decorators live under `cli/`, tool code under `<tool>/` and stays free of Click. The umbrella discovers and dispatches; it never imports from a specific tool.

## Docs

`docs/` holds `release.md` and `installer.md` beside one folder per kind of doc, flat inside, the file name the subject. [README.md](../README.md) indexes every doc, one line each.

- `docs/usage/`: the end-user docs the installer ships, plain text: `README.txt`, one file per command (`gameplan.txt`, `profile.txt`, ...: what it does, examples, options, settings, lines and exit codes) and `USAGE_ORIGINAL.txt`.
- `docs/design/`: the design docs. `architecture.md`, `testing-unit.md`, `testing-integration.md` and `reference-projects.md`, then one doc per tool or library, named after its package (`fbpro98_lge.md`, `check_ppp.md`): for a tool `## How it works`, the layout, the boundaries and the design, its usage being in `docs/usage/`; for a library Features, Setup, Usage, then an API section listing the public functions, classes and exceptions, one short entry each, then `## How it works`. A module's extra docs take its name as a prefix (`scheduler-phase-1-matchups.md`).
- `docs/design/TODO/`: pending designs and plans, `<topic>-design.md` and `<topic>-plan.md`; a finished pair folds what lasts into the docs and goes (the hand-off rule in `AGENTS.md`), so finished work has no doc of its own beyond the design docs and `CHANGELOG.md`.
- `docs/formats/`: every file-format spec with its ImHex (`.hexpat`) and Hex Workshop (`.hsl`) patterns, and a README saying what each game file holds. A spec holds only the byte layout, the validity rules and the open questions of the format, never function names or exceptions. A format takes its extension where one format owns it (`lge.md`), the file's content where it does not (`cities.md`, `stats.md`) and its purpose where it is not a game file (`schedule-import.md`); a pattern shares its spec's stem.
- `docs/research/`: research notes, and what was learned about the game and the league (`fbpro98-game-behavior.md`, `pnfl-history.md`).
- Everything else is kebab-case.

## Extension mechanism

`athc.cli.AthcGroup` (subclass of `click.Group`) discovers subcommands at runtime via `importlib.metadata.entry_points(group="athc.commands")`. Loading is lazy: the first `--help` or subcommand invocation triggers it once, then caches. A plugin that fails to import fails loudly (Flask's choice) rather than silently disappearing.

Any package, built-in athc tool or third-party extension, registers its commands the same way: under the `athc.commands` group in its own `pyproject.toml`. The umbrella has zero knowledge of any specific tool, including its own built-ins. Installing an extension that depends on `athc` makes new commands appear in `athc --help` automatically; uninstalling makes them disappear. No code changes anywhere. Extensions can mirror athc's `<pkg>/cli/` + `<pkg>/<tool>/` layout, but the umbrella doesn't care.

Extension packages can also extend athc libraries (e.g., a separate package importing from `athc.playpool` and adding behavior). Same Python import rules apply.

## Click and uv

- **Click** is the CLI framework, picked over Typer and argparse: it is the mainstream choice for plugin-extensible Python CLIs (Flask, Poetry, MkDocs, dbt, ruff, Black), its `Group` subclass hook gives lazy plugin discovery in a few lines (Flask's `FlaskGroup._load_plugin_commands`), Typer's plugin story is weaker, and argparse would make every plugin build its own parser. Terminology follows Click: `athc` is the root, `gameplan` a command group, `list-normals` a leaf command; what follows the leaf is arguments (positional) and options (flags); nesting is unlimited.
- **uv** is the package/env manager. Replaces `pip` + `virtualenv` + `pip-tools`. Per-repo `.venv`. `uv sync` creates it and installs everything from the committed `uv.lock`, `uv add` adds a dependency, `uv run` runs a command inside it, `uv build` produces wheels, `uv tool install` installs a wheel as a system-wide CLI tool.

## Running from source

Source runs read a per-machine **dev config** instead of the installed one: `ATHC_CONFIG_DIR`, if set, replaces the whole config dir (resolution: [`athc.config.config_dir()`](../../src/athc/config.py)); else the default `%LOCALAPPDATA%\athc` wins. The dev config is a full `athc.toml` plus league folders in `config/dev/` (mirrors `config/release/`). `ATHC_LOG_DIR` does the same for the run log folder ([Console, run log and errors](#console-run-log-and-errors)); the test suite sets both, so no test touches the real config or log. End users never set either. Where to set them for VS Code and one-off runs: [README.md](../../README.md#development).

## Windows version support

**Windows 10 / 11 (default target):**
- Python 3.13+.
- uv (binding constraint — uv requires Windows 10 or newer).
- Distribution: a per-user `athc-<ver>-setup.exe`, a PyInstaller bundle wrapped by Inno Setup, carrying its own Python ([installer.md](../installer.md)).
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
- Per-repo `.venv`: `uv sync`. Dev tools live in the `dev` dependency group and install by default. PyInstaller lives in a `build` group, used only by the release build.

**Build wheels**
- `uv build` writes wheel + sdist to `dist/`.

**End-user install**
- `packaging/release-build.ps1` builds `dist/athc-<ver>-setup.exe`; `packaging/release-test.ps1` tests it in Windows Sandbox. Build, config deploy and upgrade rules: [installer.md](../installer.md). Versioning and release flow: [release.md](../release.md).

## Cross-cutting conventions

Rules that hold across every command and library. Each tool's own behavior is in its `docs/usage/<tool>.txt`, its design in `docs/design/<tool>.md`.

### CLI

- Every group and command passes `context_settings=CONTEXT_SETTINGS`, so `-h` and `--help` work everywhere and each command shows its own help.
- Help is Click's own (Click 8.5 or later), with no custom usage code: the usage line is `[OPTIONS]` then the arguments (`athc gameplan list-normals [OPTIONS] GAME_PLAN [OUTPUT]`), and a group's ends in `COMMAND [ARGS]...`. Groups use `CommandGroup` (the root `AthcGroup` builds on it), standalone commands `cls=AthcCommand`; a group's subcommands get it automatically.
- Placeholders are UPPERCASE with underscores, one name per kind of value: `PATH` (a file or a folder, or a wildcard where athc expands one), `GAME_PLAN` (one .pln), `PROFILE` (one .prf), `FOLDER` (a folder only), `INPUT_FILE` (a play list; `-` is stdin), `OUTPUT` (a file or a folder for the one file a command writes; `-` is stdout where a command offers it), `OUTPUT_FOLDER` (the folder for several files), `FILE` (a file named outright). An argument's placeholder comes from its parameter name (`game_plan` gives `GAME_PLAN`, an optional `output` `[OUTPUT]`); no argument has a metavar, and an argument holds one kind of value (the game plans' location is `--path`, never a last positional). Option values take a metavar (`--league NAME`).
- An argument's help is its own line in Click's "Positional arguments" section (`click.argument(..., help=...)`), under its bare name (`PATH`, not `[PATH]...`; `format_arguments` on the shared command class), while the usage line and Click's error hints keep Click's form (`[PATH]...`, `Missing argument 'REPLACEMENT...'.`); a description names placeholders in caps.
- Help text uses Windows words (folder, subfolder, wildcard, File Explorer, Ctrl+C), but stdout and stdin for the streams (`use '-' for stdout`, `use '-' for stdin`), "game plan" and "play pool" (the command names stay `gameplan` and `playpool`), and "Check", not "Validate", for the `check` commands. Shared options read the same everywhere: `-r, --recursive  Include subfolders.` and `--league NAME  League to use (default: the one set with 'athc config set league').`
- Help text writes these one way:
  - Defaults: `(default: ...)` at the end of the help, never Click's `[default: ...]` or "on by default".
  - In single quotes: commands (`run 'athc check-ppp'`), settings (`'play_path' in league.toml`) and `'-'` (`use '-' for stdout`).
  - Not quoted: option names (`--league`), option values (`slot`, `(default: game)`), placeholders (`GAME_PLAN`) and file names (`league.toml`).
- An option that overrides a setting says so (`Overrides 'hot_corner' in athc.toml.`) and never states the setting's value, which the user may have changed.
- Click's Windows wildcard expansion is off (`windows_expand_args` defaults to False in the one place): it would expand every word before the command sees it. athc expands wildcards itself, in `collect_files`, and a name that exists is a name, never a wildcard, so a folder like `Season [2029]` works.
- Bare `athc` (or a bare group) prints help on stderr and exits 2 (`no_args_is_help=True`); the run log gets `ERROR no command given; help shown`, not the help text; `--version` reads the installed metadata (`click.version_option(package_name="athc")`), no hard-coded version; `python -m athc` works via `athc/__main__.py`.
- Every command and group has a one-line summary that starts with a verb and fits the command list (55 characters or fewer), written from the user's side ("Advance the sim to the next decision", not "Read the [autocontinue] section").
- A command's description is one to four lines (rule details belong in the tool's docs), and its help ends with one to six real examples under `Examples:`; a command that takes the four names shows their key block just above the examples.
- No athc command has a quiet flag: `> nul` hides the `OK` lines and keeps every `FAIL` on standard error. An on/off pair over an `athc.toml` boolean is `--x/--no-x` with no default, help `<what it does>. Overrides '<key>' in athc.toml.` (`convert-pdb --percentages`). An optional `OUTPUT` defaults to the input's name with the product's extension, beside the input; a binary product refuses `-`; [Output files](#output-files) has the full rules.
- `--league NAME` is an option on each league-aware command (every `gameplan` command, `profile check` / `diff` / `copy`, `check-ppp`, `playpool check`, `convert-pdb`, `generate-schedule`, `standings`, `config path` / `edit` / `reveal` / `get` / `set`), applied with the shared `league_option` decorator and taken as `league: str | None`. It goes after the command name like `aws s3 ls --profile x` and `kubectl get --context x`; it is not on the root group because Click only takes a group's options before the subcommand name. Commands that never read league data don't have it. Selection: `--league` → `[athc] league` → an error naming `athc config set league` and listing the league folders.
- `--team NAME` is the shared `team_option(head)` decorator beside `league_option`, on each command that finds a team's files (`check-ppp`, every `gameplan` command, `profile check` / `diff` / `copy`, `convert-pdb`): the head says what the team is for on that command, the tail `(default: 'team' in league.toml).` is the same everywhere. The team layer it serves is `athc/cli/_team.py`: the league's `.lg2` and `.lge` read together (`load_league_files`), a name resolved to one team (`resolve_team`), a team's four files of a kind (`team_files`), and where each file is (`locate`: a folder, else its league location). It also holds what those commands share around them: the `--team` and `team` checks, whether a team is yours, the `ppp_path` check, which operand is a name, and the not-set lines and hints, each ending with the command's own way out.
- The four names `off1`, `def1`, `off2`, `def2` (game plan keys in `gameplan`, profile keys in `profile`) stand for your team's 1st-half offense, 1st-half defense, 2nd-half offense and 2nd-half defense file wherever a game plan or profile operand is, matched without case; a path that exists wins over a name, and so does an operand with an extension or a folder separator. A name's file is found in `ppp_path` (your team only), else at its league location; `--team` with a path and no name is a usage error (the batch commands take `--team` with `--path` left out; `convert-pdb` takes `--team` with no game plan option).
- All dependencies are required (no opt-in extras): the installer must deliver every tool working. A tool with a heavy dependency (`generate-schedule` / ortools, `autocontinue` / pyautogui) imports it lazily inside the command, so discovery and `--help` survive a broken install; on `ImportError` it raises `AthcError("Missing <module>. Reinstall athc.")`, so the user sees `FAIL Missing <module>. Reinstall athc.` and exit 2, and has a test for the missing import.

### Console, run log and errors

The pattern is pdf-converter's, which the research of 2026-10-08 (git, ruff, grep, pip, Black, clig.dev, Rich) confirmed as the mainstream one: results on stdout, everything else on stderr, every status line also in a run log, one error base class, one place that turns errors into exit codes, the same codes in every command.

| Piece | Module | Job |
|---|---|---|
| Console | `athc/console.py` | The one `AthcConsole` instance, `console`, prints every line a command shows, colors the label word and writes the matching log line. |
| Run log | `athc/log.py` | The `athc` logger, `log_path()` and `setup_logging()`; the rotating `athc.log`. |
| Errors | `athc/errors.py` | `AthcError(reason, path)`, the base of every expected error: it carries the reason and, when one file is to blame, that file's path, and composes `<path>: <reason>` itself. The shared `ConfigFileError`, `LeagueError`, `RulesFileError`, and `FileFormatError` (a broken game file); every library error subclasses one. The wording helpers: `reason_of` (an `OSError` in Windows' words), `missing_reason`, `error_line` (the `FAIL` line for an `AthcError` or an `OSError`), `sentence`, `toml_reason`; `athc.config.not_set_line` composes every `<Setting> is not set. Run 'athc config set ...'` line. |
| The one place | `athc/cli/__init__.py` | `main` on `AthcCommand` and `CommandGroup` (so on `AthcGroup`): opens the log, runs Click in non-standalone mode and turns whatever comes out into a line, a log entry and an exit code. |

**Message kinds.** Only these calls print; nothing in `src/athc` calls `click.echo`, `print()` or `logging.basicConfig`.

| Kind | Call | Console line | Stream | Log level |
|---|---|---|---|---|
| Result: the command's product (report lines, lists, a diff) | `console.print(text)` | plain | stdout | no |
| One item done | `console.ok(msg)` | `OK   msg` | stdout | INFO |
| One item skipped on purpose | `console.skip(msg)` | `SKIP msg` | stdout | INFO |
| Tally, or one headline per item with findings | `console.result(msg)` | plain | stdout | INFO |
| Progress of a long run | `console.progress(msg)` | plain | stderr | INFO |
| Warning: noted, nothing failed | `console.warn(msg)` | `WARN msg` | stderr | WARNING |
| Failure: one item, or the run | `console.fail(msg)` | `FAIL msg` | stderr | ERROR |
| Bug | `console.unexpected(what)` | `FAIL what: Unexpected error. See <path> for details.` | stderr | ERROR with traceback |

- Only those four words are labels, padded to five characters. No `athc <command>:` prefix, no timestamps, no `INFO:` on the console.
- A line about a file starts with its path, once: `OK   x.pln: updated (3 special play(s))`, `FAIL x.pln: Not a .pln file.`
- `warn` and `fail` print every line of a message as its own labeled line and log entry, so a rules file with several problems is several `FAIL` lines and nothing prints unlabeled.
- Findings (violations, play-pool issues, differences, a play not found) are results: a headline per file through `result`, so the log holds one line per file, then the detail lines through `print`.
- A command that takes a directory ends with a tally through `result`; a single-file command does not.
- The console writes each log line itself, so nothing is written twice and no command touches `logging`.

**Color.** Rich decides: on for a terminal, off when piped or redirected; `NO_COLOR` set to anything non-empty turns it off, `FORCE_COLOR` turns it on; no athc option, no config key. Green `OK`, cyan `SKIP`, yellow `WARN`, red `FAIL`, only the word. Both consoles are built with `soft_wrap=True`, `highlight=False`, `markup=False` and `emoji=False`: a line is never wrapped, numbers and paths are never restyled, and a detail line such as `  [Run Left] message` or `:x:` prints verbatim instead of being read as markup or an emoji, so `2> err.log` holds whole plain lines.

**Run log.** `athc.log` under `platformdirs.user_log_path("athc", appauthor=False)` (`%LOCALAPPDATA%\athc\Logs`), 1 MB x 5 files, UTF-8, each line `YYYY-MM-DD HH:MM:SS LEVEL message`: the level once (`INFO`, `WARNING`, `ERROR`), then the console line without its `WARN` or `FAIL` label (`OK` and `SKIP` lines keep theirs; a usage error is `ERROR <Click's text>`); `ATHC_LOG_DIR` replaces the folder the way `ATHC_CONFIG_DIR` replaces the config dir (tests, dev runs); no option, no config key. A log folder that cannot be created or written is one `FAIL <path>: <reason>` line and exit 2 before anything runs. Every run writes the start line (`athc <version> <args>`), every OK / SKIP / result / progress / WARN / FAIL line, every traceback and the end line (`exit <code>`); results are never logged. The `athc` logger never propagates and carries a `NullHandler` from import, so nothing from `logging` reaches the console, and a command run under `CliRunner` without the file handler never prints a line twice through `logging.lastResort`.

**Exit codes.** The same numbers in every command, so a script treats 2 as "athc could not do it" everywhere.

| Code | Meaning |
|---|---|
| `0` | Done. Clean, or warnings only. |
| `1` | Findings: ran fine and reported problems in valid input (violations, play-pool issues, differences, a play found nowhere, nothing replaced, no valid replacement). Only the checker and finder commands ever use it: `gameplan check`, `find-play`, `replace-play`, `profile check`, `profile diff`, `check-ppp`, `playpool check`. |
| `2` | Error: could not do the job. Usage, config, league, a missing or bad input, a file that failed inside a batch, a missing dependency, a bug. |
| `130` | Ctrl-C. `autocontinue` stops on Ctrl-C by design, so there it is 0. |

- Usage errors stay Click's: its `Usage: ... Error: ...` text on stderr, 2. The one place ends the message with a period where Click leaves it off (`Got unexpected extra argument (x).`), so no command re-raises Click's message just to add one.
- A batch processes every item, then exits with the worst outcome: error beats findings beats clean. Warnings never change the code. A bug is an error, not a special code; the log holds the traceback.
- A command lets a startup problem (config, league, rules, the one named file) propagate; a named file that does not exist is `FAIL <path>: The system cannot find the file specified.` (`Access is denied.` for a folder, as `type` says) through `named_file` in `athc/cli/_files.py`, checked before anything reads it; uses `ctx.exit(1)` for findings; inside a batch loop catches `AthcError | OSError` per item (`FAIL` with `error_line(error)`, which names the file, or the item when the error names none; count, continue) and `Exception` per item (`unexpected`, count, continue); then exits `2 if failed else 1 if findings else 0`. The batch commands collect their files with `collect_files` in `athc/cli/_files.py`; a directory with no matching files is a `WARN`, the tally still prints, and the code is 0 (`find-play`: 1, nothing found).
- The one place handles everything that comes out of Click: a `ClickException` shows its own text (a usage error ending in a period) and exits with its code (Click's no-args help is logged as `ERROR no command given; help shown`, not as its text); `Abort` (Ctrl-C) prints `FAIL Interrupted.` and exits 130; `AthcError` or `OSError` prints `FAIL` and `error_line(error)` and exits 2; any other exception prints the `unexpected` line, logs the traceback and exits 2; a normal return exits with the command's code. `python -m athc` goes through it, and so does a command run under `CliRunner`, which is why the tests assert the lines and codes without a subprocess.
- A tool with a heavy dependency (`generate-schedule` / ortools, `autocontinue` / pyautogui) turns the `ImportError` into `AthcError("Missing <module>. Reinstall athc.")`: `FAIL Missing <module>. Reinstall athc.`, 2.

**Wording.** Every `FAIL` and `WARN` line reads the way Windows' own command-line tools word errors.

- Shape: `<path>: <Sentence.>`, a line in a file `<path>: line N: <Sentence.>`; no path when no single file is to blame. The sentence after the last location (`<path>:`, `line N:`, `[section] key:`) starts with a capital and ends with one period; names and keys keep their own case, so a key never starts the sentence (it joins the location instead: `[x].mandatory: Must be a list.`). A hint is a second sentence on the same line.
- File problems use Windows' phrases: `The system cannot find the file specified.` (missing file), `The system cannot find the path specified.` (missing folder), `Access is denied.` (no access, a folder given for a file), `The directory name is invalid.` (a file given for a folder), `Cannot create a file when that file already exists.`, `Unspecified error.` (an error with no text); anything else is Windows' own text as a sentence. A config file athc cannot open fails with its phrase; it is never read as empty. `reason_of` picks the phrase from the error's Windows code (any other code keeps Windows' own text, such as `The process cannot access the file because it is being used by another process.`), or from its kind when it has no code, so one problem always reads one way.
- Plain values: lists read `A, B, C`, bytes `0x07`; no Python brackets, reprs or Markdown backticks.
- No line quotes a path; a line about a folder starts with it, like a line about a file.
- One form per kind: `Not valid TOML: <parser text>.`, `<where>: Must be a table.`, `<where>: Unknown key(s): a, b. Valid: x, y.` (one line per table; `(top)` for top-level keys).
- A command hint is `Run 'athc <command>'`, a sentence of its own, with what for after it when needed (`Run 'athc gameplan check' to check a game plan alone.`). Messages say "game plan", "play pool" and "special", like the help; a play the pool lacks `is not in the play pool`.
- Click usage errors keep Click's frame. Inside `Invalid value for '<x>':` athc's part continues Click's sentence, so it starts lowercase; a bare usage error is its own sentence after `Error:`, so it starts with a capital. Both end with a period.
- Findings, `OK` / `SKIP` lines and tallies keep their own wording.

**Libraries and tool packages** (the Click-free code) never print, never import the console, never configure `logging`, never log. A failure raises an `AthcError` subclass with the reason and, when one file is to blame, its path; the error composes `<path>: <reason>` itself, so a command prints `error_line(error)` and never adds a path of its own. Readers wrap every model `ValueError` in their own error, so a command never catches a bare `ValueError`. Warnings and findings come back as values with the result (`PlayPool.issues`, `PDB.warnings`, `ConversionResult.warnings`, `violations`). Live progress goes through an optional `progress: Callable[[str], None]` parameter that the command wires to `console.progress`; a loop that cannot return its warnings (`autocontinue`) takes a `warn` callback the same way.

Per command: each tool's doc carries its lines, what counts as a finding, and its codes.

### File libraries

The six `fbpro98_*` file libraries (`play`, `gameplan`, `profile`, `lg2`, `lge`, `stats`) share one shape, the one openpyxl, pydicom, mutagen and tomlkit use: read a file into a mutable object, edit it by assignment, write it back. The `.pyr` library, when it comes, takes the same shape.

- **Layout.** `schema.py` holds the `struct` layouts, block ids and field sizes; `model.py` the dataclasses; `reader.py` the parser and the library's error; `writer.py` the builder, where the library writes. One `InvalidXError(FileFormatError)` per library; a file class on top (`GamePlan`, `Profile`, `PlayFile`, `Lg2File`, `LgeFile`, `StatsFile`) holds the file's header data and its collections.
- **Models.** Every class in a `model.py` is `@dataclass(slots=True)`, never frozen; collections are `list` (in the file's order, or the order the field's doc states: a standings list best first, the stats honors by id) or `dict[int, ...]` keyed by id, with `field(default_factory=...)` for an empty default; a derived collection property returns a list too. Equality is field by field, so a mutable model is not hashable: callers key by `id(obj)` or by a number. A sub-object is shared on assignment, as with any Python object; a caller that wants two independent copies uses `copy.deepcopy`. The library-wide test `tests/unit/test_slots.py` pins every file model as mutable and slotted. Configuration and private working data stay frozen (`CategoryLabels`, the readers' private records).
- **Editing.** Plain assignment on the object, in place: `plan.normal_plays[0] = CustomPlayRef(...)`, `profile.situations[7].stop_clock = True`. No `with_*` copies, no `dataclasses.replace`, no `.save()` on a model; a tool's edit function takes the model and edits it, resolving its whole input first so a failure leaves the model as it was (`apply_normal_plays`, `replace_in_gameplan`).
- **validate().** A file class that is written has one `validate()` covering everything the format imposes: counts, slot alignment, the sides, string lengths and value ranges, field widths. It raises `ValueError` naming the record or field and the value (`Normal slot 1: Record offset must be at most 65535, got 65536`, `situation 4: weight1: Must be 0-10, got 11`); nothing is checked at construction, so a half-built or mid-edit model is allowed. `parse_x` builds the model from the bytes and calls it, turning a `ValueError` into the library's `InvalidXError` as `<path>: <message>.`; `build_x` calls it before packing and lets the `ValueError` out: an invalid model at write time is a programming error, not a file problem, so no command catches it and one that gets there reports an unexpected error (a play pool path with a character outside ASCII reaches it through `build_custom_play`, as it did before through the ASCII encode).
- **Functions.** On files, `read_x(path)` / `write_x(x, path)`; on bytes, `parse_x(bytes, path)` / `build_x(x) -> bytes`, `path` only naming the source in errors. A coaching file takes a path; a league file takes `(league, league_dir)` and builds `<league_dir>/<league>.<ext>` itself.
- **Atomic writes.** Every `write_x`, and the two config writers in `athc/config.py`, go through `athc.fileio.atomic_write(path, data)`: the bytes (or text, written as `Path.write_text` would) go to a temp file in the target's folder, flushed and fsynced, then swapped in with `os.replace`, so a reader never sees a half-written file and a failure leaves the old one as it was. The temp file is opened once with `O_EXCL` (never `tempfile`, which on Windows retries a folder that refuses new files until it has tried billions of names) and removed on any error; the error is re-raised naming the target, so a `FAIL` line names the file the user asked for; the swap is retried for about a second when a scanner holds the file (pip does the same). The helper creates no folders: the in-place commands keep refusing to create a target. The other outputs (list files, the diff output, the schedule writers) still write directly.

### Output files

- A produced file goes where the user says; by default it lands next to its source (`list-normals` writes `<name>.normals.txt` beside the gameplan, `convert-pdb` writes `<name>.xlsm` beside the PDB) or in the current directory (`generate-schedule`), never in a fixed app folder (`platformdirs` is for config, not output). `-` means stdout where a command offers it.
- An existing file at the path is replaced.
- Missing folders in the path are created in full, the way pandoc, 7-Zip and yt-dlp do it; never one level only.
- Whatever writes the file makes that call, CLI or library, so the rule holds for every caller.
- A command that edits a file in place (`set-normals`, `set-specials`, `replace-play`, `profile copy`) never creates its target; a missing path is an error.

A command that writes one file takes an optional `OUTPUT` (`convert-pdb`, `gameplan list-normals`, `gameplan list-specials`); `resolve_output` in `athc/cli/_files.py` applies the rules. Each command keeps its default name: `<name>.xlsm`, `<name>.normals.txt`, `<name>.specials.txt`.

1. Left out: the default name beside the input (`49W6.pdb` → `49W6.xlsm`, `DEN-OGP1.pln` → `DEN-OGP1.normals.txt`, `DEN-OGP1.specials.txt`).
2. `-`: the console, where the command offers it (`list-normals`, `list-specials`); a binary product (`convert-pdb`) refuses it.
3. An existing folder: the default name inside it.
4. Ends in `\` or `/` (quoted too: `"E:\My Lists\"`), or is a bare drive (`E:`): a folder, created if missing, with the default name inside it. An existing file at that path: `The directory name is invalid.`
5. Anything else: a file path. With no extension, the command's extension is added (`week6` → `week6.xlsm`, `plays` → `plays.txt`), even when a file without it exists (`out` → `out.txt`; `out` is left alone). `convert-pdb` takes only `.xlsx` or `.xlsm`.

A command that writes several files takes an optional `OUTPUT_FOLDER` (`generate-schedule`); `resolve_output_folder` applies the rules.

1. Left out: the current folder.
2. An existing folder: used as is.
3. Anything else: a folder, created if missing, whatever its name (`output.txt` too); a trailing `\` is optional, quoted or not.
4. An existing file: `The directory name is invalid.`, before any work.
5. `-`: a usage error.

### Config

- Every settings file is TOML via stdlib `tomllib`: nested tables, quoted keys with spaces, comments; `athc.toml` is written by tomlkit. `athc.toml` is `%LOCALAPPDATA%\athc\athc.toml`, resolved with `platformdirs`, or the whole dir replaced by `ATHC_CONFIG_DIR` ([Running from source](#running-from-source)); each league's `league.toml` and rule files sit in its folder. pydantic-settings, dynaconf and confuse don't fit; if load-site validation ever hurts, the upgrade is `pydantic.dataclasses.dataclass` on each `Config` class, keeping `tomllib` as the loader.
- `athc.toml` holds only app-wide tables (`[athc] league`, `[autocontinue]`, `[convert-pdb]`); a league overrides a tool's table in its own `league.toml` (below). Everything else per-league lives in one folder per league under `leagues\`, named by the folder, with fixed well-known file names nothing lists in config: `league.toml`, `gameplan.toml`, `profile.toml`, `scheduler.toml`. League data that lives in the game's own files (standings, teams) is read from those files, never copied into config.
- A tool's settings are its `[tool]` table in `athc.toml`; a league may hold the same table in its `league.toml`, and the league's keys win, key by key: a key the league sets replaces that one key, a key it leaves out comes from `athc.toml`, and a key neither file sets takes the in-code default. Key by key goes through nested tables too (`[tool.t]` in `league.toml` with only `x` keeps the base's other keys in `[tool.t]`); an array or a scalar replaces whole, never merges. Either table is optional; `[athc]` has no league override. Code: `layered_settings(section, league)` in `athc.config` returns a `Layered`, whose `source(*keys)` is the file a key came from, so every message names that file. convert-pdb is the first tool on it (`[convert-pdb]`, with `[convert-pdb.category_order]`); the rule files stay one per tool per league.
- `[league]` in `league.toml` holds the per-league values that are not files in the folder (`path`, the folder holding the league's files; `play_path`, the play pool folder; `team`, your team's name or nickname; `ppp_path`, where you keep your team's profiles and game plans — `team` and `ppp_path` are read by check-ppp, gameplan, profile and convert-pdb); values are strings or arrays of strings, relative paths resolve against the league folder.
- `[categories.offense]` / `[categories.defense]` in `league.toml` give the league's short names for the game's play categories, keyed by the game's name (`"Run Right" = "RR"`); the shipped files list every category of each side in the game's order, the unlabeled ones commented out. Rule files, play-pool folders, `replace-play` and `convert-pdb`'s category order all use these labels (game name where the league has none; the gameplan and profile `allowed_*_categories` lists take labels only); special categories have no labels. A key that is not a category of its side, an empty or repeated label, or a label equal to a category name is a `ConfigFileError`. Code: `CategoryLabels` in `athc.fbpro98_play`, carried as `LeagueConfig.categories`.
- Each tool reads its one fixed rule file from the league folder; an optional array in `league.toml` (`gameplan_rules`, `profile_rules`) replaces it with an ordered set, later files overriding earlier. No command-line option overrides the league's rules or play pool, and there is no shared default outside the league folders.
- `athc config path | edit | reveal | get | set` locate, open, reveal, read and write the settings files: `path`, `edit` and `reveal` take FILE (`athc.toml`, the default, or `league.toml`) and `--league NAME`; `get` reads `league` from `athc.toml` and `path`, `play_path`, `team`, `ppp_path` from the league's `league.toml`; `set` writes `league` to `athc.toml`, validating the league folder first, and `path`, `play_path`, `team`, `ppp_path` to the league's `league.toml`, both through tomlkit so comments survive (a missing `[athc]` table leads the file, or ends it when a key sits above the first table, so the key stays where it was), a new league key on the line after its commented example (`# team = ...`), else after `[league]`'s last key, and both written atomically through `atomic_write` ([File libraries](#file-libraries)); `edit` opens through `os.startfile`, `reveal` through `click.launch`.
- An unreadable `athc.toml` or `league.toml` (wrong value type, bad label) raises `ConfigFileError`; a missing or unknown league raises `LeagueError`.
- Each tool owns `<tool>/config.py`: a frozen `Config` dataclass with typed defaults and a `load(league)` that asks the resolved `LeagueConfig` for what the tool needs (`string(key)`, `path(key)`, `rules_file(name)` / `rule_files(key, default)`, `categories`). `athc.toml` values come back TOML-typed (`config_table(section)`); checking each type is the tool's job, and TOML's types are not interchangeable (`1` is not `true`, `"1.0"` is not a number).
- In-code defaults are authoritative: missing file, table or key means defaults; a tool errors only when a value it needs at runtime can't be resolved (`play_path` not on disk). A new tool's `[table]` runs on defaults after an upgrade, which never overwrites `athc.toml`; to customize, the user adds the table to their own (the pgcli/mycli model; deploy rules in [installer.md](../installer.md)).
- A deprecated key keeps working for 2–3 releases with a one-line `WARN` at startup naming the replacement (VS Code's `deprecationMessage` pattern), then goes.
