# Status

Where things stand now, per component: what is in, how it is laid out, what
is open, and the decisions behind it. The details of a change live here, not
in CHANGELOG.

Updated 2026-10-16. Task list: [TODO.md](TODO.md). History:
[WORKLOG.md](WORKLOG.md). Detail: [docs/](docs/).

Game plan, profile and league tools for Front Page Sports Football Pro '98.
Nine commands are in. Nothing has been released.

All non-scheduler work was committed in one batch on 2026-07-19, so git dates
for it are not when the work happened.

## Commands

```
athc autocontinue               DONE
athc check-ppp                  DONE
athc config edit                DONE
athc config get                 DONE
athc config path                DONE
athc config reveal              DONE
athc config set                 DONE
athc convert-pdb                DONE
athc gameplan check             DONE
athc gameplan find-play         DONE
athc gameplan list-normals      DONE
athc gameplan list-specials     DONE
athc gameplan replace-play      DONE
athc gameplan set-normals       DONE
athc gameplan set-specials      DONE
athc generate-schedule          DONE
athc playpool check             DONE
athc profile check              DONE
athc profile copy               DONE
athc profile diff               DONE
athc standings                  DONE
```

## standings

- `athc standings` (2026-10-13): the league's standings as played so far,
  from its current `.lge`; `--view game` (default, the game's screen),
  `league`, `conference`, `division` (ESPN's tabs); `--method scheduler`
  (default), `game`, `nfl`; one fixed coin toss. Docs:
  [standings.md](docs/standings.md).

## athc

Umbrella concerns: CLI, config, logging, docs, project tooling, install.

### CLI and help (1.0.0)

- `OUTPUT` (`convert-pdb`, `list-normals`, `list-specials`) takes a file or a
  folder, and a name with no extension gets the command's; `generate-schedule`
  takes `OUTPUT_FOLDER`. Rules:
  [docs/architecture.md](docs/architecture.md#output-files).
- Every command's help is in one style, Click's own (8.5): `[OPTIONS]` then
  UPPERCASE placeholders, a line per argument, a summary of 55 characters or
  fewer, a description of one to four lines, one to six examples. Rules:
  [docs/architecture.md](docs/architecture.md#cli).
- athc expands wildcards itself (Click's Windows expansion is off), and a name
  that exists is never a wildcard.
- Your team: `team` and `ppp_path` in `league.toml`, `--team NAME` for one
  run, and the keys `off1`, `def1`, `off2`, `def2` for its four game plans or
  profiles, shared by check-ppp, gameplan, profile and convert-pdb
  (`athc/cli/_team.py`).
- Usage errors end with a period, added in the one place.

### Console, run log and errors

- Messages review (2026-10-14): the pool's per-issue `WARN` lines stay on
  purpose, `find-play` lists hits only in a set, one word and one form for
  every message, the run log is `time LEVEL message`.
- Error wording (2026-10-09): every `FAIL` and `WARN` line is a sentence in
  Windows' words (`The system cannot find the file specified.`), names its
  file once and fits on one line; `athc/errors.py` holds the phrases and
  helpers (`reason_of`, `error_line`, `sentence`); play-list errors name the
  list and the real line. A key never starts a sentence (it joins the
  location), unknown keys are one line per table with the valid ones, and a
  config file athc cannot open fails instead of reading as empty. Rules:
  [docs/architecture.md](docs/architecture.md#console-run-log-and-errors).
- Done the pdf-converter way (2026-10-08): `athc/console.py` (Rich, one
  instance) prints every line; `athc/log.py` writes the rotating run log under
  `%LOCALAPPDATA%\athc\Logs` (`ATHC_LOG_DIR` overrides it); `athc/errors.py`
  holds `AthcError` and the shared config, league and rules errors; `main` on
  the Click command classes is the one place that turns errors into a line, a
  log entry and an exit code, under `CliRunner` too.
- Results and `OK` / `SKIP` lines on stdout; progress, `WARN` and `FAIL` on
  stderr; 0 / 1 findings / 2 error / 130 Ctrl-C in every command; a batch
  catches per item and the worst outcome wins.
- Libraries raise `AthcError` subclasses, return warnings as values and take a
  `progress` callback; nothing in a library prints or logs.
- CLI tests assert stdout and stderr apart; console, `NO_COLOR` and run-log
  tests cover the pieces. Rules:
  [docs/architecture.md](docs/architecture.md#console-run-log-and-errors).
- Errors carry the path as data: `AthcError(reason, path)` composes
  `<path>: <reason>` itself, the readers and loaders pass the path instead of
  writing it into the message, and a batch `FAIL` line names the file once.

- `docs/` is one folder per kind of doc, flat inside: one doc per module (its
  README and ARCHITECTURE merged), `formats/` (every file spec with its
  patterns), `research/` and `proposals/` (pending designs and plans; a
  finished pair folds into the docs and goes, the rule in AGENTS.md). Index:
  [docs/README.md](docs/README.md).
- Python 3.13 is the floor: `pyproject.toml`, ruff and pyright all target it.
- `league.toml`, the rule files and `scheduler.toml` may start with a UTF-8 BOM
  (Notepad, Excel); it is skipped.
- Every frozen dataclass, the Config ones included, uses `slots=True`.
- The design docs are one `docs/architecture.md`: the architecture plus a
  Cross-cutting conventions section (CLI; console, run log and errors; output
  files; config); `cli.md`, `config.md` and `logging.md` are gone, their rules
  folded in. New rule: a produced file's missing folders are created in full
  (pandoc, 7-Zip, yt-dlp do the same); `convert-pdb`, `list-normals`,
  `list-specials` and `profile diff -o` follow it.
- A league's category labels come from `league.toml` (`CategoryLabels`); the
  category enum carries only codes and game names.
- A file spec holds only the layout, its validity rules and open questions; a
  library's API is in its doc, indexed in [docs/README.md](docs/README.md).
- A league's rule files sit beside its `league.toml`; there is no `rules\`
  subfolder.
- Tests never name a real league: test leagues get neutral names, rules come
  from the tests' own files, and shipped-file tests run once per league folder.
- The PCFL ships gameplan and profile rules, copied from the PNFL's.
- One folder per league under `leagues\`; every league-aware tool reads its
  rules there. `athc.ini` keeps only app-wide settings.
- The league in use is `[athc] league`, set by hand or with
  `athc config set league NAME`, which rewrites `athc.ini` and keeps its
  comments; `athc config get league` prints it. `config get` and `config set`
  also read and write the league file's `path`, `play_path`, `team` and
  `ppp_path` (tomlkit keeps `league.toml`'s comments), and `path`, `edit` and
  `reveal` take `league.toml` as well as `athc.ini`. `--league NAME` on a league-aware command overrides it for one run
  (`athc profile check OFF1.prf --league PCFL`, like `aws s3 ls --profile x`).
- Rule layering stays: a `gameplan_rules` / `profile_rules` array in
  `league.toml` replaces the fixed file.
- Rule files live only in league folders, never next to `athc.ini`.
- The installer seeds the tree below once; an upgrade never overwrites a file
  in it, only adds missing ones.
- Unreadable config files, blank or unknown league names and a missing league
  each stop with a one-line message. No old-layout compatibility code: nothing
  has been released.

Config tree, identical in `config\dev\`, `config\release\` and the installed
`%LOCALAPPDATA%\athc\`:

```
athc.ini                      [athc] league, [autocontinue], [convert-pdb]
leagues\
  PNFL\
    league.toml               [league] path, play_path (dev also db_path); [categories.*]
    gameplan.toml
    profile.toml
    scheduler.toml            rules, solver settings, [renames.<season>]
  PCFL\
    league.toml               [league] path, play_path (dev also db_path); [categories.*]
    gameplan.toml
    profile.toml
    scheduler.toml
```

- League keys in `athc.ini` are lowercase (`play_path`) like every other key,
  so the parser no longer needs a subclass to keep key case.
- The shared exit scheme and message kinds are in architecture.md; each tool's
  README carries its own lines and what counts as a finding, where a coach
  will look.
- The `RULES_PNFL.md` docs are gone. Each tool's rules TOML is the league
  reference; a prose copy of every value went stale the moment one changed.
- The shipped `config/release/athc.ini` is loaded through every section loader in
  `test_config.py`, so a missing bundled rule file fails the suite.
- `config/dev/athc.ini` points at the real play pool and game log database. It used
  to point at the test fixtures, which nothing required.
- Agent instructions live in [AGENTS.md](AGENTS.md); `.claude/CLAUDE.md` points
  at it. New STATUS, WORKLOG, CHANGELOG and TODO entries go at the top of their
  section.
- CHANGELOG is grouped by component, alphabetically, with `config:` and other
  umbrella topics under athc.
- Setup is `uv sync` and commands run through `uv run`. Dev tools sit in a
  `dev` dependency group and `uv.lock` is committed.
- Coverage runs with every test run and fails below 92%. Ruff gained the
  pathlib, simplify, comprehension and pycodestyle-warning groups; pytest turns
  warnings into errors.
- `.vscode/` is untracked; game data files are marked binary in
  `.gitattributes`.
- Config stays INI.
- Install is a per-user `athc-<ver>-setup.exe`: a PyInstaller bundle with its
  own Python, wrapped by Inno Setup; no Python, uv or internet needed. Built
  from the exact versions in `uv.lock`. Scripts in `packaging/`; a Windows
  Sandbox test installs it, runs every command against the goldens, upgrades
  and uninstalls. athc-admin builds its own setup.exe from the same scripts;
  the public setup.exe refuses to install over it. Design: [docs/installer.md](docs/installer.md).

Open: athc-admin's three commands still call `basicConfig` and its tests still
write the old `[league.PNFL]` layout; both need updating when it picks up this
athc.

## autocontinue

Working. Docs: [autocontinue.md](docs/autocontinue.md)

- With `drive_league_pregame` on (shipped on, off when missing), it clicks
  through the league play pre-game screen (Plans/Profiles, Visitor,
  Conditions, Venues) and clicks Game; each pause setting at 0 skips its
  click.
- Return and Game are matched at 0.6, and Venues at 0.7, so the game's own
  pointer on them does not hide them.
- Tests: real game screenshots of every button it acts on, with the pointer
  elsewhere, resting on it and lighting it, where the game has that look;
  the league pre-game driven with
  the pointer on each button, and the exhibition pre-game left alone; a test
  per setting at its default, `-1` and `0`; each match cutoff from both
  sides. Slow Windows Sandbox tests play an exhibition game while a helper
  lights, moves off or leaves the pointer on each button, and drive a league
  pre-game screen on and off. The game test's menu images live with the
  test, not in the package. Every case is
  in [the test matrix](tests/integration/test-matrix-autocontinue.md).
- Just before each click it checks the button is still on screen, still under
  the spot found, and the game still in front; otherwise no click, with a
  `... gone` or `... moved; not clicked.` line. Any other failure in a pass
  is a `WARN` and a retry, never the end of the run.
- At halftime it moves the mouse to Return, waits `halftime_pause` seconds
  (8 by default) and clicks; at the end of the game it moves the mouse to
  Return and stops. One screenshot a second, checked for the Results label,
  the Halftime label, then the Continue button.
- Every `[autocontinue]` setting is optional, with the shipped defaults.
  `--continue-pause SECONDS` overrides `continue_pause` for one run;
  `-n, --dry-run` reports the button and never clicks. The status lines name
  the `athc.ini` keys and say when the game window is active; the click lands
  on the button itself.
- Its images load once at start; a missing or unreadable one stops the run
  (`Reinstall athc.`). A locked screen, screensaver or disconnected Remote
  Desktop is a `WARN` naming those causes, retried every 60 seconds.
- Hot-corner toggle, focus checks and halftime assets added.

## check-ppp

Working. Checks profiles with their gameplans, and how they fit. Docs:
[check_ppp.md](docs/check_ppp.md)

- With no path, checks your team's files (`team` in `league.toml`) where the
  league file puts them, or in `ppp_path`; `--team NAME` picks another team,
  `-a/--all-teams` every team. A folder (`.` the current one, `-r` for a
  tree) is searched for the team's files by their `.lg2` names; one `.prf`
  and one `.pln` are checked as a pair.
- The league's `.lg2` and `.lge` (in the `path` folder) name each team's four
  pairs. Where the league file puts them a missing file is a `FAIL`; in a
  folder a missing partner is a `WARN`, counted as missing. A gameplan used
  for both halves reports once. A stock league's `.lg2` is an error.
- Each file is checked and printed exactly as `profile check` and
  `gameplan check` do, with its own code. A pair must be the same side, and
  each side's rules decide what fails: the profile rules'
  `[gameplan_compatibility]` `require_all_profile_categories_in_gameplan` (on
  for PNFL and PCFL) and the gameplan rules' `[profile_compatibility]`
  `require_all_gameplan_categories_in_profile` (off; unused gameplan
  categories are then only info lines).
- An argument error stops the run before anything is read. Past that, every
  config and file error is reported in one run: a rules, league file or other
  setup error stops the rule checks and the summary, but bad files and
  mismatches still report. A side mismatch stops two-file mode; in a
  directory it is that pair's error line.

Open: PCFL's `.lg2` doesn't exist yet.

## fbpro98_gameplan (library)

Reads and writes `.pln` game plans. Docs:
[spec](docs/formats/pln.md)

- One typed custom/stock slot per special category 1-12; the clock categories
  (11 Run Clock, 12 Stop Clock) are stock-only and offense-only. A play whose
  category bytes are unrecognized is a reader error.
- The `.pln` spec gained a whole-file map and a slot layout section of its own:
  86 offsets, slots 1-1 through 16-4, then the special plays.
- Updated for the `PlayRef` rename.

## fbpro98_lg2 (library)

Reads the profile and game plan files each team uses from a league's `.lg2`.
Docs: [spec](docs/formats/lg2.md)

- Used by `check-ppp` to pair a folder's files; `path` in
  `league.toml` names the folder that holds the file.
- Team order is the league's `.lge` order (spec section 1).
- Reader in, with unit tests; reads custom and stock leagues (modern and
  old) and says which.

## fbpro98_lge (library)

Reads conference, division and team names, standings and the played games
from a league's `.lge`. Docs: [spec](docs/formats/lge.md)

- Standings: each team's W-L-T, PF and PA from the schedule; division and
  conference order the way the game orders a finished season (the manual's
  tie-breakers, checked against six seasons' playoff brackets and the 2048
  season-end screen); in season the game's screen sorts ties by points for.
- Games: each regular-season week's and each playoff round's played games
  (winner, loser), and how many games are not played yet.
- `ranked(lge, teams)`: any teams of a file in the same order, every team by
  default; the scheduler uses it for a division whose members changed.
- Reader in, with unit tests; every league size, 8 to 30 teams, stock and
  custom.
- Used by `generate-schedule` for the standings and the league structure.

## fbpro98 league files (specs)

Reverse engineered from the PNFL's game files; only `.lge` has a library so
far (`fbpro98_lge`, names and standings). Docs:
[overview](docs/formats/README.md), [lge spec](docs/formats/lge.md),
[pyr spec](docs/formats/pyr.md), [cities spec](docs/formats/cities.md),
[stats spec](docs/formats/stats.md), [notes](docs/research/pnfl-formats.md).

- `.lge`, `.rst`, `.pyr`, `.PYF`, `.dft`, `.tmn` and `.lgc` decoded in full;
  `.dat` + `.idx` mostly (stat categories 12, 14, 15 and part of 16 unmapped).
- `research/pnfl_decode.py` reads them all (stdlib, read-only).

## fbpro98_play (library)

Reads `.ply` play files. Docs: [spec](docs/formats/ply.md)

- Reads every player's logic boxes and tells a play's attributes from them:
  timed pass and QB run (the QB's commands), rollout (the QB gets beyond a given
  margin outside the outermost offensive lineman, C, G or T, on that side
  before he passes) and the defensive front from the down
  linemen (3-4 / 4-3 on Run Left, Middle and Right plays, 2-DL on pass
  plays). A player record too short for its logic boxes makes the file
  invalid. A damaged play file gets one message, `The play file is invalid or
  corrupted.`; only a wrong header and an unknown category say more.
- The special-teams enum includes the two clock categories, Run Clock (`0x0B`)
  and Stop Clock (`0x0C`).
- The `.ply` spec gained a whole-file map and its categories were split into
  sections.
- Play category is an enum with short and long forms, resolved from the play
  file itself.
- The `Play` family renamed to `PlayRef`/`CustomPlay`/`StockPlay`.

## fbpro98_profile (library)

Reads and writes `.prf` coaching profiles. Docs:
[spec](docs/formats/prf.md)

- Reader and writer in, with unit tests.

## fbpro98_standings (library)

Ranks a league's teams from its `.lge` files: division, conference and league
standings by the game's, the scheduler's or the NFL's tie-breakers. Docs:
[fbpro98_standings.md](docs/fbpro98_standings.md) (the design doc: each
method's steps),
[tie-breakers research](docs/research/standings-tie-breakers.md).

- One season, or last season's results for this season's divisions and
  teams, with team moves for teams whose name changed; a seeded coin toss.
- Library in, with unit tests. Used by `athc standings`; `fbpro98_lge` and
  `generate-schedule` keep their own ranking for now.

## gameplan

Working. Validates and edits `.pln` game plans. Docs:
[gameplan.md](docs/gameplan.md) · [rules](config/release/leagues/PNFL/gameplan.toml)

- The attribute caps (QB runs, rollouts, timed passes, 2-DL) count what each
  play file holds, not its name or folder.
- Rules say which categories a gameplan may contain
  (`allowed_offensive_categories` / `allowed_defensive_categories`, by the
  league's labels); a play in any other category is a violation.
- Scope: no path means the default, `.` the current folder, a path overrides
  both. `check` defaults to the current folder; `find-play`, `replace-play`
  and `set-specials` default to your team's four game plans, and `--path`
  points them at a file, a folder, a wildcard or one game plan key.
- The game plan keys `off1`, `def1`, `off2`, `def2` name your team's game
  plans on every subcommand; `--team NAME` picks another team.
- Rules can name every category: the five without a league abbreviation use
  their quoted game name (`[offense."Pass Long Left"]`), and Run Clock / Stop
  Clock may be required specials.
- A written play path starts with the play pool's folder name, so each league's
  gameplans point at its own plays.
- Rules and the play pool come from the league folder (`gameplan.toml`,
  `play_path` in `league.toml`); `check` has no overrides.
- Attribute caps take a count, ratio or percent form — one form per attribute,
  so a league writes its rule the way the league states it. Naming two forms
  for one attribute is a rules-file error.
- PNFL 2-DL caps are 50% Pass Short and Medium, 75% Pass Long, 100% Pass
  Dazzle.
- Brian reviewed the PNFL gameplan rules against the league threads; every one
  is covered.
- `find-play` searches by play name across files and trees, reading the
  category straight from the `.pln`. `replace-play` swaps one play across
  files for the first of its replacements that is not already in the
  gameplan and leaves it passing `check`.
- `set-normals`, `set-specials` and `replace-play` write in place with no backup.
- `set-normals` has no `-q`; `> nul` hides the `OK` lines.

Open: `replace-play` should take a list of plays for bulk swaps.

## pdbtoexcel — `convert-pdb`

Working. Extracts a WinLogStats database into an Excel workbook. Docs:
[pdbtoexcel.md](docs/pdbtoexcel.md)

- Each sheet's filter covers the header and every row written; it is set when
  the workbook closes, once the row count is known.
- The Type column's QB run and defensive front come from each play file, not
  its folder.
- Everything league-specific comes from the league folder: the play pool, the
  category names (`league.toml`), and the category order and deleted plays
  (`pdbtoexcel.toml`, required). The workbook names categories the league's
  way and sorts them in the league's order. The workbook always has the Total
  Stats team; the workbook options stay in `[convert-pdb]`
  (`include_category_worksheets` is no longer shipped in `athc.ini`).
- The output is optional: `<name>.xlsm` beside the PDB by default, or inside a
  folder given.
- The Slot columns come from your team's four game plans (`--path FOLDER`,
  else `ppp_path`, else where the league file puts them; `--team NAME` for
  another team), or from `-o`, `-o2`, `-d`, `-d2` alone; a missing defaulted
  plan is a `WARN` that hides its column, and a plan on the wrong side is
  refused.
- `--percentages/--no-percentages` override `calculate_percentages` both ways
  for one run (it replaced `--skip-calcs`).
- The `.pdb` spec lives in `docs/formats/`; the master VBA workbooks
  in `src/athc/pdbtoexcel/excel-template/` (not shipped) rebuild the `.bin`
  blocks. A golden workbook test pins the real `.pdb` output cell by cell.

Note: a standalone port for testers lives outside this repo at
`E:\PNFL\__My Projects\PdbToExcel_2.0`; re-sync it by hand when this package
changes.

## playpool

Working. Backs `gameplan` and `convert-pdb`; `playpool check` checks the pool.
Docs: [playpool.md](docs/playpool.md)

- QB run, rollout, pass logic and the defensive front come from the play file
  (`fbpro98_play`), by the rules in playpool.md. `playpool.toml` and
  its filename filters are gone; only a `Screens` folder still adds an
  attribute.
- An unreadable play file is skipped with a warning; plays load in sorted path
  order, so a duplicate name resolves the same way every time.
- `PlayPool` is a plain container (`add`, `find_by_name`, `issues`); it no
  longer holds `rules`/`labels` or a `to_dict`.
- Modules renamed to match the other libraries: `model.py` holds the play
  records and `PlayPool`; `reader.py` walks the folder and fills the pool.
- `check-playpool` became `playpool check`, a command group like `gameplan`
  and `profile`.
- `check` reads the league's `play_path`, or a folder given on the command
  line (a league is then optional; one that resolves still names the category
  folders). A `play_path` that is not set, missing or not a folder gets the
  `athc config set play_path FOLDER` hint.
- `check` prints the warnings pool loading already logs, word for word, as
  findings: plays in a folder that contradicts the file, duplicate names,
  invalid files.
- The `PlayRecord` family renamed to `Play`.
- Plays are classified from the play file, with the user category
  authoritative; folder categories only warn.

Open: count plays by file name type (TODO).

## profile

Working. Validates and compares `.prf` coaching profiles. Docs:
[profile.md](docs/profile.md) · [rules](config/release/leagues/PNFL/profile.toml)

- `copy --pat-logic` copies the whole 60-situation PAT table, either side.
- `check` defaults to the current directory when no path is given, like
  `grep -r` and `find`.
- `check` takes its rules from the league folder (`profile.toml`, or a
  `profile_rules` array in `league.toml`); there is no override.
- `check` validates profiles only; checking a profile with its gameplan is
  `check-ppp`'s job.
- Substitution bounds cover every position group: QB pinned at 75/80, every
  other group but K capped at 95 out and 96-100 in.
- Substitution rules take `min_`/`max_` bounds per side as well as exact
  values; a side with no key is unchecked and each unmet side reports on its
  own line.
- Brian reviewed the PNFL profile rules against the league thread; every one is
  covered.
- `diff` reports one line per differing situation and infers CSV from the
  `--output` extension.
- `copy` writes each target in place with no backup.
- The profile keys `off1`, `def1`, `off2`, `def2` name your team's profiles in
  `check`, `diff` and `copy`; `--team NAME` picks another team. `copy` takes
  `SOURCE TARGET...`, and `--substitutions` replaced `--sub-percent`.

Open: revisit `edit`/`copy` options (a copy across sides is still one `SKIP`
per target).

## scheduler — `generate-schedule`

Working. Docs: [scheduler.md](docs/scheduler.md) ·
[phase 1](docs/scheduler-phase-1-matchups.md) ·
[phase 2](docs/scheduler-phase-2-schedule.md)

- Phase 1 aims each team at a sum of opponent conference ranks, not an
  average: the slope tilts the league's smallest non-conference count and
  each extra game adds a neutral rank 5, so a 4-team-division team's fifth
  game is no longer tilted. The top-half/bottom-half opponent rule is gone.
  `[phase1] random_nonconference` (the PCFL's, off) picks the non-conference
  games at random instead, through seeded pair weights in the same solve.
  `scheduler.toml` reads `[solver]` (`phase1_time_limit`,
  `phase2_time_limit`) then `[phase1]` (`difficulty_slope`, was
  `[difficulty] spread`); `--phase2-time-limit` replaces `--time-limit`.
  An unknown table or `[solver]` key is an error, like the other tables'
  unknown keys.
- Ctrl+C stops the run with `FAIL Interrupted.` (exit 130) and nothing
  written: CP-SAT's own handler is off and a console handler stops the
  search at the press; a press while the three files are written takes
  effect once all three are written.
- CLI fits the shared help style: `--previous FILE` (optional, default the
  upcoming file) and `--upcoming FILE` (default `<league>.lge` in `path`)
  take the `.lge` file itself; `--seed` is 0 to 2147483647 and
  `--phase2-time-limit` 1 or more, usage errors outside;
  `[solver] phase1_time_limit` and `phase2_time_limit` must be positive; with
  no `path` and no `--upcoming`, the "League files folder is not set" hint.
- `solver_workers = "auto"` is the default: the CPU's fast threads (P-cores
  on Intel hybrid CPUs) minus 2. A benchmark on an i5-14600KF found 8-12
  threads fastest and 18-24 slower. The report shows the CPU, thread count and
  seed, so a schedule can be reproduced on another machine.
- League data from the game's files: `--previous FILE` is the previous
  season's `.lge` (standings: records, opponents, playoff results), else the
  upcoming file gives them too and `[renames.<season>]` is ignored;
  `--upcoming FILE` is the upcoming season's (conferences, divisions, names;
  default `<league>.lge` in the league's `path`). An unfinished season is a
  `WARN`, and the run goes on with the games played. Teams match by name;
  `[renames.<season>]` in `scheduler.toml` lists the ones that changed (a
  realignment moves team numbers, so numbers never match). Overall order:
  playoff finish, record, strength of schedule, the previous season's
  division finish, point differential, then a coin toss drawn from the
  run's seed, which reproduces the PNFL's published 2048 order. Division
  finish: each upcoming division's members in the lge library's order for
  the previous season as it stood, with the coin toss last, so a team that
  moved keeps its record and the others shift around it (the 2002 NFL
  realignment ranked its new divisions the same way). No file's team order
  breaks a tie. The `standings\<season>.league.ini` files are gone.
- League-agnostic: `--league NAME` picks the league; its rules are
  `scheduler.toml` in the league folder. Conferences and divisions come from
  the league file by position, the same-place games from the divisions, and
  the writers take the league name. No league or division name is left in
  scheduler code or tests; one validator and one test suite run every league.
  The PCFL ships in `leagues\PCFL\` in `config/dev/` and `config/release/`.
- Two league formats: the PNFL (divisions, 16 weeks) and the PCFL (two
  conferences of nine, 12 weeks, rivalry week). One matchup builder and one
  schedule builder; PNFL-only rules are toggles.
- Rules overhauled from NFL data: hard rules, league-wide anti-pileup caps,
  and a soft objective with NFL-typical bands so seasons vary.
- Schedulers A, B and D removed; there is just the scheduler, no
  `--scheduler` flag.
- Both phases run multithreaded and stop on deterministic time, not
  wall-clock, through one shared solver setup. Verified against the OR-Tools
  source: interleave search is valid here and used correctly.
- Golden integration test compares three output files byte for byte; the
  divisional case is the real 2048 PNFL season from its league files, the
  conference case a built pair of league files.
- Past PNFL seasons were re-ranked from real results using SOS tiebreaks, which
  gave a real-schedule baseline to measure generated seasons against and the
  ranking rule the loader now applies.
- Every run writes three files named to the minute in `OUTPUT_FOLDER`, else the
  current folder; a rerun in the same minute replaces them.

Open: simplify the ruleset — 50 `[phase2]` keys, some redundant by
construction, never pruned · then the quirk budget in
[quirk-budget.md](docs/proposals/quirk-budget.md) · delete the obsolete
`TEST_DATA/scheduler_integration/` at the workspace root.

## Decisions

- **`gameplan check` and `profile check` are not dropped for check-ppp.**
  They check files of one kind by any name, many at once, with wildcards and
  trees; check-ppp pairs files only as the league file names them, plus one
  pair given by hand. The split is helm lint beside yamllint and cargo check
  beside rustc.
- **No athc command has a quiet flag.** `> nul` hides the `OK` lines and keeps
  every `FAIL` on standard error.
- **The team's game plans are the default scope of the gameplan batch
  commands; check keeps the current folder.** `find-play`, `replace-play` and
  `set-specials` work on your team's game plans; `gameplan check` stays the
  any-name checker of the current folder.
- **Wildcards stay, expanded by athc.** `gameplan check`, `profile check`,
  `profile copy` and `--path` on `find-play`, `replace-play` and
  `set-specials` take one; Click's own Windows expansion is off.
- **check-ppp checks pairs only; `profile check` and `gameplan check` stay.**
  check-ppp always takes a profile with its gameplan and replaced
  `profile check --gameplan`, now removed; the two check commands stay for
  checking many files of one kind.
- **check-ppp pairs a folder's files from the league's `.lg2`.** The game's own
  league file already lists every team's eight files, so no team list is kept
  in config. Pairs match by file name in one folder at a time, since weeks and
  seasons reuse the same names.
- **check-ppp follows each side's compatibility setting.** A profile
  category the gameplan lacks is the profile's error, so that setting is in
  the profile rules (`[gameplan_compatibility]`); the reverse check's setting
  is in the gameplan rules (`[profile_compatibility]`). PNFL and PCFL require
  every profile category in the gameplan, and leave unused gameplan
  categories as info lines.
- **check-ppp tells its files apart by extension.** Positional files of mixed
  kinds, like gcc, so the order never matters.
- **One folder per league, fixed file names inside.** The OBS / Kodi / Hugo
  shape; nothing lists the inner files in config, so adding a league is
  copying a folder.
- **The league in use is a key in `athc.ini`, not a separate state file.**
  Calibre keeps its current library the same way; `athc config set` rewrites
  the file with ConfigUpdater so the comments survive.
- **`--league` is on each league-aware command, after the command name.**
  `aws s3 ls --profile x` and `kubectl get --context x` take theirs there too;
  Click only takes a root option before the command name, which read oddly.
- **convert-pdb's workbook options are app-wide.** They stay in
  `[convert-pdb]`; only the play pool is per league.
- **check-ppp's compatibility rules live in the rules file, not the code.**
  They are league rules like any other, so a league enables each direction
  itself.
- **`solver_workers` defaults to `"auto"`.** A seed reproduces only at the same
  thread count, so the report shows the count and it stays config-only.
- **The config command is `reveal`, not `explorer`.** It opens the config dir
  in Explorer, but the name should not promise Windows.
- **A bundled `.exe` still needs a real config folder.** The bundle carries no
  editable config, so the setup.exe seeds it into `%LOCALAPPDATA%\athc`.
- **STATUS carries no test counts.** They change every run.
- **The tools stay PNFL-specific.** playpool, gameplan and profile all lean on
  PNFL conventions, and making them fully league-agnostic would cost more than
  it is worth.
- **The CLI is Click.** CLI tests run through its `CliRunner`.
- **athc-admin ships the full installer.** Open to revisiting.
- **`uv` runs the project.** It handles Python, dependencies and the lockfile,
  in place of pip.
- **Config is `configparser`.** Pydantic was considered and dropped.
