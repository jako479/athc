# Changelog

Very high-level, release-note style: what is new or changed, one line per
feature or change, nothing technical. A finished TODO item moves here as its
own line, stripped of the detail that only explained the work; any other
high-level change completed alongside it gets its own line.

## athc

- athc: the defensive Dazzle categories carry the game's names, Razzle Dazzle Run and Razzle Dazzle Pass, in every tool
- fbpro98_play: a play whose record offset points inside the header or category bytes is rejected as damaged
- fbpro98_play: tests reviewed: gaps filled, error messages pinned in full, size limits probed at the edge, redundant tests dropped
- fbpro98_gameplan: tests check every reader error at its limit and one past it, the counts a write updates for a stock play and a custom special play, and the pad on both sides; goldens that only restated the slot layout went; the `.pln` spec's parity pad is on either side when needed, not defense only
- fbpro98_lge, fbpro98_lg2: tests pin strength of schedule counting each opponent once, a tree with more divisions or teams than counted, an empty week, playoff-round numbering, the error offsets and the size-before-fields order, and the `.lg2` team order against the `.lge`
- athc: the `.prf` spec says where the game puts an embedded game plan: a G95 + S98 pair before I95, whose count field counts those blocks
- athc: the profile library's tests check the situation layout at the start of every group, every reader check and limit, the PAT weight rule and an edit of every profile field; cases the byte-identical round trip already proved are gone
- athc: docs regrouped: `docs/design/` holds the design docs, `docs/usage/` the end-user docs the installer ships (one file per command, each with its options, settings, lines and exit codes), `docs/research/` the game and league notes
- gameplan: set-normals reports every bad line of a play list in one run; a special play no longer hides the others
- gameplan: tests check both sides of every rule limit and the wording of every rule message, plus a wrong `--league`, a bug in one file and a play list that does not fit
- athc: the `.dat` / `.idx` spec names every header field after FairCom's c-tree file header and states how deleted slots and index nodes are reused and how full nodes split
- athc: the game-behavior doc says how the game updates the stats files each week, at the end of the regular season and through the playoffs
- athc: library tests no longer restate layout constants or check that frozen dataclasses refuse changes
- fbpro98_stats: reads a league's .dat stats file: player, team and opponents stats for the last game, season and career, and the honors
- athc: the `.dat` / `.idx` spec now decodes field goal ranges, safeties, blocked punts, fair catches, first downs, third and fourth downs, penalties, awards and the Hall of Fame
- gameplan: set-normals leaves a slot empty for each blank line in the list again; the help says set-normals replaces all 64 normal plays and set-specials only the listed ones
- athc: options that override a setting no longer state its value; `list-normals --sort` and `standings --view` help is one short line
- check-ppp: `--all-teams` help says it checks every team's profiles and game plans; gameplan's key list is "for your team's game plans"
- athc: help writes defaults as `(default: ...)` and puts the commands and settings it names in single quotes
- athc: help says stdout and stdin, not the console (`use '-' for stdout`, `use '-' for stdin`)
- athc: OUTPUT help names the default plainly (`<name>.normals.txt next to GAME_PLAN`) and says `use '-' for stdout`
- athc: the setup.exe refuses to install over a newer installed version
- profile: rules list the categories a profile may use, by the league's names, in place of the never-use lists
- convert-pdb: an `.xlsm` always outlines the selected row; the Options sheet's Highlight Selected Row option is gone
- convert-pdb: the golden workbook test uses a real week's PDB with its own test pool holding every play in it, so it runs with no warnings
- profile: `copy` onto the same file as its only target is an error, as with Windows' `copy`; in a bulk copy the source is still skipped
- profile: a situation rule's disallowed list now forbids only the categories it names; it no longer also forbids every category the league gives no short name
- athc: settings file is athc.toml (TOML, like every other settings file); a league's league.toml overrides a tool's settings a key at a time
- convert-pdb: the category order and deleted plays live in athc.toml, overridable per league; pdbtoexcel.toml is gone
- athc: every library test of an add, update or remove now checks the whole result, not just the changed item
- autocontinue: the real-game tests build their own game from the dev's game install and the repo's test league
- autocontinue: the installer no longer carries the game test's menu images
- autocontinue: tested on real game screens with the pointer off, on and lighting every button it clicks, and with each setting at its default, -1 and 0
- autocontinue: finds Venues on the league play pre-game screen even with the game's pointer resting on it
- autocontinue: finds Return at halftime and Game on the pre-game screen even with the game's own pointer on them
- autocontinue: clicks through the league play pre-game screen and starts the game (`drive_league_pregame`, on in the shipped athc.ini); a pause of 0 skips its click
- athc: an athc.ini saved as something other than UTF-8 is a config error naming the file, not a crash
- autocontinue: a one-off failure mid-game warns and retries instead of ending the run; a button that moved, or the game losing focus, just before a click means no click
- autocontinue: checks a button is still on screen just before clicking it, so one the coach already clicked is left alone
- autocontinue: clicks Return at halftime after `halftime_pause` seconds (8 by default) and stops at the end of the game
- autocontinue: every setting is optional, with the shipped defaults; `--continue-pause` sets the wait before each Continue click for one run; `-n/--dry-run` reports the button and never clicks; it says when it has the game window; the click lands on the button itself
- generate-schedule: takes an output folder, the current folder by default
- convert-pdb, gameplan list-normals and list-specials: the output can be a folder, and a name with no extension gets the command's own
- convert-pdb: each sheet's filter covers all its rows, not just the header
- generate-schedule: an unknown table or `[solver]` key in `scheduler.toml` is an error, like an unknown key in the other tables; the error names only the unknown ones, not every valid name
- generate-schedule: every team's non-conference difficulty covers the same number of games, so an extra game is no harder or easier than average; no team has to draw a top-half and a bottom-half opponent
- generate-schedule: `random_nonconference` picks the non-conference games at random from the run's seed (the PCFL's option, off)
- generate-schedule: `--phase2-time-limit` replaces `--time-limit`; `scheduler.toml` puts `[solver]` first with `phase1_time_limit` and `phase2_time_limit`, and `[phase1] difficulty_slope` replaces `[difficulty] spread`
- gameplan: find-play prints hits only when searching a set; a single game plan still says when the play is not in it
- athc: messages say "game plan", "special" and "is not in the play pool" everywhere, and every command hint reads `Run 'athc ...'`
- athc: set-normals says `updated`, generate-schedule says `written`, and no line quotes a path
- athc: the run log is `time LEVEL message`, the level once: `WARN` and `FAIL` lines carry it as the level, `OK` and `SKIP` lines keep their word
- docs: `docs/` is four folders: one doc per module, `formats/` for every file spec and its patterns, `research/` and `proposals/`; the designs, specs and plans of merged work are gone
- docs: tie-breaking has one design doc, the standings library's ARCHITECTURE, and one research note; the standings specs and plans are gone
- standings: `athc standings` takes the shared help style
- generate-schedule: an unfinished season is a warning, not an error; ties in the standings go to the previous season's division finish, then a coin toss from the run's seed, never a file's order; Ctrl+C stops the run and writes nothing
- generate-schedule: `--previous` and `--upcoming` take the `.lge` file itself and `--previous` is optional; a hint when the League files folder is not set; `--seed`, `--time-limit` and the solver budgets in `scheduler.toml` are bounded
- playpool: `check` says to set `play_path` or pass the folder when the pool is unset or missing
- config: edit reports a file Windows cannot open instead of doing nothing
- config: get prints the league in use and a league's path, play_path, team and ppp_path; path, edit and reveal take league.toml as well as athc.ini; set writes path, play_path, team and ppp_path to the league's league.toml and says which file it wrote
- convert-pdb: the output is optional, `<name>.xlsm` beside the PDB
- convert-pdb: the Slot columns come from your team's game plans by default (`--path`, `ppp_path` or the league file; `--team` for another team), or from `-o`, `-o2`, `-d`, `-d2` alone; a plan on the wrong side is refused
- convert-pdb: `--percentages/--no-percentages` replace `--skip-calcs` and override the setting both ways
- profile: check, diff and copy take off1, def1, off2 or def2 for one of your team's profiles, with `--team` for another team
- profile: copy takes several targets (`SOURCE TARGET...`); `--substitutions` replaces `--sub-percent`
- gameplan: find-play, replace-play and set-specials work on your team's game plans by default; --path points them at a file, a folder, a wildcard or one game plan
- gameplan: every subcommand takes off1, def1, off2 or def2 for one of your team's game plans
- gameplan: set-normals dropped -q; redirect with > nul instead
- gameplan: find-play's --path takes a wildcard
- gameplan: a play list that cannot be read is one FAIL line (Not a valid play list.), not an unexpected error
- check-ppp: checks your team's profiles and game plans where the league file puts them (or in `ppp_path`) by default; `--team` and `--all-teams` pick other teams, and a folder is searched for the team's files
- athc: every command's help in one style: `[OPTIONS]` usage, UPPERCASE placeholders, a line per argument, a short summary and examples
- athc: athc expands wildcards itself, and a name that exists is never a wildcard
- athc: `League is not set.` replaces `No league selected.`; a missing `play_path` folder says to run `athc config set play_path FOLDER`
- standings: new `athc standings` command shows the league's standings as played so far, as the game's standings screen or ESPN's League, Conference and Division tabs
- fbpro98_standings: new library that ranks division, conference and league standings from `.lge` files by the game's, the scheduler's or the NFL's tie-breakers
- athc: the `.lge` spec decodes each team's Training Camp percentages
- league.toml and athc.ini: each comment says what the setting is, not which commands read it
- convert-pdb: the Type column says `QB run`, not `QB draw`
- fbpro98_play: a damaged play file reads `The play file is invalid or corrupted.`; a wrong header and an unknown category keep their own messages
- playpool: QB run, rollout, timed pass and the defensive front come from each play file, not its name or folder; `playpool.toml` is gone
- fbpro98_play: tells a play's timed pass, QB run, rollout and defensive front (2-DL, 3-4, 4-3) from its players' logic
- generate-schedule: reads the standings from the previous season's `.lge` (`--previous folder`) and the conferences, divisions and teams from the upcoming season's (`--upcoming folder`, default the league's `path`); the `standings\<season>.league.ini` files are gone; a team that changed its name is listed under `[renames.<season>]` in `scheduler.toml`
- generate-schedule: the overall order is the league's own: playoff finish, record, strength of schedule, then point differential
- fbpro98_lge: standings follow the game's own order for a finished season (the manual's tie-breakers: head-to-head, division record, conference record, net points, strength of schedule) instead of point differential; any teams of a file can be ranked the same way
- fbpro98_lge: reads the played games by week and playoff round, with each game's winner and loser, and how many games are left
- tests: every CLI test checks stdout and stderr apart; console, `NO_COLOR` and run-log tests added
- docs: the cross-cutting rules live in one `architecture.md`; each tool's README lists its status lines and exit codes
- gameplan: `set-normals` / `set-specials` call their list argument `play_list`, and a console list's errors say `(play list line N)`
- autocontinue: a missing or unreadable Continue button image stops the run with a reinstall hint; a locked screen warns with its likely causes
- athc: an `athc.ini` or standings file that cannot be opened fails instead of reading as empty
- gameplan: play lists saved with a BOM (Notepad's "UTF-8 with BOM") read their first play
- athc: every `FAIL` and `WARN` line is a sentence in Windows' words, names its file once and fits on one line
- gameplan: play-list errors name the list file and the real line
- athc: the `.dat` / `.idx` spec decodes a league's player and team statistics (last game, season and career) and their index
- gameplan: `replace-play` takes backup replacements, tried in order: one already in the gameplan or that would make it fail `check` is skipped; the path is optional (the current folder)
- check-ppp: every kind of stock league gets the same `Stock league not supported.` line
- fbpro98_lg2: reads stock leagues, modern and old, and says which kind of league it read
- fbpro98_play: the `.ply` spec decodes each player's position and logic boxes, enough to tell a timed pass, QB run or rollout, and a 2-DL, 4-3 or 3-4 defense
- athc: the `.lge` spec shows how a roster slot sets a player's status (Assigned, Open Active, Open Inactive) and depth
- athc: the `.pyr` spec is checked against the game's Player Editor and injury screens
- gameplan: `set-normals` / `set-specials` input errors from the console no longer start with `- `; `find-play` prints no tally for a single path that failed
- playpool: `check` on a folder that does not exist says `not found`, and `not a directory` only for a file in its place
- athc: bare `athc` no longer writes its whole help text into the run log
- athc: a run-log folder that cannot be written is one `FAIL` line and exit 2 instead of a traceback
- athc: a named file that does not exist is `FAIL <file>: not found` in every command, never Python's `[Errno 2]` text
- athc: a config or rules file that cannot be read names it once (`<file>: No such file or directory`), not again inside Python's text
- athc: an error about a file names it once, first (`FAIL <file>: <why>`), in every command; the scheduler's config errors read the same way
- athc: every command prints the same way: `OK` / `SKIP` / `WARN` / `FAIL` status lines, the label colored on a terminal (`NO_COLOR` turns it off); results, `OK` and `SKIP` on stdout, progress, `WARN` and `FAIL` on stderr
- athc: every run writes a run log, `%LOCALAPPDATA%\athc\Logs\athc.log` (1 MB, five files kept): the command line, every status line, every traceback and the exit code
- athc: one exit scheme in every command: 0 done (warnings included), 1 findings (the checkers and finders only), 2 any error, 130 Ctrl-C; a batch processes every file and the worst outcome wins
- athc: a bug prints one `FAIL ... unexpected error (see log: ...)` line instead of a traceback; `ATHC_DEBUG` is gone
- convert-pdb: a league without `play_path` is an error, not an empty workbook
- convert-pdb: progress on stderr, a `WARN` line per play-pool, rules, PDB or workbook notice, then `OK   <file>: <n> play(s)`
- generate-schedule: progress on stderr, an `OK` line per file written, then `Generated <n> games (seed <s>)`
- autocontinue: its status lines go to stderr and the run log
- athc: Python 3.13 is the minimum version
- athc: every frozen dataclass, the Config ones included, uses `slots=True`
- install: athc ships as `athc-<ver>-setup.exe`, which needs no Python, uv or internet; a per-user install with `athc` on PATH, settings seeded once and never overwritten, and an uninstaller that removes everything
- convert-pdb: the category order is league data again — `pdbtoexcel.toml` in the league folder lists the run, pass and defense categories in the order the rows sort and the Options sheet shows them, by the league's names (`PSL`, `RunLeft`)
- convert-pdb: `pdbtoexcel.toml` also lists deleted plays, skipped quietly instead of warning "Play file not found"
- convert-pdb: the play names a league's `playpool.toml` lists under include / exclude are checked against the play pool; one not in the pool, on the wrong side, or under both lists is a warning
- convert-pdb: the release settings count sacks as pass attempts
- convert-pdb, gameplan `list-normals` / `list-specials`, profile `diff -o`: the output file's missing folders are created in full instead of being an error
- gameplan: rules list the categories a gameplan may contain (`allowed_offensive_categories` / `allowed_defensive_categories`, by the league's labels) instead of the ones it may not
- config: the TOML rule and scheduler files carry no `schema_version` line; the rule loaders reject it like any other unknown key
- gameplan: `list-normals --sort category` groups the plays by category, each group under a `::` header with the league's category name
- gameplan: `list-normals` reads the league like the other gameplan commands and takes `--league`
- gameplan: a rules file whose `offense` / `defense` value or section is not a table is reported like any other rules error instead of crashing
- gameplan: `check` names a required or stock-only special category by its game name (`Kickoff`, `Kick Return`) instead of its slot number
- playpool: an unreadable play file is skipped with a warning instead of failing the whole load
- playpool: plays load in path order, so the same play wins a duplicate name every time
- playpool: the pool no longer carries the rules and labels it was built with, nor a `to_dict`; `add` takes only sided plays
- playpool: library modules renamed to match the other libraries: `model.py` (play records and the pool) and `reader.py` (builds the pool from a folder)
- scheduler: the phase-2 rules are documented once, in the phase-2 design doc; the code keeps only its modeling notes
- config: `league.toml`, the TOML rule files and `scheduler.toml` may start with a UTF-8 byte-order mark (Notepad, Excel); it is skipped
- playpool: `check` on a given folder still uses the configured league's category names for its folders; with no league, folder names are not checked
- config: league settings moved from `league.ini` to `league.toml`; a league's short names for the play categories live there under `[categories.offense]` / `[categories.defense]`, no longer in code
- playpool: `check-playpool` became `playpool check`, a command group like `gameplan` and `profile`
- profile: `copy --pat-logic` copies the PAT play-calling table into the targets
- athc: the file specs hold only the file layout, its validity rules and open questions; each library's README documents its API, indexed in the architecture overview
- athc: the file specs name fields in prose and keep code font for what is stored in the file
- fbpro98_play: the `.ply` spec explains the category bytes and shows sample plays
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

## fbpro98_lge

- standings: each team's W-L-T, points for and against, and division and conference order
- added the `.lge` league file reader: conference, division and team names, every league size

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
