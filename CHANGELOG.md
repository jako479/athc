# Changelog

## athc

- docs: added STATUS.md — per-tool state, what is done, what is next
- docs: TODO modifications
- tests: golden integration test for `generate-schedule` — three output files compared byte for byte
- build: dropped the Python prerequisite; uv downloads a managed Python
- build: the dev config dir (`dev/`) is tracked in git
- docs: scheduler strength-of-schedule analysis scripts and real-season reports; dropped the testing research notes
- build: moved the release docs into `release/docs/`; installer and build script updates
- config: paths in config files resolve against the config dir
- cli: unexpected errors print one line instead of a traceback; `ATHC_DEBUG=1` re-raises
- build: all dependencies are required — no optional extras
- config: added the `config` command — `path`, `edit`, `reveal`
- docs: README and ARCHITECTURE per tool, file format specs, design notes on logging and testing
- tests: added the unit and integration test tiers
- build: added the PNFL rules files and the scheduler command docs to the release bundle
- build: removed the Hello World proof of concept
- build: initial commit — build and install pipeline, Hello World proof of concept

## autocontinue

- hot-corner toggle, focus checks, halftime images
- added the `autocontinue` command

## fbpro98_gameplan

- updated for the `PlayRef` rename
- added the `.pln` game plan reader and writer

## fbpro98_play

- renamed the `Play` family to `PlayRef`/`CustomPlay`/`StockPlay`
- added the `.ply` play file reader

## fbpro98_profile

- added the `.prf` profile reader and writer

## gameplan

- added the `find-play` and `replace-play` commands
- added the `gameplan` command — `check`, `list-normals`, `list-specials`, `set-normals`, `set-specials`, `find-play`

## pdbtoexcel

- rules paths resolve against the config dir; cleanup
- added the `convert-pdb` command, backed by the pdbtoexcel package

## playpool

- renamed the `PlayRecord` family to `Play`; play attributes come from the pool's folder categories
- added the play pool package

## profile

- expanded `check`'s gameplan compatibility checks and validators
- added the `profile` command — `check`, `copy`, `diff`

## scheduler

- corrected the phase-2 solver worker count in the design doc
- removed references to the dropped A, B, C and D schedulers from the league.ini files and release docs
- league.ini `[Standings]` renamed to `[OverallStandings]`
- added the `five_team_max_divisional_first_5` rule
- league.ini dropped the redundant `[Divisions]` section; `[DivisionStandings]` now lists each division's teams
- report moves the Conf Rank column after the non-conference columns
- added `solver_workers` to the solver config — phase-2 parallel search width, fixed at 8 so seeds reproduce
- phase 2 runs multithreaded
- renamed "scheduler C" to just the scheduler
- removed scheduler D
- NFL-derived divisional spread rules for 4- and 5-team divisions
- NFL-derived rule overhaul — hard rules, league-wide anti-pileup caps, soft objective with NFL-typical bands
- tidied CLI output
- report lists the Team column first
- phase 1 no longer forced to take the first set of matchups it finds
- status message improvements
- default `c_spread` raised from 1.5 to 1.8; status messaging improved
- removed schedulers A and B; added status messages
- added schedulers C and D; difficulty tuning; 2049 league data
- added the `generate-schedule` command and the scheduler package
