# TODO

## 1.0.0

- [ ] convert-pdb: add a problems section to the release docs
- [ ] athc: output, logging and errors the way pdf-converter (Tamarack Habilitations) does them; decisions and order in [pdf-converter-conventions](docs/design/TODO/pdf-converter-conventions.md); one session per subtask, in this order:
  - [ ] Python 3.13: raise the floor (pyproject, ruff, pyright, AGENTS.md, architecture.md)
  - [ ] errors: one base exception in one module; every library error subclasses it; duplicate class names gone; commands catch the base
  - [ ] console: a Console class on Rich (OK/WARN/FAIL prefixes, prefix-only color, stdout/stderr split, soft wrap, `NO_COLOR`); every command's status and failure lines go through it, `generate-schedule` and `convert-pdb` included; no `athc <command>:` prefixes
  - [ ] library warnings: libraries return warnings instead of logging them; commands print them as WARN lines; live progress (generate-schedule, autocontinue) is the one exception
  - [ ] run log: rotating file under the per-user log folder, set up once in `main()`; logging never prints to the console; the per-command `basicConfig` calls go
  - [ ] unexpected errors: caught per file and at startup; traceback to the run log; one FAIL line naming the log; the batch continues; `ATHC_DEBUG` goes
  - [ ] `python -m athc`: `__main__.py` goes through `main()`
  - [ ] config: `slots=True` on the frozen Config dataclasses
  - [ ] tests: every CLI test asserts stdout and stderr separately
  - [ ] docs: architecture.md describes the code as it is; LOGGING-IS-FUCKED.md, pdf-converter-conventions.md and the older logging/error-handling TODO lines retired
- [ ] athc: Logging: fix the deviations from the design — `generate-schedule` and `convert-pdb` print nothing to stdout, 15 per-command `basicConfig` calls; see [LOGGING-IS-FUCKED](docs/design/TODO/LOGGING-IS-FUCKED.md)
- [ ] gameplan: `replace-play` takes a list of play/replacement pairs to swap in one run
- [ ] convert-pdb: complete integration into athc
- [ ] convert-pdb: clear sort instructions on Options page
- [ ] convert-pdb: remove hidden setting `include_category_worksheets = false` from athc.ini
- [ ] convert-pdb: 2-DL or R&S?
- [ ] profile: copy: copy PATs
- [x] playpool: convert from `check-playpool` to `playpool check`
- [ ] athc: fix toml reading so handles UTF-8 BOM in file properly
- [ ] athc: rename path parameters to the `<something>_dir` convention (`play_path`, `league_path`, ...)
- [ ] athc: CLI: confirm mainstream CLI strategy (see Tamarack Habilitations)
- [ ] athc: Logging: switch to the mainstream logging strategy w/ color (see Tamarack Habilitations)
- [ ] athc: Error handling and exit codes (see Tamarack Habilitations)
- [ ] athc: clear usage and help text for all commands
- [ ] athc: STATUS.md, WORKLOG.md, CHANGELOG.md: clean and clear
- [ ] athc: Release Docs:
  - [ ] clear user documentation
  - [ ] list of commands
  - [ ] explain each command's messages in the release docs ([command-messages](docs/design/TODO/command-messages.md))
- [x] build a PyInstaller-built installer (exe); replacing the `install.bat` + wheel zip and uv prereq; design in [installer](docs/design/installer.md)
  - [ ] exclude autocontinue
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
- athc: cli: wire logging in the `cli()` group callback — `RichHandler` on stderr, `click.style` on stdout; drop the 15 per-command `basicConfig` calls. Design: [docs/design/architecture.md](docs/design/architecture.md#output-streams)
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
