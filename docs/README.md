# Docs

Docs for repo readers; the end-user docs are in `config/release/docs/`. One folder per kind of doc, flat inside, the file name the subject; the rules: [architecture.md](architecture.md#docs).

## Project

- [architecture.md](architecture.md) — how athc is built, and the conventions every command and library follows
- [fbpro98-game-behavior.md](fbpro98-game-behavior.md) — how the game behaves: injuries, standings, tie-breakers
- [installer.md](installer.md) — the setup.exe: build, config deploy and upgrade rules
- [pnfl-history.md](pnfl-history.md) — the PNFL's relocations and division changes, season by season
- [reference-projects.md](reference-projects.md) — the projects athc models itself on
- [release.md](release.md) — versioning and the release flow
- [testing-integration.md](testing-integration.md) — the integration test tier: a command end to end
- [testing-unit.md](testing-unit.md) — the unit test tier: components in isolation

## Tools

- [autocontinue.md](autocontinue.md) — `athc autocontinue`: clicks the game's Continue button
- [check_ppp.md](check_ppp.md) — `athc check-ppp`: profiles checked with their game plans
- [config.md](config.md) — `athc config`: the settings files
- [gameplan.md](gameplan.md) — `athc gameplan`: check and edit game plans
- [pdbtoexcel.md](pdbtoexcel.md) — `athc convert-pdb`: a WinLogStats database to an Excel workbook
- [playpool.md](playpool.md) — the play pool library and `athc playpool check`
- [profile.md](profile.md) — `athc profile`: check, compare and copy profiles
- [scheduler.md](scheduler.md) — `athc generate-schedule`: a season schedule with OR-Tools
- [scheduler-phase-1-matchups.md](scheduler-phase-1-matchups.md) — phase 1: the matchup inventory
- [scheduler-phase-2-schedule.md](scheduler-phase-2-schedule.md) — phase 2: placing the matchups into weeks
- [standings.md](standings.md) — `athc standings`: the league's standings as played so far

## Libraries

- [fbpro98_gameplan.md](fbpro98_gameplan.md) — `.pln` game plans, read and write
- [fbpro98_lg2.md](fbpro98_lg2.md) — `.lg2`: each team's profile and game plan files
- [fbpro98_lge.md](fbpro98_lge.md) — `.lge`: conferences, divisions, teams, standings and games
- [fbpro98_play.md](fbpro98_play.md) — `.ply` plays
- [fbpro98_profile.md](fbpro98_profile.md) — `.prf` coaching profiles, read and write
- [fbpro98_standings.md](fbpro98_standings.md) — standings by the game's, the scheduler's or the NFL's tie-breakers
- [fbpro98_stats.md](fbpro98_stats.md) — `.dat`: player and team stats, and the honors

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
- [nfl-formula.md](research/nfl-formula.md) — the NFL's own scheduling formula
- [nfl-schedules.md](research/nfl-schedules.md) — NFL schedule patterns behind the phase-2 rules
- [pnfl-formats.md](research/pnfl-formats.md) — decoding the PNFL's league files
- [sierra-source.md](research/sierra-source.md) — what Sierra's FbPro98 source shows: ratings, files, computer teams
- [standings-tie-breakers.md](research/standings-tie-breakers.md) — the game's, the NFL's, pnfl.biz's and the scheduler's tie-breakers side by side

## Proposals

Pending designs and plans; a finished pair folds into the docs and goes (the rule in AGENTS.md).

- [logging-updates.md](proposals/logging-updates.md) — Proposal — logging updates
- [quirk-budget.md](proposals/quirk-budget.md) — Proposal — schedule quirk budget
- [stat-corrections.md](proposals/stat-corrections.md) — Proposal — stat corrections
