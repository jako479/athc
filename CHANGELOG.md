# Changelog

Very high-level, release-note style: what is new or changed, one line per
feature or change, nothing technical. A finished TODO item moves here as its
own line, stripped of the detail that only explained the work; any other
high-level change completed alongside it gets its own line.

## athc

- config: `league.toml`, the TOML rule files and `scheduler.toml` may start with a UTF-8 byte-order mark (Notepad, Excel); it is skipped
- playpool: `check` on a given folder still uses the configured league's category names for its folders; with no league, folder names are not checked
- config: league settings moved from `league.ini` to `league.toml`; a league's short names for the play categories live there under `[categories.offense]` / `[categories.defense]`, no longer in code
- playpool: `check-playpool` became `playpool check`, a command group like `gameplan` and `profile`
- profile: `copy --pat-logic` copies the PAT play-calling table into the targets
- athc: the file specs hold only the file layout, its validity rules and open questions; each library's README documents its API, indexed in the architecture overview
- athc: the file specs name fields in prose and keep code font for what is stored in the file
- fbpro98_play: the `.ply` spec explains the category bytes bit by bit, the shared bits 7–6, and shows sample plays
- gameplan: the `.pln` spec no longer defines category values; a plan's bytes are a copy of the play file's
- gameplan: `check` and `find-play` work on the current folder when no path is given
- profile: `check` works on the current folder when no path is given
- config: a league's rule files sit next to its league.ini; the rules\ subfolder is gone
- gameplan: rules can name every play category, game-name labels like `[offense."Pass Long Left"]` and `"Run Clock"` / `"Stop Clock"` as required specials; a `.pln` with an unrecognized play category is rejected as corrupt
- convert-pdb: the `.pdb` file spec and the master VBA workbooks came over from pnfl
- tests: golden workbook test for `convert-pdb` — the real `.pdb` against the curated pool, every cell compared
- check-ppp: `require_all_gameplan_categories_in_profile` moved from the profile rules to the gameplan rules' `[profile_compatibility]` section
- profile: `check` dropped `--gameplan`; `check-ppp` checks a profile with its gameplan
- check-ppp: checks every profile and gameplan pair the league's `.lg2` names in a folder, or a whole tree with `-r`
- check-ppp: needs both a profile and a gameplan; one file alone is an error
- athc: new `path` league setting, the folder that holds the league's files
- fbpro98_lg2: reading a league's `.lg2` takes the league name and its folder; the library adds the extension
- athc: the `dev\` and `release\` config folders moved under `config\`
- check-ppp: follows the league's profile-vs-gameplan settings, renamed `require_all_profile_categories_in_gameplan` (on) and `require_all_gameplan_categories_in_profile` (off)
- athc: PCFL ships gameplan, playpool and profile rules (same as the PNFL's)
- athc: usage lines list each option (`[-h] [--sort slot|name] gameplan [output_file]`) instead of `[OPTIONS]`
- profile: `diff` help shows `file1 file2` and `-o file`
- profile: `copy` takes `source target`, dropped `--no-backup` and makes no backups
- profile: `check` dropped `--rules`; help shows `path...` and `--gameplan pln_file`
- scheduler: `generate-schedule` help shows `--season year`, `--seed number`, `--time-limit number`
- gameplan: `set-specials` takes `path input_file` (`-` reads the console); dropped `--stdin`, `--play-path`, `--playpool-rules` and `--no-backup`, and makes no backups
- gameplan: `set-normals` takes `gameplan input_file` (`-` reads the console); dropped `--stdin`, `--play-path`, `--playpool-rules` and `--no-backup`
- gameplan: `set-normals` and `replace-play` no longer make backups; `--no-backup` is gone from both
- gameplan: `replace-play` dropped `--play-path` (the pool comes from the league); help shows `play replacement path`
- gameplan: `find-play` exits like grep — 0 when any play is found, 1 when none are
- gameplan: `find-play` help shows `play... path` in lowercase
- gameplan: `list-specials` takes the output file (or `-`) as an optional second argument; `--output` is gone
- gameplan: `list-normals` takes the output file (or `-`) as an optional second argument again; `--output` is gone
- gameplan: `list-specials` matches `list-normals`: writes `<name>.specials.txt` by default, `--output file` or `--output -`, no `-f`
- athc: `-h` works on every command; help shows argument and value names in lowercase (`gameplan`, `--league name`)
- gameplan: `list-normals` takes `--output file` instead of a second argument; `--output -` prints
- gameplan: `list-normals` writes `<name>.normals.txt` next to the `.pln` by default and replaces it; `-` prints instead; `-f` is gone
- gameplan: `check` dropped `--play-path`, `--playpool-rules` and `--rules`; everything comes from the league folder
- convert-pdb: dropped `--play-path`, `--playpool-rules` and `--skip-totals`; the Total Stats team is always written and `calculate_total_stats` is no longer a setting
- config: `athc config edit` always opens athc.ini in its default app; `$VISUAL`/`$EDITOR` are no longer read
- athc: `--league` moved from `athc` to each command that uses a league, so it goes after the command name
- docs: dropped the planned root `-v/--verbose` option
- athc: the `ATHC_LEAGUE` environment variable is gone; the league comes from `--league` or `athc config set league`
- athc: config and rules files reorganised to support multiple leagues
- athc: new `athc config set` command and a root `--league` option to pick the league
- gameplan: `--play-path` alone no longer drops the league's playpool rules; the timed, rollout and QB-draw caps were silently skipped
- config: league keys are lowercase (`play_path`, `playpool_rules`); the case-keeping parser is gone
- docs: the rules TOML is the PNFL reference; the RULES_PNFL docs are gone and exit codes moved into each README
- tests: the shipped `release/athc.ini` is loaded through every section loader and its rule files must exist
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

## check-ppp

- takes its own `--league name`; help shows `file [file]`
- a profile and its gameplan are checked against each other: same side, every profile category backed by the gameplan; unused gameplan categories are info only
- added the `check-ppp` command: one profile and/or one gameplan, checked like `profile check` and `gameplan check`

## fbpro98_gameplan

- updated for the `PlayRef` rename
- added the `.pln` game plan reader and writer

## fbpro98_lg2

- added the `.lg2` league file reader

## fbpro98_play

- an unrecognized play category is an invalid `.ply` now (it was logged as an error); the play pool skips the file with a warning
- renamed the `Play` family to `PlayRef`/`CustomPlay`/`StockPlay`
- added the `.ply` play file reader

## fbpro98_profile

- added the `.prf` profile reader and writer

## gameplan

- written play paths use the play pool's folder name instead of always `PNFL`
- find-play: a wildcard PATH is a usage error, never expanded
- find-play: dropped `--verbose`, so misses always print `not found`; hits read `found in slot(s) …`, with no category on normal slots
- rules: attribute caps take a count, ratio or percent form, and the PNFL 2-DL caps moved to percents
- added the `find-play` and `replace-play` commands
- added the `gameplan` command — `check`, `list-normals`, `list-specials`, `set-normals`, `set-specials`, `find-play`

## pdbtoexcel

- playpool rules come only from the league's `rules\playpool.toml`; the shared default `playpool.toml` is gone
- rules paths resolve against the config dir; cleanup
- added the `convert-pdb` command, backed by the pdbtoexcel package

## playpool

- added the `check-playpool` command: plays in the wrong folder, duplicate play names and invalid play files, from the league's play path or a given folder
- README with quickstart and API
- renamed the `PlayRecord` family to `Play`; play attributes come from the pool's folder categories
- added the play pool package

## profile

- gameplan compatibility is checked both ways, fails the check, and is turned on per direction in the rules file
- rules: substitution bounds now cover every position group, not just QB
- rules: substitution thresholds accept `min_`/`max_` bounds per side alongside exact values; one violation per unmet side
- expanded `check`'s gameplan compatibility checks and validators
- added the `profile` command — `check`, `copy`, `diff`

## scheduler

- `solver_workers = "auto"` (the new default) uses the CPU's fast threads minus 2; the report shows the CPU and thread count
- phase 1 runs multithreaded like phase 2; `phase1_time_limit` is now deterministic time (default 120)
- league-agnostic: `--league` picks the league; conferences, divisions and same-place games come from the standings file; a solver failure exits 1; the PCFL ships in `dev/` and `release/`; one test suite for every league
- second league format: a league without divisions (`[ConferenceStandings]`), `[league] weeks`, opening non-conference weeks, a conference-sequence streak cap, rivalry week with home rotation by season; PCFL 2029 data files
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
