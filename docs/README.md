# Docs

`release.md` and `installer.md`, then one folder per kind of doc, flat inside, the file name the subject; the rules: [design/architecture.md](design/architecture.md#docs).

- [installer.md](installer.md) — the setup.exe: build, config deploy and upgrade rules
- [release.md](release.md) — versioning and the release flow

## Usage

The end-user docs the installer ships, plain text, one file per command.

- [README.txt](usage/README.txt) — install, first-time setup, the settings folder, exit codes, troubleshooting
- [autocontinue.txt](usage/autocontinue.txt) — `athc autocontinue`
- [check-ppp.txt](usage/check-ppp.txt) — `athc check-ppp`
- [config.txt](usage/config.txt) — `athc config`
- [convert-pdb.txt](usage/convert-pdb.txt) — `athc convert-pdb`
- [gameplan.txt](usage/gameplan.txt) — `athc gameplan`, every subcommand
- [generate-schedule.txt](usage/generate-schedule.txt) — `athc generate-schedule`, for the Commissioner
- [playpool.txt](usage/playpool.txt) — `athc playpool check`
- [profile.txt](usage/profile.txt) — `athc profile`, every subcommand
- [standings.txt](usage/standings.txt) — `athc standings`
- [USAGE_ORIGINAL.txt](usage/USAGE_ORIGINAL.txt) — each command's help as it was before 1.0

## Design

- [architecture.md](design/architecture.md) — how athc is built, and the conventions every command and library follows
- [reference-projects.md](design/reference-projects.md) — the projects athc models itself on
- [testing-integration.md](design/testing-integration.md) — the integration test tier: a command end to end
- [testing-unit.md](design/testing-unit.md) — the unit test tier: components in isolation

Tools:

- [autocontinue.md](design/autocontinue.md) — `athc autocontinue`: clicks the game's Continue button
- [check_ppp.md](design/check_ppp.md) — `athc check-ppp`: profiles checked with their game plans
- [config.md](design/config.md) — `athc config`: the settings files
- [gameplan.md](design/gameplan.md) — `athc gameplan`: check and edit game plans
- [pdbtoexcel.md](design/pdbtoexcel.md) — `athc convert-pdb`: a WinLogStats database to an Excel workbook
- [playpool.md](design/playpool.md) — the play pool library and `athc playpool check`
- [profile.md](design/profile.md) — `athc profile`: check, compare and copy profiles
- [scheduler.md](design/scheduler.md) — `athc generate-schedule`: a season schedule with OR-Tools
- [scheduler-phase-1-matchups.md](design/scheduler-phase-1-matchups.md) — phase 1: the matchup inventory
- [scheduler-phase-2-schedule.md](design/scheduler-phase-2-schedule.md) — phase 2: placing the matchups into weeks
- [standings.md](design/standings.md) — `athc standings`: the league's standings as played so far

Libraries:

- [fbpro98_gameplan.md](design/fbpro98_gameplan.md) — `.pln` game plans, read and write
- [fbpro98_lg2.md](design/fbpro98_lg2.md) — `.lg2`: each team's profile and game plan files
- [fbpro98_lge.md](design/fbpro98_lge.md) — `.lge`: conferences, divisions, teams, rosters, standings and games
- [fbpro98_play.md](design/fbpro98_play.md) — `.ply` plays
- [fbpro98_profile.md](design/fbpro98_profile.md) — `.prf` coaching profiles, read and write
- [fbpro98_pyr.md](design/fbpro98_pyr.md) — `.pyr`: every player by id, with position, ratings and injury
- [fbpro98_standings.md](design/fbpro98_standings.md) — standings by the game's, the scheduler's or the NFL's tie-breakers
- [fbpro98_stats.md](design/fbpro98_stats.md) — `.dat`: player and team stats, and the honors

Pending designs and plans, in `design/TODO/`; a finished pair folds into the docs and goes (the rule in AGENTS.md).

- [game-stats-correction.md](design/TODO/game-stats-correction.md) — Proposal — game stats correction
- [logging-updates.md](design/TODO/logging-updates.md) — Proposal — logging updates
- [quirk-budget.md](design/TODO/quirk-budget.md) — Proposal — schedule quirk budget
- [standings-net-touchdowns.md](design/TODO/standings-net-touchdowns.md) — Proposal — net touchdowns in the standings

## Formats

[formats/README.md](formats/README.md) says what each game file holds; each spec sits beside its ImHex and Hex Workshop patterns.

- [cities.md](formats/cities.md) — `CITIES.DAT`, the game's city table
- [lg2.md](formats/lg2.md) — `.lg2`, each team's profile and game plan files
- [lge.md](formats/lge.md) — `.lge`, the league file
- [pdb.md](formats/pdb.md) — `.pdb`, the WinLogStats database
- [pln.md](formats/pln.md) — `.pln`, a game plan
- [ply.md](formats/ply.md) — `.ply`, a play
- [prf.md](formats/prf.md) — `.prf`, a coaching profile
- [pyr.md](formats/pyr.md) — `.pyr`, the players
- [schedule-import.md](formats/schedule-import.md) — the schedule-import text format, with an example
- [stats.md](formats/stats.md) — `.dat` and `.idx`, the statistics

## Research

- [cpsat-rule-patterns.md](research/cpsat-rule-patterns.md) — CP-SAT rule design patterns
- [fbpro98-game-behavior.md](research/fbpro98-game-behavior.md) — how the game behaves: injuries, standings, tie-breakers, the stats files
- [nfl-formula.md](research/nfl-formula.md) — the NFL's own scheduling formula
- [nfl-schedules.md](research/nfl-schedules.md) — NFL schedule patterns behind the phase-2 rules
- [pnfl-formats.md](research/pnfl-formats.md) — decoding the PNFL's league files
- [pnfl-history.md](research/pnfl-history.md) — the PNFL's relocations and division changes, season by season
- [sierra-source.md](research/sierra-source.md) — what Sierra's FbPro98 source shows: ratings, files, computer teams
- [standings-tie-breakers.md](research/standings-tie-breakers.md) — the game's, the NFL's, pnfl.biz's and the scheduler's tie-breakers side by side
