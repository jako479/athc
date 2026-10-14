# generate-schedule CLI plan

Fits generate-schedule's help, options and lines to cli-help.md: both options take the `.lge` file, `--previous` is optional, `--seed` and `--time-limit` are bounded; the functional changes are in generate-schedule-behavior.md.

Depends on cli-help.md landing first.

## Decisions

- No coach runs it: it stays hidden from `athc --help`, `-h` keeps working on it, it stays out of COMMANDS.txt, and SCHEDULER-COMMANDS.txt stays its document.
- A leaf command named `generate-schedule`, no group.
- `--season YEAR` stays a required option; a bare command is Click's `Missing option '--season'.`, not reworded.
- No default season.
- `--previous FILE` takes the previous season's `.lge` file itself, saved after its last playoff game, and is optional; what happens without it is in generate-schedule-behavior.md.
- `--upcoming FILE` takes the upcoming season's `.lge` file itself and defaults to `<path>\<league>.lge`, `path` from `league.toml`; an explicit file overrides it.
- With neither `--upcoming` nor `path`: `FAIL <league.toml>: League files folder is not set. Run 'athc config set path FOLDER' or pass --upcoming.`
- That line is this command's own literal; check-ppp prints the same words from its own literal, ending in its own alternative (`--all-teams`).
- No season check on the files; a wrong-season `--previous` shows only through its names.
- The upcoming file may hold played games.
- A missing or broken league file keeps the read's own line, naming the file; no pre-check.
- The previous file is read first, then the upcoming, then the checks between them, in the code's order.
- `--seed NUMBER` takes 0 to 2147483647, checked by an athc callback raising Click's `BadParameter`; no seed draws one from 0 to 1,000,000, as today, and the result line shows it.
- `--time-limit LIMIT` stays an integer, now 1 or more, checked by a callback of the same shape, with no maximum, and keeps replacing `time_limit` (phase 2) only.
- The bounds use plain `int` and callbacks, not Click's `IntRange`: no range suffix after the help text, and a non-integer keeps Click's `is not a valid integer.`
- `[solver] time_limit` and `phase1_time_limit` in `scheduler.toml` must be positive numbers, one validator for both; `[difficulty] spread` stays as it is.
- Phase 1 keeps its own file key, `phase1_time_limit`, and no option.
- No `--workers` or other solver flag; `solver_workers` stays in `scheduler.toml` only.
- Inputs are the league folder's `scheduler.toml` and the two league files; no PATH, no team.
- `--league NAME` stays, with the shared help text.
- Output stays the current folder, the names stay `schedule_YEAR_DATE_TIME`, and a same-minute rerun replaces the files; no `-o`.
- No folder check before the solve.
- Lines and codes stay the project's: progress and `WARN` on stderr, `OK` per file and the tally line on stdout; exit 0 or 2, never 1, 130 on Ctrl+C.
- Setup order: arguments, league and its `league.toml`, league folder, the two files (`--upcoming`, else `<path>\<league>.lge`; `--previous`, else the upcoming file), `scheduler.toml`, the previous file, the upcoming file, the checks between them (the `Season not finished` `WARN` first), the cross checks, the solver, the files; the bound checks are Click callbacks and come first; `Missing ortools` shows after the files are read.
- Help follows cli-help.md: `[OPTIONS]`, `--season YEAR`, `--previous FILE`, `--upcoming FILE` (`FILE`, a `.lge` file), `--seed NUMBER`, `--time-limit LIMIT`, `--league NAME`, "folder", the solver's time units in plain words, a summary under 55 characters starting with a verb, a four-line description naming the options and the placeholders in caps, an Examples epilog.
- The description says "the league's .lge in path in league.toml" for the default upcoming file.
- The bounds are said in the error lines, in plain words, not in the help.
- The pointer to `athc config path` leaves the help; SCHEDULER-COMMANDS.txt keeps it.
- No check or preview mode.

## Help

### athc generate-schedule -h

```
Usage: athc generate-schedule [OPTIONS]

  Generate a league's season schedule and report.

  Reads the standings from --previous FILE (default: the --upcoming file) and
  the conferences, divisions and team names from --upcoming FILE (default: the
  league's .lge in path in league.toml), then writes a .txt and .html schedule
  plus an .html report to the current folder, named schedule_YEAR_DATE_TIME.

Options:
  --season YEAR       Season to schedule, e.g. 2048.  [required]
  --previous FILE     Previous season's .lge file, saved after its last
                      playoff game (default: the --upcoming file).
  --upcoming FILE     Upcoming season's .lge file (default: the league's .lge
                      in path in league.toml).
  --seed NUMBER       Seed for a repeatable run (default: random; the last
                      line shows it).
  --time-limit LIMIT  Solver budget for placing games into weeks, in the
                      solver's own time units, not seconds (default:
                      time_limit in scheduler.toml).
  --league NAME       League to use (default: the one set with athc config set
                      league).
  -h, --help          Show this message and exit.

  Examples:

    athc generate-schedule --season 2050 --previous E:\PNFL\2049\PNFL.lge
    athc generate-schedule --season 2030 --league PCFL --previous PCFL.lge
```

### Examples for the docs

```
athc generate-schedule --season 2050 --previous E:\PNFL\2049\PNFL.lge
athc generate-schedule --season 2050 --previous E:\PNFL\2049\PNFL.lge --seed 7
athc generate-schedule --season 2030 --league PCFL --previous D:\PCFL\2029\PCFL.lge --upcoming D:\PCFL\2030\PCFL.lge
athc generate-schedule --season 2050 --previous E:\PNFL\2049\PNFL.lge --time-limit 900
```

## Inputs

| Input | Where | Needed | Missing or wrong |
|---|---|---|---|
| the previous season's `.lge` | `--previous FILE`, else the upcoming file | no, the upcoming file stands in | absent folder or file: Windows' phrase naming the file; broken: the lge library's line; unfinished: the `WARN` `Season not finished: <n> game(s) not played.`, then the run; a team with no upcoming match: `Team(s) not in <upcoming>: ... List renamed teams under [renames.YEAR] in <scheduler.toml>.` |
| the upcoming season's `.lge` | `--upcoming FILE`, else `<league>.lge` in `path` from `league.toml`, else the "League files folder is not set" line | yes | as above for absent or broken, and for unfinished when it gives the standings; a team with no previous match: `Team(s) not in <previous>: ...`; not two conferences of nine: the structure error naming it |
| `scheduler.toml` | the league folder | no, every key defaults | bad TOML or a bad value: `FAIL <file>: ...`, as today; a bad `[renames.YEAR]` entry: its line naming the table and key; `time_limit` or `phase1_time_limit` at 0 or below: the positive-number line |
| `league.toml`, `path` | the league folder | unless `--upcoming` | `FAIL <league.toml>: League files folder is not set. Run 'athc config set path FOLDER' or pass --upcoming.` |
| `athc.ini`, `[athc] league` | the config folder | unless `--league` | `FAIL League is not set. Run 'athc config set league NAME' or pass --league. Available: ...` |

## Settings

`athc.ini`:

```ini
[athc]
; league used when --league is not given; change it with
;   athc config set league NAME
league = PNFL
```

`leagues\PNFL\league.toml`, the key whose `<league>.lge` `--upcoming` defaults to (the one shared text for it):

```toml
[league]
# The folder that holds this league's files (PNFL.lg2, PNFL.lge and the rest).
path = 'C:\SIERRA\FBPRO98'
```

`leagues\PNFL\scheduler.toml`, the shipped lines for the one key the command line can replace for a run and for the renamed teams:

```toml
[solver]
time_limit = 600.0        # max deterministic time for the week-placement (phase-2) solve (multithreaded; not wall-clock seconds)

# Teams that changed their name between seasons, one table per upcoming season:
# previous name = "new name". generate-schedule matches the previous season's
# teams to the upcoming season's by name; a team not listed keeps its name.

[renames.2048]
Baltimore = "Los Angeles"
```

- `time_limit` and `phase1_time_limit` must be positive numbers; the shipped files already are, and their comments do not change.
- The previous season's file has no setting; `--previous FILE` names it, else the upcoming file gives the standings.
- `play_path`, `team` and `ppp_path` have no effect on this command.
- Nothing new is written to any settings file.

## Lines and exit codes

| When | Line | Code |
|---|---|---|
| bare `athc generate-schedule` | `Error: Missing option '--season'.` (Click) | 2 |
| `--season` without `--previous` | the run, with the standings from the `--upcoming` file | 0 |
| `--upcoming` with no value | `Error: Option '--upcoming' requires an argument.` (Click) | 2 |
| `--season abc` | `Error: Invalid value for '--season': 'abc' is not a valid integer.` (Click) | 2 |
| `--time-limit 1.5` | `Error: Invalid value for '--time-limit': '1.5' is not a valid integer.` (Click) | 2 |
| `--seed abc` | `Error: Invalid value for '--seed': 'abc' is not a valid integer.` (Click) | 2 |
| `--seed -1`, `--seed 2147483648` | `Error: Invalid value for '--seed': must be 0 to 2147483647, got -1.` (athc's callback in Click's frame) | 2 |
| `--time-limit 0` | `Error: Invalid value for '--time-limit': must be 1 or more, got 0.` (athc's callback in Click's frame) | 2 |
| an unknown option | `No such option '--workers'.` (Click) | 2 |
| no `--league`, no league set | `FAIL League is not set. Run 'athc config set league NAME' or pass --league. Available: ...` | 2 |
| no `--upcoming`, no `path` | `FAIL <league.toml>: League files folder is not set. Run 'athc config set path FOLDER' or pass --upcoming.` | 2 |
| a league file's folder is absent | `FAIL <folder>\PNFL.lge: The system cannot find the path specified.` | 2 |
| a league file is missing from a folder that exists | `... The system cannot find the file specified.` | 2 |
| a broken league file | the lge library's line, naming the file | 2 |
| unplayed games in the file that gives the standings (`--previous`, else `--upcoming`) | `WARN <file>: Season not finished: <n> game(s) not played.`, then the run with the games played | 0 |
| a team name repeats | `FAIL <file>: Team name repeats: <name>.` | 2 |
| a bad rename | `FAIL <scheduler.toml>: [renames.2048] <old>: Not a team in <file>.` or `... Another team in <previous> is named <new>.` | 2 |
| a previous team with no upcoming match | `FAIL <previous>: Team(s) not in <upcoming>: Baltimore. List renamed teams under [renames.2048] in <scheduler.toml>.` | 2 |
| an upcoming team with no previous match | `FAIL <upcoming>: Team(s) not in <previous>: <names>.` | 2 |
| a tied playoff game | `Playoff round 1: Tied game, <home> 10, <away> 10.` | 2 |
| not two conferences of nine | the `build_league` error naming the upcoming file | 2 |
| `[solver] time_limit` or `phase1_time_limit` at 0 or below | `FAIL <scheduler.toml>: [solver] time_limit: Must be a positive number.` | 2 |
| no feasible schedule | `CP-SAT returned status INFEASIBLE - no feasible schedule.` | 2 |
| broken install | `Missing ortools. Reinstall athc.` | 2 |
| a folder that refuses writes, when the files are written | `FAIL <file>: Access is denied.` | 2 |
| Ctrl+C during phase 1 or phase 2 | `FAIL Interrupted.`, the search stopped at the press, nothing written | 130 |
| Ctrl+C before phase 1's solve, between the phases, or while phase 2's model is built | `FAIL Interrupted.`, nothing written | 130 |
| Ctrl+C while the three files are written | the three files written, then `FAIL Interrupted.` | 130 |
| written | stderr: `Generating the <season> schedule`, `Phase 1: selecting matchups`, `Phase 2: placing games into weeks. This usually takes several minutes and can take 30 minutes or more.`; stdout: `OK   <file>` per file, then `Generated <n> games (seed <s>)` | 0 |

- Order of output: nothing until the two files and `scheduler.toml` are read, then the `Season not finished` `WARN`, if any; then the progress lines on stderr in the order the solve runs, then the three `OK   <file>` lines on stdout in the order written (`.txt`, `.html`, `_report.html`), then `Generated <n> games (seed <s>)`.
- An error stops the run at its line; nothing is written before the solve ends.
- The three output names share one minute stamp, and a file of the same name is replaced.

## Files to change

- `src/athc/cli/generate_schedule.py`: the summary, the description and the Examples epilog; the option help texts; metavars `YEAR`, `FILE`, `FILE`, `NUMBER` and `LIMIT`; `--seed` and `--time-limit` stay `type=int` and gain callbacks raising `click.BadParameter(f"must be 0 to 2147483647, got {value}.", ctx, param)` and `click.BadParameter(f"must be 1 or more, got {value}.", ctx, param)` (`None`, the no-value default, passes); `--previous` drops `required=True`; `_upcoming_dir` becomes the upcoming file, `--upcoming`, else `<path>\<league>.lge`, and its line becomes `League files folder is not set. Run 'athc config set path FOLDER' or pass --upcoming.`; `run_generate` gets the two files as `previous_file` and `upcoming_file`; `hidden=True`, the required `--season`, the random default, `Path.cwd()`, the `ImportError` wrap, the `OK` and result lines stay; the `[OPTIONS]` usage line and the `--league NAME` text come with cli-help.md's general fixes.
- `src/athc/scheduler/config.py`: a `_positive_number` beside `_number` for `[solver] time_limit` and `phase1_time_limit` (`Must be a positive number.`).
- `src/athc/scheduler/main.py`: `generate_schedule` takes `previous_file` and `upcoming_file` in place of the two folders.
- `src/athc/scheduler/league_files.py`: `load_league` takes the two file paths in place of the league and the two folders and reads each with `parse_lge(path.read_bytes(), path)`, the previous first.
- `scheduler.py`, the lge library and the writers: nothing (the progress lines stay).

## Tests

- `tests/unit/scheduler/test_cli.py` (the file's `folders` and `league_folder` fixtures, `run_generate` stubbed as the file does unless said otherwise): `--seed 0` and `--seed 2147483647` reach `run_generate` with that seed; `--seed -1` and `--seed 2147483648` exit 2 with `Error: Invalid value for '--seed': must be 0 to 2147483647, got -1.` (`got 2147483648.`) and never reach it.
- `tests/unit/scheduler/test_cli.py`: no `--seed`: the seed forwarded is within 0 to 1,000,000.
- `tests/unit/scheduler/test_cli.py`: `--time-limit 1` is forwarded; `--time-limit 0` exits 2 with `Error: Invalid value for '--time-limit': must be 1 or more, got 0.`
- `tests/unit/scheduler/test_cli.py`: a `--previous` file missing from a folder that exists: `FAIL <folder>\divisions.lge: The system cannot find the file specified.`
- `tests/unit/scheduler/test_config.py`: the positive-number validator, once, through `time_limit`: `1` accepted, `0` rejected with `[solver] time_limit: Must be a positive number.`; `phase1_time_limit` shares the validator.
- `tests/unit/scheduler/test_cli.py::test_errors_when_the_league_has_no_path`: the line becomes `League files folder is not set. Run 'athc config set path FOLDER' or pass --upcoming.`
- `tests/unit/scheduler/test_cli.py`: every `--previous` names the file (`_lge(previous)`), `_run_main` passes the files, and the captured `previous_dir` and `upcoming_dir` become `previous_file` and `upcoming_file` (`test_league_and_season_resolve_files_and_output_to_cwd`, `test_upcoming_option_overrides_the_league_path`, `test_season_resolves_files_for_the_configured_league`).
- `tests/unit/scheduler/test_cli.py`: `test_errors_when_previous_file_missing` and `test_cli_errors_when_a_renamed_team_is_not_listed` pass the file and keep their lines.
- `tests/unit/scheduler/test_league_files.py`: `_folders`, `_load`, `_build` and the `load_league` calls pass the files.
- `tests/integration/league_files.py` (`write_league_files`, `case_league`) and `tests/integration/test_generate_schedule.py` (`_generate`, `test_conference_league_files_reproduce_the_test_league`): the files in place of the folders.
- `tests/integration/test_cli_root.py::test_help_uses_lowercase_names`, the generate-schedule row: `--season YEAR`, `--previous FILE`, `--upcoming FILE`, `--seed NUMBER`, `--time-limit LIMIT`; `INTEGER` stays hidden.
- `tests/integration/test_cli_root.py::test_usage_lists_each_option`, the generate-schedule row: `athc generate-schedule [OPTIONS]`, with cli-help.md.
- `tests/integration/test_cli_root.py::test_league_flag_reaches_the_command`: passes `--previous <tmp_path>` and fails on the league first, as today.
- Keep passing unchanged: `test_requires_season`, `test_rejects_non_integer_time_limit` (exit 2 only), `test_no_worker_count_override`, `test_errors_on_oserror`, `tests/unit/scheduler/test_matchups.py::test_scheduler_says_both_phases_through_progress`.

## Docs and meta

- `docs/scheduler/README.md`: Usage with the new help's wording, `--previous FILE` and `--upcoming FILE` (the `.lge` file itself; `--upcoming` defaults to `<league>.lge` in `path`), the "League files folder is not set" line, the `--seed` bounds, `--time-limit` 1 or more and phase 2 only, the positive-number rule for the file's two limits, that a wrong-season `--previous` shows only through its names; "current directory" becomes "current folder".
- `docs/scheduler/ARCHITECTURE.md`: the usage line under "What this package does" becomes `athc generate-schedule [OPTIONS]` with the options named, and its `--upcoming` default and reading lines name the files; "What this package enforces", CLI-level, gains the two bounds and no longer requires `--previous`; Config gains the positive-number rule and the hint; "current directory" becomes "current folder".
- `config/release/docs/SCHEDULER-COMMANDS.txt`: the Options block in cli-help.md's placeholders with the new help texts and bounds, the two files and their defaults, the "League files folder is not set" line, the `league.toml` line naming the default upcoming file; the command stays out of COMMANDS.txt.
- cli-help.md, generate-schedule section: add `--previous FILE` and `--upcoming FILE` with the help texts above, the summary "Generate a league's season schedule and report.", the two bound error lines, the four-line description above and the Examples epilog.
- `docs/design/architecture.md`: nothing.
- `STATUS.md`, scheduler: the line saying every run writes to "a new timestamped folder, so nothing is overwritten" becomes "three files named to the minute in the current folder; a rerun in the same minute replaces them"; a line for the CLI changes.
- `CHANGELOG.md`: one line for the file options and the optional `--previous`, the hint and the bounds.
- `TODO.md`: the 1.0.0 generate-schedule item is ticked when this work lands.
- `tests/integration/README.md`: the `test_help_uses_lowercase_names` row with cli-help.md.
- `tests/unit/scheduler/test-matrix-config-loading.md`: rows for the new tests under "CLI" and "Scheduler rules".
