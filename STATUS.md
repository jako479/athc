# Status

Where things stand now, per component: what is in, how it is laid out, what
is open, and the decisions behind it. The details of a change live here, not
in CHANGELOG.

Updated 2026-10-07. Task list: [TODO.md](TODO.md). History:
[WORKLOG.md](WORKLOG.md). Detail: [docs/](docs/).

Game plan, profile and league tools for Front Page Sports Football Pro '98.
Eight commands are in. Nothing has been released.

All non-scheduler work was committed in one batch on 2026-07-19, so git dates
for it are not when the work happened.

## Commands

```
athc autocontinue               DONE
athc check-playpool             DONE
athc check-ppp                  DONE
athc config edit                DONE
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
athc profile check              DONE
athc profile copy               DONE
athc profile diff               DONE
```

## athc

Umbrella concerns: CLI, config, logging, docs, project tooling, install.

- A file spec holds only the layout, its validity rules and open questions; a
  library's API is in its README, indexed in
  [docs/design/overview.md](docs/design/overview.md).
- A league's rule files sit beside its `league.ini`; there is no `rules\`
  subfolder.
- Tests never name a real league: test leagues get neutral names, rules come
  from the tests' own files, and shipped-file tests run once per league folder.
- The PCFL ships gameplan, playpool and profile rules, copied from the PNFL's.
- One folder per league under `leagues\`; every league-aware tool reads its
  rules and standings there. `athc.ini` keeps only app-wide settings.
- The league in use is `[athc] league`, set by hand or with
  `athc config set league NAME`, which rewrites `athc.ini` and keeps its
  comments. `--league NAME` on a league-aware command overrides it for one run
  (`athc profile check OFF1.prf --league PCFL`, like `aws s3 ls --profile x`).
- Rule layering stays: a `gameplan_rules` / `profile_rules` list in
  `league.ini` replaces the fixed file.
- Rule files live only in league folders; there is no shared default
  `playpool.toml` next to `athc.ini`.
- The installer ships the tree below; `league.ini` and standings survive a
  reinstall, rule files are replaced.
- Unreadable config files, blank or unknown league names and a missing league
  each stop with a one-line message. No old-layout compatibility code: nothing
  has been released.

Config tree, identical in `config\dev\`, `config\release\` and the installed
`%LOCALAPPDATA%\athc\`:

```
athc.ini                      [athc] league, [autocontinue], [convert-pdb]
leagues\
  PNFL\
    league.ini                [league] play_path (dev also db_path)
    gameplan.toml
    profile.toml
    playpool.toml
    scheduler.toml
    standings\
      2045.league.ini … 2049.league.ini
  PCFL\
    league.ini                [league] play_path, db_path
    gameplan.toml
    profile.toml
    playpool.toml
    scheduler.toml
    standings\
      2029.league.ini
```

- League keys in `athc.ini` are lowercase (`play_path`, `playpool_rules`) like
  every other key, so the parser no longer needs a subclass to keep key case.
- Exit codes and the error-vs-finding distinction live in each tool's README,
  where a coach will look, not in ARCHITECTURE.
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
- Config stays INI. Logging is designed but not wired — one `basicConfig` in
  `cli()`, per [docs/design/logging.md](docs/design/logging.md).
- Install is `install.bat` plus a wheel in a zip; uv downloads a managed
  Python, so Python is no longer a prerequisite.

Open: a PyInstaller `.exe` installer in place of `install.bat` and the uv
prerequisite · wire the logging design into `cli()` · athc-admin's tests still
write the old `[league.PNFL]` layout and need updating when it picks up this
athc.

## autocontinue

Working. Docs: [README](docs/autocontinue/README.md) ·
[ARCHITECTURE](docs/autocontinue/ARCHITECTURE.md)

- Hot-corner toggle, focus checks and halftime assets added.

Open: halftime handling itself.

## check-playpool

Working. Checks the play pool. Docs: [README](docs/check_playpool/README.md)

- Reads the league's `play_path`, or a folder given on the command line (then
  no league is read). `playpool.toml` is not used.
- Prints the warnings pool loading already logs, word for word, as findings:
  plays in a folder that contradicts the file, duplicate names, invalid files.

Open: maybe use `playpool.toml` for counts by file name type (TODO).

## check-ppp

Working. Checks profiles with their gameplans, and how they fit. Docs:
[README](docs/check_ppp/README.md)

- Takes one `.prf` and one `.pln`, in either order (the extension tells them
  apart), or a directory (`-r` for a tree). Both files are required.
- In a directory, the league's `.lg2` (in the `path` folder) names each
  team's four pairs; every pair with both files in one folder is checked,
  matched by file name, ignoring case. Each folder of a tree stands alone. A
  gameplan used for both halves reports once.
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
[spec](docs/fbpro98_gameplan/specs/pln.md)

- One typed custom/stock slot per special category 1-12; the clock categories
  (11 Run Clock, 12 Stop Clock) are stock-only and offense-only. A play whose
  category bytes are unrecognized is a reader error.
- The `.pln` spec gained a whole-file map and a slot layout section of its own:
  86 offsets, slots 1-1 through 16-4, then the special plays.
- Updated for the `PlayRef` rename.

## fbpro98_lg2 (library)

Reads the profile and game plan files each team uses from a league's `.lg2`.
Docs: [spec](docs/fbpro98_lg2/specs/lg2.md)

- Used by `check-ppp` to pair a folder's files; `path` in
  `league.ini` names the folder that holds the file.
- Team order is the league's `.lge` order (spec section 1).
- Reader in, with unit tests; stock leagues are rejected.

## fbpro98 league files (specs only)

Reverse engineered from the PNFL's game files; no libraries yet. Docs:
[overview](docs/design/fbpro98-files.md), [lge spec](docs/fbpro98_lge/specs/lge.md),
[pyr spec](docs/fbpro98_pyr/specs/pyr.md), [cities spec](docs/fbpro98_cities/specs/cities.md),
[notes](docs/design/research/pnfl-formats.md).

- `.lge`, `.rst`, `.pyr`, `.PYF`, `.dft`, `.tmn` and `.lgc` decoded in full;
  `.dat` stat records mostly.
- `research/pnfl_decode.py` reads them all (stdlib, read-only).

## fbpro98_play (library)

Reads `.ply` play files. Docs: [spec](docs/fbpro98_play/specs/ply.md)

- The special-teams enum includes the two clock categories, Run Clock (`0x0B`)
  and Stop Clock (`0x0C`).
- The `.ply` spec gained a whole-file map and its categories were split into
  sections.
- Play category is an enum with short and long forms, resolved from the play
  file itself.
- The `Play` family renamed to `PlayRef`/`CustomPlay`/`StockPlay`.

## fbpro98_profile (library)

Reads and writes `.prf` coaching profiles. Docs:
[spec](docs/fbpro98_profile/specs/prf.md)

- Reader and writer in, with unit tests.

## gameplan

Working. Validates and edits `.pln` game plans. Docs:
[README](docs/gameplan/README.md) · [rules](config/release/leagues/PNFL/gameplan.toml)

- `check` and `find-play` default to the current directory when no path is
  given, like `grep -r` and `find`; `find-play` only does so with a single
  argument, since with two or more the last is always the path.
- Rules can name every category: the five without a league abbreviation use
  their quoted game name (`[offense."Pass Long Left"]`), and Run Clock / Stop
  Clock may be required specials.
- A written play path starts with the play pool's folder name, so each league's
  gameplans point at its own plays.
- Rules and the play pool come from the league folder (`gameplan.toml`,
  `playpool.toml`, `play_path` in `league.ini`); `check` has no overrides.
- Attribute caps take a count, ratio or percent form — one form per attribute,
  so a league writes its rule the way the league states it. Naming two forms
  for one attribute is a rules-file error.
- PNFL 2-DL caps are 50% Pass Short and Medium, 75% Pass Long, 100% Pass
  Dazzle.
- Brian reviewed the PNFL gameplan rules against the league threads; every one
  is covered.
- `find-play` searches by play name across files and trees, reading the
  category straight from the `.pln`. `replace-play` swaps one play across
  files.
- `set-normals`, `set-specials` and `replace-play` write in place with no backup.

Open: `replace-play` should take a list of plays for bulk swaps.

## pdbtoexcel — `convert-pdb`

Working. Extracts a WinLogStats database into an Excel workbook. Docs:
[README](docs/pdbtoexcel/README.md) ·
[ARCHITECTURE](docs/pdbtoexcel/ARCHITECTURE.md)

- The play pool and playpool rules come only from the league folder. The
  workbook always has the Total Stats team; the three other workbook options
  stay in `[convert-pdb]`.
- The `.pdb` spec lives in `docs/pdbtoexcel/specs/`; the master VBA workbooks
  in `src/athc/pdbtoexcel/excel-template/` (not shipped) rebuild the `.bin`
  blocks. A golden workbook test pins the real `.pdb` output cell by cell.

Note: a standalone port for testers lives outside this repo at
`E:\PNFL\__My Projects\PdbToExcel_2.0`; re-sync it by hand when this package
changes.

## playpool (library)

Working. Backs `gameplan` and `convert-pdb`. Docs:
[README](docs/playpool/README.md),
[ARCHITECTURE](docs/playpool/ARCHITECTURE.md)

- The `PlayRecord` family renamed to `Play`.
- Plays are classified from the play file, with the user category
  authoritative; folder categories only add attributes.

## profile

Working. Validates and compares `.prf` coaching profiles. Docs:
[README](docs/profile/README.md) · [rules](config/release/leagues/PNFL/profile.toml)

- `check` defaults to the current directory when no path is given, like
  `grep -r` and `find`.
- `check` takes its rules from the league folder (`profile.toml`, or a
  `profile_rules` list in `league.ini`); there is no override.
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

Open: revisit `edit`/`copy` options.

## scheduler — `generate-schedule`

Working. Docs: [README](docs/scheduler/README.md) ·
[phase 1](docs/scheduler/phase-1-matchups.md) ·
[phase 2](docs/scheduler/phase-2-schedule.md)

- `solver_workers = "auto"` is the default: the CPU's fast threads (P-cores
  on Intel hybrid CPUs) minus 2. A benchmark on an i5-14600KF found 8-12
  threads fastest and 18-24 slower. The report shows the CPU, thread count and
  seed, so a schedule can be reproduced on another machine.
- League-agnostic: `--league NAME` picks the league; its standings are
  `standings\<season>.league.ini` and its rules `scheduler.toml` in the
  league folder. Conferences and divisions come from the standings file, the
  same-place games from the divisions, and the writers take the league name.
  No league or division name is left in scheduler code or tests; one validator
  and one test suite run every league. The PCFL ships in `leagues\PCFL\` in
  `config/dev/` and `config/release/`.
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
- league.ini simplified to `[DivisionStandings]` and `[OverallStandings]`.
- Golden integration test compares three output files byte for byte.
- Past PNFL seasons were re-ranked from real results using SOS tiebreaks, which
  gave each following season's `league.ini` standings and a real-schedule
  baseline to measure generated seasons against.
- Every run writes to a new timestamped folder, so nothing is overwritten and
  there is no backup to make.

Open: simplify the ruleset — 50 `[phase2]` keys, some redundant by
construction, never pruned · then the quirk budget in
[quirk-budget.md](docs/design/quirk-budget.md) · delete the obsolete
`TEST_DATA/scheduler_integration/` at the workspace root.

## Decisions

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
- **A bundled `.exe` still needs a real config folder.** Whatever ships can
  only carry a read-only template, so the editable config is written on first
  run.
- **STATUS carries no test counts.** They change every run.
- **The tools stay PNFL-specific.** playpool, gameplan and profile all lean on
  PNFL conventions, and making them fully league-agnostic would cost more than
  it is worth.
- **The CLI is Click.** CLI tests run through its `CliRunner`.
- **athc-admin ships the full installer.** Open to revisiting.
- **`uv` runs the project.** It handles Python, dependencies and the lockfile,
  in place of pip.
- **Config is `configparser`.** Pydantic was considered and dropped.
