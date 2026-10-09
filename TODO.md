# TODO

## 1.0.0

- [ ] gameplan: set-normals: decide whether to keep `-q/--quiet`, the only quiet option in athc: drop it, keep it, or give every file-writing command one; pdf-converter has none
- [ ]
- [ ] convert-pdb: add a problems section to the release docs
- [ ] gameplan: `replace-play` takes a list of play/replacement pairs to swap in one run
- [ ] convert-pdb: add clear sort instructions on Options page
- [ ] convert-pdb: remove hidden setting `include_category_worksheets = false` from athc.ini
- [x] convert-pdb: complete integration into athc
- [x] profile: copy: copy PATs
- [x] playpool: convert from `check-playpool` to `playpool check`
- [x] athc: fix toml reading so handles UTF-8 BOM in file properly
- [ ] athc: rename path parameters to the `<something>_dir` convention (`play_path`, `league_path`, ...)
- [ ] athc: clear usage and help text for all commands
- [ ] athc: STATUS.md, WORKLOG.md, CHANGELOG.md: clean and clear
- [x] athc: console, run log, errors and exit codes the pdf-converter way; rules in [architecture](docs/design/architecture.md#console-run-log-and-errors), each command's lines in its tool README; one session per subtask, in this order:
  - [x] Python 3.13: raise the floor (pyproject, ruff, pyright, AGENTS.md, architecture.md)
  - [x] errors: `athc/errors.py` with the base `AthcError` and the shared `ConfigFileError`, `LeagueError`, `RulesFileError`; every library error subclasses it; duplicate class names and the two `ConfigError`s gone; readers wrap model `ValueError`s; `load_config` wraps `configparser` errors
  - [x] console: `athc/console.py` on Rich (print / ok / skip / result / progress / warn / fail / unexpected; prefix-only color; stdout/stderr split; soft wrap; `NO_COLOR`); every command's lines go through it, `generate-schedule` and `convert-pdb` included; no `athc <command>:` prefixes; `click.echo` gone
  - [x] run log: `athc/log.py`, rotating `athc.log` under the per-user log folder, set up once in `main()`; the console writes each log line itself; the 15 per-command `basicConfig` calls go
  - [x] main(): `cli(standalone_mode=False)`; one place turns usage errors, `AthcError`, `OSError`, Ctrl-C and bugs into the line, the log entry and the exit code; `ATHC_DEBUG` goes; `__main__.py` goes through it
  - [x] exit codes: 0 / 1 findings / 2 error in every command; a per-item catch keeps a batch going and the worst outcome wins; Ctrl-C 130; a directory with no files warns and exits 0
  - [x] library warnings and progress: libraries return warnings and findings as values and take a `progress` callback (`warn` too for autocontinue); no library logs or prints
  - [x] config: `slots=True` on the frozen Config dataclasses
  - [x] tests: every CLI test asserts stdout and stderr separately; console color, `NO_COLOR` and log-file tests
  - [x] docs: architecture.md describes the code as it is; per-tool READMEs carry their lines and codes; logging.md, logging-by-command.md and the older logging/error-handling TODO lines retired; athc-admin follow-on TODO added
- [x] build a PyInstaller-built installer (exe); replacing the `install.bat` + wheel zip and uv prereq; design in [installer](docs/design/installer.md)
  - [ ] exclude autocontinue
- [ ] athc: Release Docs:
  - [ ] clear user documentation
  - [ ] list of commands
  - [ ] explain each command's messages in the release docs, from the per-tool READMEs ([gameplan](docs/gameplan/README.md), [profile](docs/profile/README.md), [check-ppp](docs/check_ppp/README.md), [playpool](docs/playpool/README.md), [convert-pdb](docs/pdbtoexcel/README.md), [generate-schedule](docs/scheduler/README.md), [autocontinue](docs/autocontinue/README.md), [config](docs/config/README.md))
- [ ] RELEASE!!!
  - [ ] upload installer to Google Drive
  - [ ] post in forum
  - [ ] send email

## 2.0.0

- convert-pdb: Total Stats filtering (from pnfl's TODO): remove filtering via script? add filtering to config? convert to a table for filtering (greater-than, less-than)?
- gameplan-check: rule for excluded files [ME ONLY?]
- playpool-check: check that each play's name matches its play category
- playpool-check: count plays by file name type
- libraries: game-specific library under gameplan, profile, play, etc. with common categories??
- athc: tests: add ruff's `PT` rule group (pytest style); 117 findings today, 111 auto-fixable under `--unsafe-fixes`
- autocontinue: work with Dean to determine usability requirements
- autocontinue: add halftime
- gameplan: evaluate whether wildcard paths through `collect_files` were added on purpose, per command
  - check
  - set-specials
  - replace-play
- gameplan: drop wildcard paths — they are expanded before the command sees them, which breaks `find-play`
- gameplan: replace play (single and bulk) - list of plays as input??
- profile: check for wildcard path support
  - check
  - copy
- profile: revisit edit\copy options
- generate-schedule: generate schedules for PCFL
- generate-schedule: review and simplify the ruleset — 50 `[phase2]` keys, some redundant; consider simple vs. full ruleset switch. Reasoning and plan in [STATUS.md](STATUS.md)
- generate-schedule: quirk budget — allow a few rare NFL-style one-offs per season; see [docs/design/TODO/quirk-budget.md](docs/design/TODO/quirk-budget.md). Do the ruleset simplification first
