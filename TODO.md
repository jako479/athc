# TODO

## 1.0.0

- [ ] profile: CLI plan (the four names `off1 def1 off2 def2` on check, diff and copy, `--team`, `copy SOURCE TARGET...`, `--substitutions`); see [docs/design/TODO/profile-cli.md](docs/design/TODO/profile-cli.md)
- [ ] playpool: CLI plan (`check [FOLDER]` with `pass the folder` hints; new `show PLAY...` for a play's side, category, attributes and file; new `list [CATEGORY]...` listing a category's plays with their attributes as a play list); see [docs/design/TODO/playpool-cli.md](docs/design/TODO/playpool-cli.md)
- [ ] generate-schedule: CLI plan (`--previous` and `--upcoming` folder rules, the same-folder warning, the No path hint, seed and time-limit bounds, writable-folder check before the solve, Ctrl+C handling); see [docs/design/TODO/generate-schedule-cli.md](docs/design/TODO/generate-schedule-cli.md)
- [ ] gameplan: CLI plan (the four names, `--team`, `--path` on find-play, replace-play and set-specials with the team's game plans as default, `-q` dropped, cap lines name the plays); see [docs/design/TODO/gameplan-cli.md](docs/design/TODO/gameplan-cli.md)
- [ ] convert-pdb: CLI plan (optional `OUTPUT_FILE` beside the PDB, Slot columns from the team's game plans with per-slot `-o/-o2/-d/-d2` and `--path FOLDER`, `--team`, `--percentages/--no-percentages`); see [docs/design/TODO/convert-pdb-cli.md](docs/design/TODO/convert-pdb-cli.md)
- [ ] config: CLI plan (`get KEY` for athc.ini and league.toml keys; `path`, `edit` and `reveal` take FILE `athc.ini` or `league.toml` with `--league`; `edit` via `os.startfile`); see [docs/design/TODO/config-cli.md](docs/design/TODO/config-cli.md)
- [ ] autocontinue: CLI plan (every setting optional with shipped defaults, `--delay`, `-n/--dry-run`, hot corner checked every pass, window lines, clicks on the button's point); see [docs/design/TODO/autocontinue-cli.md](docs/design/TODO/autocontinue-cli.md)
- [ ] check-ppp: team and league modes (`team` and `ppp_path` in league.toml, `--team`, `--all-teams`); `gameplan check` and `profile check` stay; see [docs/design/TODO/check-ppp-cli.md](docs/design/TODO/check-ppp-cli.md)
- [ ] athc: reorganize the docs folders and set the rule for design docs and plans; see [docs/design/TODO/docs-layout.md](docs/design/TODO/docs-layout.md)
- [ ] athc: go through the CLI and help text for each command; see [docs/design/TODO/cli-help.md](docs/design/TODO/cli-help.md)
- [ ] athc: go through all messages, warnings and errors for each command — messages name the file and line number, then say the problem in plain words; see [docs/design/TODO/logging-updates.md](docs/design/TODO/logging-updates.md)
- [ ] athc: look for gaps in test cases for each command and library
- [ ] athc: update the release README with each command's warnings and errors, from the per-tool READMEs ([gameplan](docs/gameplan/README.md), [profile](docs/profile/README.md), [check-ppp](docs/check_ppp/README.md), [playpool](docs/playpool/README.md), [convert-pdb](docs/pdbtoexcel/README.md), [generate-schedule](docs/scheduler/README.md), [autocontinue](docs/autocontinue/README.md), [config](docs/config/README.md))
- [ ] athc: convert the release notes from .txt to .md
- [ ] athc: update the release docs to Markdown
- [ ] athc: recommend Markdown plugins for Chrome or Notepad++ in the release README
- [ ] athc: create a fancy project README for GitHub
- [ ] athc: go through and clean up the project README, TODO, STATUS, CHANGELOG and WORKLOG
- [ ] athc: go through and reorganize the flood of design docs
- [ ] athc: go through and reorganize the flood of file specs
- [ ] athc: go through and update the release documentation (README, CHANGELOG, commands and errors/warnings, etc.)
- [ ] gameplan: set-normals: decide whether to keep `-q/--quiet`, the only quiet option in athc: drop it, keep it, or give every file-writing command one; pdf-converter has none
- [ ] gameplan: `replace-play` takes a list of play/replacement pairs to swap in one run
- [ ] check-ppp: league plan and profile names
- [ ] convert-pdb: add a problems section to the release docs
- [ ] convert-pdb: add clear sort instructions on Options page
- [ ] convert-pdb: remove hidden setting `include_category_worksheets = false` from athc.ini
- [ ] athc: rename path parameters to the `<something>_dir` convention (`play_path`, `league_path`, ...)
- [ ] install: exclude autocontinue; design in [installer](docs/design/installer.md)
- [ ] RELEASE!!!
  - [ ] upload installer to Google Drive
  - [ ] post in forum
  - [ ] send email

## 2.0.0

- athc: list the players who show P-1 but will still be injured for the next game after weekly healing; chart in [game behavior](docs/design/fbpro98-game-behavior.md#p-1-that-stays-injured)
- convert-pdb: Total Stats filtering (from pnfl's TODO): remove filtering via script? add filtering to config? convert to a table for filtering (greater-than, less-than)?
- gameplan-check: rule for excluded files [ME ONLY?]
- playpool-check: check that each play's name matches its play category
- playpool-check: count plays by file name type
- libraries: game-specific library under gameplan, profile, play, etc. with common categories??
- athc: tests: add ruff's `PT` rule group (pytest style); 117 findings today, 111 auto-fixable under `--unsafe-fixes`
- autocontinue: work with Dean to determine usability requirements
- autocontinue: add halftime
- gameplan: replace play (single and bulk) - list of plays as input??
- profile: revisit edit\copy options
- generate-schedule: generate schedules for PCFL
- generate-schedule: review and simplify the ruleset — 50 `[phase2]` keys, some redundant; consider simple vs. full ruleset switch. Reasoning and plan in [STATUS.md](STATUS.md)
- generate-schedule: quirk budget — allow a few rare NFL-style one-offs per season; see [docs/design/TODO/quirk-budget.md](docs/design/TODO/quirk-budget.md). Do the ruleset simplification first
