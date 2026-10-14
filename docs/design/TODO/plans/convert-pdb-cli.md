# convert-pdb CLI plan

`athc convert-pdb` takes one PDB and an optional output (default `<name>.xlsm` beside the PDB), gains `--path`, `--team` and `--percentages/--no-percentages`, and drops `--skip-calcs`; the game plan behavior is in convert-pdb-behavior.md.

Depends on cli-help.md landing first.

## Decisions

- `PDB_FILE` stays required and positional, one per run; `OUTPUT_FILE` becomes optional.
- A bare `athc convert-pdb` is Click's `Missing argument 'PDB_FILE'.` usage error, exit 2.
- One PDB per run; several go through Windows' `for` loop, `for %f in (*.pdb) do athc convert-pdb "%f"`; COMMANDS.txt shows the loop.
- A second `.pdb` where `OUTPUT_FILE` goes is the normal extension error; a `*.pdb` that does not exist is the normal missing-file `FAIL` with Windows' phrase; no error carries the loop.
- The default output is the PDB's name with `.xlsm`, beside the PDB; a coach who wants plain `.xlsx`, or another place, names `OUTPUT_FILE`.
- The README and COMMANDS.txt say in one sentence that Excel opens the workbook with the macros disabled until Enable Content is clicked, and a copy sent by email opens with its macros blocked (unblock it in the file's Properties, or convert to `.xlsx` for sharing).
- An existing output file is replaced.
- `-` is not an output: the extension check refuses it; this is the exception to the cli-help.md rule that `-` means the console, noted in its derived-output rule.
- `OUTPUT_FILE` is a file, never a folder; a folder gets today's `must have a .xlsx or .xlsm extension.` error.
- A game plan option takes a `.pln` file only: `-o off1` is the `.pln` extension error, as today; a folder given is `named_file`'s `Access is denied.`, as today.
- With no game plan option, the team's plans come from three sources in a fixed order: `--path FOLDER` on the command line, else `ppp_path` in `league.toml`, else the league locations (`path` joined with the plan's `.lg2` folder).
- In a folder each plan is found by its `.lg2` file name without case, as check-ppp's folder mode does.
- `--path` means "where the game plans are" on every command that has it, and what is taken from there follows the command; convert-pdb takes a folder only and picks the team's four plans by their `.lg2` names.
- `--path` is an option, not a positional.
- `ppp_path` applies only when the team is the one `team` in `league.toml` resolves to: `--team` naming that team goes through it; `--team` naming another team, or `--team` with `team` unset or unresolvable, uses the league locations.
- The team is `team` in `league.toml`, `--team NAME` for one run: the `.lge`'s team name, nickname or both, matched without case, exactly one match.
- `--team` or `--path` with any game plan option is a usage error: `Error: --team cannot be used with -o, -o2, -d or -d2.` and `Error: --path cannot be used with -o, -o2, -d or -d2.`; with both flags the `--team` line shows (`--team` is checked first).
- `--league NAME` is never a contradiction: convert-pdb reads the league in every run, for `play_path`; a league that does not resolve is the league error, as everywhere.
- Each slot athc resolved from the league file is named as progress, one line per slot, path first: `<path>: Denver 1st-half offense, Slot 1`; when both slots of a side resolve to one file, one line, `<path>: Las Vegas offense, both halves, Slot 1`.
- A `.pln` path the coach typed gets no echo; the existing explicit-mode lines stay as they are.
- Config problems are `FAIL`, exit 2, each in check-ppp-cli.md's line: `team` set with no `path`, a `team` that matches no team or two, a bad or missing `.lg2` or `.lge`, two league files that disagree, `ppp_path` missing on disk.
- Each config line's tail names a way out that works for this command: the "No path" tail is `or pass a game plan with -o, -o2, -d or -d2.`; the "No team" line fires only when `--path` forced the team, and its tail is `or pass --team.`
- With nothing asked for, no team is silent.
- `--skip-calcs` becomes `--percentages/--no-percentages`, an on/off pair that overrides `calculate_percentages` in `athc.ini` both ways; neither given leaves the setting alone.
- The workbook shows the percentage columns when the run's value says so; the setting is the default, not a ceiling, so the `and` with it goes.
- `--skip-calcs` becomes `--percentages/--no-percentages`, as cli-help.md lists.
- New options: `--path FOLDER`, `--team NAME` and the `--percentages` pair; no `-a/--all-teams`, no `-r`, no quiet flag.
- `include_category_worksheets` and `exclude_sacks_from_pass_attempts` get no option.
- `include_category_worksheets` leaves the shipped `athc.ini` (`config/release/athc.ini` and `config/dev/athc.ini`) and keeps its code default `False`, so `test_release_convert_pdb_defaults` keeps passing.
- Setup order: usage, the named files, the league and its config, the team, the league files, the plans, the output folder, then the pool and the PDB.
- In detail: the named files (the PDB, the plans given as paths) first, as today; then the league, `play_path` and `pdbtoexcel.toml`; then `team` from `league.toml`, so a missing `team` shows before a missing `path`; then the `.lg2` and `.lge` from `path` and the team match; then the `--path` folder, the plans' lines and `WARN`s; then the output folder, the pool, the PDB, `Creating`, the notices, `OK`.
- A `--team` typo shows before the pool's `WARN` lines.
- The team resolver, the league-file loader and the file locator are shared code in `src/athc/cli/_team.py`, beside `_files.py`, imported by check-ppp, gameplan, profile and convert-pdb; check-ppp's behavior is unchanged.
- `team_option` is declared once in `src/athc/cli/__init__.py` beside `league_option`.
- The CLI loads the config; the tool takes it: `load_config` and `play_dir` move out of `main.convert_pdb()` into the command; `convert_pdb()` takes the tool's `Config`.
- The `[league]` keys (`team`, `path`, `ppp_path`) come from `load_league_config(league)`, called by the command as `check_ppp.py`'s `load_lg2` does; the tool's `Config` stays as it is.
- Usage errors get athc's period once, where they are rendered (the `ClickException` branch of `_OnePlace.main`), so every command prints `Got unexpected extra argument (x).`; check-ppp-cli.md's own raise for a third path becomes unnecessary.
- Help text: `[OPTIONS] PDB_FILE [OUTPUT_FILE]`, `GAME_PLAN` as the value name of the four plan options, `FOLDER` for `--path`, `NAME` for `--team` and `--league`, the summary "Convert a WinLogStats PDB to an Excel workbook.", the shared `--league` text; `-o`, `-o2`, `-d`, `-d2` keep their spelling.
- This plan describes the cli-help.md form only.

Modes, per run (with any game plan option, the files given fill their slots and nothing else is read; with none, the team's four plans are resolved from the league file):

| Game plan options | `--path` | Team | The plans come from | What is missing |
|---|---|---|---|---|
| one or more | none (`--path` and `--team` are usage errors) | not used | the files given; the slots not given hidden | `FAIL`, exit 2, as today |
| none | `FOLDER` | `team` or `--team` | that folder, by each plan's `.lg2` name without case | `WARN`, column hidden |
| none | none; `ppp_path` set and the team is `team`'s | your team | `ppp_path`, by the `.lg2` name without case | `WARN`, column hidden |
| none | none | `team` or `--team` | the league locations: `path` joined with the plan's `.lg2` folder | `WARN` with the `ppp_path` hint, column hidden |
| none | none | no `team`, no `--team` | nothing | the Slot columns hidden; no line |
| none | `FOLDER` | no `team`, no `--team` | nothing | `FAIL`: the "No team" line, tail `or pass --team.` |

- Output: `OUTPUT_FILE` as given, else `<PDB folder>\<PDB name>.xlsm`; its missing folders are created in full and an existing file is replaced, as today.
- Team mode: `team` is read from `league.toml`, then the `.lg2` and `.lge` from `path`; the team's four plan entries are taken in `.lg2` order; each plan is read before the pool, so its line or `WARN` comes first.
- `--path` must be an existing folder; the plans are looked up in it alone (no subfolders).

## Help

### athc convert-pdb

```
Usage: athc convert-pdb [OPTIONS] PDB_FILE [OUTPUT_FILE]

  Convert a WinLogStats PDB to an Excel workbook.

  Slot 1 and Slot 2 show where each play sits in your team's 1st- and 2nd-half
  game plans, per side; -o, -o2, -d and -d2 use the given game plans instead.

Positional arguments:
  PDB_FILE     WinLogStats .pdb file.
  OUTPUT_FILE  .xlsx, or .xlsm to include sorting macros (default: PDB_FILE
               with .xlsm, beside it).

Options:
  -o, --pln-off GAME_PLAN         Offense Slot 1.
  -o2, --pln-off-2 GAME_PLAN      Offense Slot 2.
  -d, --pln-def GAME_PLAN         Defense Slot 1.
  -d2, --pln-def-2 GAME_PLAN      Defense Slot 2.
  --path FOLDER                   Folder holding your team's game plans, by
                                  their league-file names (default: ppp_path,
                                  else where the game reads them).
  --team NAME                     Team whose game plans fill the Slot columns
                                  (default: team in league.toml).
  --percentages / --no-percentages
                                  Overrides calculate_percentages in athc.ini
                                  (on by default).
  --league NAME                   League to use (default: the one set with
                                  athc config set league).
  -h, --help                      Show this message and exit.

  Examples:

    athc convert-pdb 49W6.pdb
    athc convert-pdb 49W6.pdb reports\week6.xlsx -o try3.pln
```

## Settings

In `league.toml`, under `[league]`, the keys check-ppp-cli.md adds, with its `path` and `team` comment text:

```toml
# The folder that holds this league's files (PNFL.lg2, PNFL.lge and the rest).
path = 'C:\SIERRA\FBPRO98'
# Your team: its name or nickname in the league (Denver, Broncos).
team = 'Denver'
# Optional: where you keep your profiles and game plans, when it is not where
# the league file puts them. A relative path is under this league folder.
# ppp_path = 'D:\PNFL\Denver'
```

In `athc.ini`, `[convert-pdb]` loses `include_category_worksheets`; the comment on `calculate_percentages` names the new pair:

```ini
[convert-pdb]
; add the percentage columns (--percentages / --no-percentages override this
; for one run)
calculate_percentages = true
; leave sacks out of pass attempts
exclude_sacks_from_pass_attempts = false
```

- `play_path`, the category labels and `pdbtoexcel.toml` are read as today, in every mode, by the command before the team; there is no `playpool.toml`.
- `team` is read whenever no game plan option is given; `path` when a team is in play (its `.lg2` and `.lge`); `ppp_path` when the team is `team`'s and no `--path` is given; any game plan option reads none of the three.
- `include_category_worksheets` keeps its code default and gets no option.
- Shipped files: the comments above in `config/release/leagues/PNFL` and `PCFL` and the `[convert-pdb]` section of `config/release/athc.ini` and `config/dev/athc.ini`; the dev PNFL sets `team = 'Denver'`.

## Lines and exit codes

| When | Line | Code |
|---|---|---|
| no `PDB_FILE` | `Error: Missing argument 'PDB_FILE'.` (Click's, after its `Usage:` and `Try 'athc convert-pdb --help' for help.` lines) | 2 |
| `PDB_FILE` not `.pdb` | `Error: Invalid value for 'PDB_FILE': must have a .pdb extension.` | 2 |
| `OUTPUT_FILE` not `.xlsx`/`.xlsm` (`-`, a folder, a second `.pdb`) | `Error: Invalid value for 'OUTPUT_FILE': must have a .xlsx or .xlsm extension.` | 2 |
| a plan option not `.pln` (`off1` included) | `Error: Invalid value for '-o' / '--pln-off': must have a .pln extension.` (today's text; Click joins the option's names with ` / `) | 2 |
| a third positional | `Error: Got unexpected extra argument (<x>).` (Click's text, athc's period) | 2 |
| `--team` with any game plan option (with or without `--path`) | `Error: --team cannot be used with -o, -o2, -d or -d2.` | 2 |
| `--path` with any game plan option, no `--team` | `Error: --path cannot be used with -o, -o2, -d or -d2.` | 2 |
| `--skip-calcs` | `Error: No such option '--skip-calcs'.` (Click's) | 2 |
| a PDB (a `*.pdb` included) or a named plan that does not exist | `FAIL <path>: The system cannot find the file specified.` (today's) | 2 |
| a PDB or a named plan that is a folder | `Access is denied.` in the same `FAIL <path>:` line (today's) | 2 |
| `play_path` or `pdbtoexcel.toml` missing | a `FAIL` naming the file (today's) | 2 |
| `--path` folder missing | `FAIL <folder>: The system cannot find the path specified.` | 2 |
| `--path` names a file | `FAIL <folder>: The directory name is invalid.` | 2 |
| `--path` given, no `team`, no `--team` | `FAIL <league.toml>: Team is not set. Run 'athc config set team NAME' or pass --team.` | 2 |
| a team in play, no `path` | `FAIL <league.toml>: League files folder is not set. Run 'athc config set path FOLDER' or pass a game plan with -o, -o2, -d or -d2.` | 2 |
| `team` matches no team or two teams; `team` is an array; `--team` matches no team or two; `.lge` missing or bad; the league files disagree; `ppp_path` missing on disk or a file | check-ppp-cli.md's lines, unchanged | 2 |
| a named plan on the wrong side | `FAIL <path>: Not an offense game plan.` (`Not a defense game plan.` under `-d`/`-d2`) | 2 |
| `OUTPUT_FILE`'s folder is a file | `FAIL <folder>: Cannot create a file when that file already exists.` (today's) | 2 |
| the output still open in Excel | `FAIL <output>: The process cannot access the file because it is being used by another process.` (today's) | 2 |
| a defaulted plan missing, in `--path` or `ppp_path` | `WARN <path>: The system cannot find the file specified. Offense Slot 2 is hidden.` | 0 |
| a defaulted plan missing, at the league locations | `WARN <path>: The system cannot find the file specified. Offense Slot 2 is hidden. Run 'athc config set ppp_path FOLDER' or pass --path.` | 0 |
| a shared plan missing, both slots resolved | one line: `WARN <path>: The system cannot find the file specified. Offense Slot 1 is hidden.` (Slot 2 is hidden with it) | 0 |
| none of the team's plans in the folder (`--path`, `ppp_path`) | `WARN <folder>: No Denver game plans. The league file names DEN-OGP1.pln, DEN-DGP1.pln, DEN-OGP2.pln, DEN-DGP2.pln.` (each name once, as gameplan and check-ppp print it) | 0 |
| none of the team's plans at a league location, folder present | `WARN <folder>: No Denver game plans. Run 'athc config set ppp_path FOLDER' or pass --path.` | 0 |
| none of the team's plans at a league location, folder absent | `WARN <folder>: The system cannot find the path specified. Run 'athc config set ppp_path FOLDER' or pass --path.` | 0 |
| a defaulted plan unreadable | `WARN <path>: <the game plan library's reason> Offense Slot 2 is hidden.` | 0 |
| a defaulted plan on the wrong side | `WARN <path>: Not an offense game plan. Offense Slot 1 is hidden.` | 0 |
| a resolved slot in use | `<path>: Denver 1st-half offense, Slot 1` (progress, stderr, logged) | |
| both slots of a side resolved to one file | `<path>: Las Vegas offense, both halves, Slot 1` | |
| the workbook started | `Creating '<output>'` (progress, stderr, today's) | |
| a notice: a play with no play file, a stale deleted play, bad PDB data, a pool issue (no rules file, no rules notice) | a `WARN` per notice (today's) | 0 |
| the workbook written | `OK   <output>: <n> play(s)`, as today; with the default output, the derived path | 0 |

- Usage errors are Click's: the usage line, `Try 'athc convert-pdb --help' for help.` and `Error: <message>`, with athc's period added once where usage errors are rendered.
- Order of output: config and team `FAIL`s (nothing else prints); the resolved slots' lines and `WARN`s in `.lg2` order; `Creating '<output>'`; the pool, PDB and workbook `WARN`s as today; the `OK` line.
- The team label is the `.lge` team name (`Denver`), whichever form `team` or `--team` used, as in check-ppp.
- The "No <Team> game plans" lines cover every Slot column of that side or team at once: a team folder with nothing in it is one line, not four.
- No team with nothing asked for prints no line.
- A `WARN` never changes the code; the plan `WARN`s come before `Creating`.
- Codes: 0 done (warnings included), 2 error or usage; convert-pdb never exits 1.

## Files to change

- `src/athc/cli/convert_pdb.py`: the arguments renamed `pdb_file` and `output_file` (today `pdbfile`, `outputfile`), neither with an explicit metavar, so Click renders `PDB_FILE` and `[OUTPUT_FILE]` in the usage line; `output_file` is `required=False` and the derived default is built after `named_file` accepts the PDB (`pdb.with_suffix(".xlsm")`); `_ext` raises `BadParameter(..., param_hint="'OUTPUT_FILE'")` for the optional argument, so the error reads `'OUTPUT_FILE'`, not `'[OUTPUT_FILE]'`; `metavar="GAME_PLAN"` on the four plan options, each with Click `default=None` and today's `.pln` extension callback; `--path FOLDER`; `team_option` and `league_option` from `athc.cli`; `--percentages/--no-percentages` with `default=None` in place of `--skip-calcs`; the two `UsageError`s when any plan option is given, `--team` checked first; the command loads the tool config (`load_config(league)`, `play_dir`) and the `[league]` keys (`load_league_config(league)`, as `check_ppp.py`'s `load_lg2` does), then, when no plan option is given, resolves the team through `_team.py` (`--team`, else `team` from the `LeagueConfig`; the "No team" line with its `--team` tail when neither), loads the league files (`load_league_files`; the "No path" line and its tail when `path` is unset), takes the team's four plans (`team_files(team, "gameplan")`), locates each (`locate(file, ppp_path, league_path)`, or the `--path` folder) and prints the progress lines.
- `src/athc/cli/__init__.py`: `team_option` beside `league_option`: `--team NAME`, help "Team whose game plans fill the Slot columns (default: team in league.toml)." here, the head per command; in `_OnePlace.main`'s `except click.ClickException` branch, a `UsageError` whose message has no trailing period gets one before `error.show()`, so no command raises its own copy.
- `src/athc/cli/_team.py` (new; contents as gameplan-cli.md decides): `TEAM_FILE_NAMES = ("off1", "def1", "off2", "def2")`, `TEAM_KEY = "team"` and `PPP_PATH_KEY = "ppp_path"` (new), `LEAGUE_PATH_KEY` imported from `athc.config`; `load_league_files(league, league_dir)` (the `.lg2` with its stock check, then the `.lge`, then the team counts compared; check-ppp's `load_lg2` generalized); `resolve_team(name, lge)` (check-ppp's matcher and its two error lines); `team_files(team, kind)` (the four `(name, file)` pairs in `.lg2` order with a shared file repeated; callers that process files drop repeats by resolved path); `locate(file, ppp_path, league_path) -> Located(path, exists, source)` (the three sources, each file's existence decided before any read); `check_ppp.py` imports them.
- `src/athc/pdbtoexcel/main.py`: `convert_pdb(*, config: Config, pdb_path, output_path, pln_offense: GamePlan | None, pln_offense_2, pln_defense, pln_defense_2, percentages: bool | None)`; `load_config` and `play_dir` leave it; `percentages` falls back to `config.calculate_percentages` when `None`.
- `src/athc/pdbtoexcel/config.py`: unchanged.
- `src/athc/pdbtoexcel/excel_workbook.py`: `show_percentages = perform_calculations` (the setting is resolved in `main.py`).
- `src/athc/config.py`: `LeagueConfig.string(key)`, as check-ppp-cli.md plans; nothing else (`LEAGUE_PATH_KEY` is already there).
- `src/athc/fbpro98_lge/model.py`: nothing; `resolve_team` reads `LgeFile.teams`.
- `config/release/athc.ini`, `config/dev/athc.ini`: `include_category_worksheets` removed, the `calculate_percentages` comment.
- `config/release/leagues/*/league.toml`, `config/dev/leagues/*/league.toml`: the comments in Settings.

## Tests

- `tests/integration/test_convert_pdb.py`: the fixture PDB is copied to `tmp_path` wherever the default output would land beside it, so no run writes into `tests/integration/data/`; leagues come from the `tests/integration/conftest.py` fixtures `build_league`, `lg2_league` (a built `.lg2` and `.lge` with real team names beside `league.toml`, `path` and `team` set), `pnfl_league` (the real `tests/integration/data/PNFL.lg2` with a `PNFL.lge` beside it; Denver's four files, Las Vegas's one plan per side) and the `team()` entry builder.
- Output: one argument writes `<name>.xlsm` beside the PDB and the `OK` line names that path; an existing `<name>.xlsm` is replaced; a PDB given by a bare file name lands beside it in the current folder; `OUTPUT_FILE` given wins; `-`, a folder and a second `.pdb` as `OUTPUT_FILE` are the extension error, with no further sentence; a `*.pdb` that does not exist is the missing-file `FAIL`; no arguments is `Missing argument 'PDB_FILE'.` with the `'PDB_FILE'` hint; a third positional is Click's line with the period (the shared test lives in `test_cli_root.py`).
- Options: `-o2` and `-d2` accepted with a `.pln`, rejected with a `.txt` (the ` / ` hint); `-o off1` rejected with the same extension error; `--skip-calcs` rejected; `--percentages`/`--no-percentages` against `calculate_percentages = true` and `= false` (the setting alone, the setting overridden each way; the `%` headers present or absent, read back with openpyxl).
- Option limits: `--team` with no plan option accepted, with one plan option rejected (the usage error), and the same for `--path`; both flags with one plan option give the `--team` line.
- Team mode at the league locations: the four progress lines in `.lg2` order; a shared plan gives the "both halves" line.
- `--path FOLDER`: found by name without case; `--path` wins over `ppp_path`; a `--path` that does not exist and one that is a file are the two `FAIL`s; a subfolder is not searched.
- `ppp_path`: found by name without case; used for your team, skipped for `--team` naming another team; a relative `ppp_path`; `ppp_path` missing on disk and a file (check-ppp's lines).
- Team resolution: `--team` beats `team`; `--team` with `team` unset; a name, a nickname and both accepted; no match and two matches rejected (one run each; the resolver's full matrix is check-ppp's test file); no `team` and no `--team` with nothing asked for prints no plan line and hides the Slot columns; `--path` with no team is the "No team" line with the `--team` tail; a team in play with no `path` is the "No path" line with the four-options tail, and a missing `team` is reported before a missing `path`; the `.lge` missing; team counts off by one; the team error comes before the pool's `WARN`s.
- Existing tests that change: `test_requires_both_args` becomes the no-argument test; `test_bad_extension_is_a_sentence` expects `'PDB_FILE'`; `test_skip_calcs` becomes the `--percentages`/`--no-percentages` tests; `test_removed_options_are_rejected` gains `--skip-calcs`; `test_play_path_not_a_directory_is_a_config_error` calls `load_config` and `play_dir` the way the command does (`run_conversion` no longer loads the config); `test_workbook_matches_golden`, `test_progress_on_stderr_warnings_and_ok_line`, `test_entry_point_subprocess` and every `league`-fixture test keep passing (explicit plans or no team, explicit output).
- `tests/integration/test_cli_root.py`: the convert-pdb rows of `test_help_uses_lowercase_names` and `test_usage_lists_each_option` (`PDB_FILE [OUTPUT_FILE]`, `--pln-off GAME_PLAN`, `--path FOLDER`, `--team NAME`, `--percentages / --no-percentages`); `test_league_commands_take_league` changes from `--league name` to `--league NAME` for every league command; `test_long_usage_wraps_between_options` (built on convert-pdb's usage line, which no longer wraps under `[OPTIONS]`) goes with cli-help.md's switch to Click's own usage line, its `tests/integration/README.md` row too; one new test that a third positional on any command prints `Got unexpected extra argument (x).`
- `tests/integration/test_check_ppp.py`: its `league`, `lg2_league`, `team` and `pnfl_league` fixtures move to `tests/integration/conftest.py`; `league` becomes `build_league`, the others keep their names (main's `tests/integration/league_files.py` module rules out a `league_files` fixture); its tests use them; its third-path test asserts the shared period.
- `tests/unit/pdbtoexcel/test_workbook_creation.py`: `test_skip_calcs_omits_percent_columns` keeps passing (it passes `perform_calculations=False` to `__init__`).

## Docs and meta

- `docs/pdbtoexcel/README.md`: the Command section rewritten around the default output, `--path`, `--percentages/--no-percentages`, the lines and codes above, one sentence on `.xlsm` (Excel disables the macros until Enable Content is clicked, and a copy sent by email opens with them blocked; unblock it in the file's Properties, or make an `.xlsx`), and one sentence that `gameplan check` checks the plans convert-pdb reads while convert-pdb only reads their slots; the Config section names `path`, `team` and `ppp_path`.
- `docs/pdbtoexcel/ARCHITECTURE.md`: the CLI line; the Config section says the command loads the config; the exit-code table (1 for errors today) becomes 0 and 2.
- `docs/design/architecture.md`: Output files: "by default it lands next to its source (`list-normals` writes `<name>.normals.txt` beside the gameplan, `convert-pdb` writes `<name>.xlsm` beside the PDB)"; Config: `team` and `ppp_path` are read by check-ppp, gameplan, profile and convert-pdb; CLI: `team_option` beside `league_option`; Console and errors: Click usage errors end with athc's period, added in the one place.
- `docs/design/TODO/plans/cli-help.md`, convert-pdb ("cli-help.md changes"): usage `[OPTIONS] PDB_FILE [OUTPUT_FILE]`; OUTPUT_FILE help "`.xlsx`, or `.xlsm` to include sorting macros (default: PDB_FILE with .xlsm, beside it)."; `GAME_PLAN` as the value name of `-o`, `-o2`, `-d`, `-d2`, `.pln` files only; `--path FOLDER`; `--team NAME`; the description above; `test_long_usage_wraps_between_options` and `test_league_commands_take_league` added to its notes on Click's own usage line and the shared `--league` text.
- `docs/design/TODO/plans/check-ppp-cli.md`: amended as gameplan-cli.md lists (the `_team.py` move, `team_option`, the fixtures, the extra-argument period, the `league.toml` comment text and the rest); this plan adds nothing to that list.
- `docs/design/TODO/plans/autocontinue-cli.md`: its parenthetical that `convert-pdb --skip-calcs` can only turn the columns off now describes `--percentages/--no-percentages`.
- `docs/check_ppp/README.md`: the settings sentence names convert-pdb as another reader of `team`, `path` and `ppp_path`; `docs/gameplan/README.md`: nothing.
- `config/release/docs/COMMANDS.txt` section 13: the default output, `--path`, `--percentages/--no-percentages`, the `.xlsm` sentence, the examples below with the `for` loop.
- `config/release/docs/README.txt`: the settings list says `team` serves check-ppp, gameplan, profile and convert-pdb.
- `tests/integration/README.md`, `tests/unit/pdbtoexcel/README.md`: the convert-pdb rows above; the `--skip-calcs` row reworded.
- `CHANGELOG.md`, `STATUS.md`, `TODO.md` (the convert-pdb plan line, like check-ppp's; the `include_category_worksheets` item is ticked when this lands).

Examples for the docs:

```
athc convert-pdb 49W6.pdb
athc convert-pdb 49W6.pdb reports\week6.xlsx
athc convert-pdb 49W6.pdb --team Broncos
athc convert-pdb 49W6.pdb -o try3.pln -o2 plans\DEN-OGP1.pln
athc convert-pdb 49W5.pdb --path plans\wk5
athc convert-pdb 2045-2047.pdb --no-percentages --league PCFL
for %f in (*.pdb) do athc convert-pdb "%f"
```
