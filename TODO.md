# TODO

## 1.0.0

- [x] profile: `copy` errors when the source and the single target are the same file (non-bulk copy)
- [x] athc: an output folder for convert-pdb, list-normals, list-specials and generate-schedule
- [x] profile: CLI plan (profile keys `off1 def1 off2 def2` on check, diff and copy, `--team`, `copy SOURCE TARGET...`, `--substitutions`)
- [x] playpool: CLI plan (`check [FOLDER]`, `athc config set play_path` in its not-set lines)
- [x] generate-schedule: CLI plan (`--previous FILE` optional and `--upcoming FILE`, an unfinished season warns, coin-toss and division-finish tiebreaks, seed and time-limit bounds, Ctrl+C handling)
- [x] gameplan: CLI plan (game plan keys `off1 def1 off2 def2`, `--team`, `--path` on find-play, replace-play and set-specials with the team's game plans as default, `-q` dropped)
- [x] convert-pdb: CLI plan (optional `OUTPUT_FILE` beside the PDB, Slot columns from the team's game plans or from `-o/-o2/-d/-d2` instead, `--path FOLDER`, `--team`, `--percentages/--no-percentages`)
- [x] config: CLI plan (`get KEY` for athc.ini and league.toml keys; `set` also writes `path`, `play_path`, `team` and `ppp_path`; `path`, `edit` and `reveal` take FILE `athc.ini` or `league.toml` with `--league`; `edit` via `os.startfile`)
- [x] check-ppp: team and league modes (`team` and `ppp_path` in league.toml, `--team`, `--all-teams`); `gameplan check` and `profile check` stay
- [x] athc: reorganize the docs folders and set the rule for design docs and plans
- [x] athc: go through the CLI and help text for each command
- [ ] athc: go through all messages, warnings and errors for each command — messages name the file and line number, then say the problem in plain words; see [docs/proposals/logging-updates.md](docs/proposals/logging-updates.md)
- [ ] athc: look for gaps in test cases for each command and library
- [ ] athc: update the release README with each command's warnings and errors, from the per-tool docs ([gameplan](docs/gameplan.md), [profile](docs/profile.md), [check-ppp](docs/check_ppp.md), [playpool](docs/playpool.md), [convert-pdb](docs/pdbtoexcel.md), [generate-schedule](docs/scheduler.md), [autocontinue](docs/autocontinue.md), [config](docs/config.md))
- [ ] athc: convert the release notes from .txt to .md
- [ ] athc: update the release docs to Markdown
- [ ] athc: recommend Markdown plugins for Chrome or Notepad++ in the release README
- [ ] athc: create a fancy project README for GitHub
- [ ] athc: go through and clean up the project README, TODO, STATUS, CHANGELOG and WORKLOG
- [ ] athc: go through and reorganize the flood of design docs
- [ ] athc: go through and reorganize the flood of file specs
- [ ] athc: go through and update the release documentation (README, CHANGELOG, commands and errors/warnings, etc.)
- [x] gameplan: set-normals: decide whether to keep `-q/--quiet`, the only quiet option in athc: drop it, keep it, or give every file-writing command one; pdf-converter has none
- [ ] gameplan: `replace-play` takes a list of play/replacement pairs to swap in one run, through an option that reads a file (`-` for the console), which makes both positionals optional
- [ ] check-ppp: league plan and profile names
- [ ] convert-pdb: add a problems section to the release docs
- [ ] convert-pdb: add clear sort instructions on Options page
- [x] convert-pdb: remove hidden setting `include_category_worksheets = false` from athc.ini
- [ ] athc: rename path parameters to the `<something>_dir` convention (`play_path`, `league_path`, ...)
- [ ] install: exclude autocontinue; design in [installer](docs/installer.md)
- [ ] RELEASE!!!
  - [ ] upload installer to Google Drive
  - [ ] post in forum
  - [ ] send email

## 2.0.0

- athc: stat corrections — fix stats the game records wrong in `<league>.dat`; see [docs/proposals/stat-corrections.md](docs/proposals/stat-corrections.md)
- gameplan: set-normals checks the resulting game plan and, if it fails, asks for confirmation before replacing
- athc: update the file specs and their ImHex patterns from the Sierra source findings; see [docs/research/sierra-source.md](docs/research/sierra-source.md#14-planned-spec-changes)
- athc: document the game behaviors and fix comments and code from the Sierra source findings and the updated specs; see [docs/research/sierra-source.md](docs/research/sierra-source.md#15-other-planned-changes)
- [x] autocontinue: full test set (real screens with the pointer off, on and lit; a test per setting; a pointer helper in the sandbox game; a test matrix)
- athc: tests: remove the help description length test (`test_description_fits_the_range`)
- view-standings: provide the official NFL tie-breaking rules (needs total TDs, etc.)
- view-standings: add a playoff race setting that describes what needs to happen for a team to make the playoffs
- [x] autocontinue: CLI plan and improvements (every setting optional with shipped defaults, `--delay`, `-n/--dry-run`, window lines, click on the button)
- playpool: add a `playpool find-play` command
- playpool: add a `playpool show` command
- athc: list the players who show P-1 but will still be injured for the next game after weekly healing; chart in [game behavior](docs/fbpro98-game-behavior.md#p-1-that-stays-injured)
- convert-pdb: Total Stats filtering (from pnfl's TODO): remove filtering via script? add filtering to config? convert to a table for filtering (greater-than, less-than)?
- gameplan-check: rule for excluded files [ME ONLY?]
- playpool-check: check that each play's name matches its play category
- playpool-check: count plays by file name type
- libraries: game-specific library under gameplan, profile, play, etc. with common categories??
- athc: tests: add ruff's `PT` rule group (pytest style); 117 findings today, 111 auto-fixable under `--unsafe-fixes`
- autocontinue: work with Dean to determine usability requirements
- [x] autocontinue: add halftime and end of game
- gameplan: replace play (single and bulk) - list of plays as input??
- profile: revisit edit\copy options
- generate-schedule: generate schedules for PCFL
- generate-schedule: review and simplify the ruleset — 50 `[phase2]` keys, some redundant; consider simple vs. full ruleset switch. Reasoning and plan in [STATUS.md](STATUS.md)
- generate-schedule: quirk budget — allow a few rare NFL-style one-offs per season; see [docs/proposals/quirk-budget.md](docs/proposals/quirk-budget.md). Do the ruleset simplification first
