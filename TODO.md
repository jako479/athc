# TODO

## 1.0.0

- [ ] gameplan: `list-normals --sort category` — group the plays by category
- [ ] gameplan: `replace-play` takes a list of play/replacement pairs to swap in one run
- [ ] convert-pdb: complete integration into athc
- [ ] convert-pdb: clear sort instructions on Options page
- [ ] convert-pdb: remove hidden setting `include_category_worksheets = false` from athc.ini
- [ ] profile: copy: copy PATs
- [ ] playpool: convert from `check-playpool` to `playpool check`
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
- [ ] build a PyInstaller-built installer (exe); replacing the `install.bat` + wheel zip and uv prereq
- [ ] RELEASE!!!
  - [ ] upload installer to Google Drive
  - [ ] post in forum
  - [ ] send email

## 2.0.0

- convert-pdb: Total Stats filtering (from pnfl's TODO): remove filtering via script? add filtering to config? convert to a table for filtering (greater-than, less-than)?
- gameplan-check: rule for excluded files [ME ONLY?]
- playpool-check: check that each play's name matches its play category
- playpool-check: count plays by file name type
- athc: cli: wire logging in the `cli()` group callback — `RichHandler` on stderr, `click.style` on stdout; drop the 15 per-command `basicConfig` calls. Design: [docs/design/logging.md](docs/design/logging.md)
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
- generate-schedule: quirk budget — allow a few rare NFL-style one-offs per season; see [docs/design/quirk-budget.md](docs/design/quirk-budget.md). Do the ruleset simplification first
