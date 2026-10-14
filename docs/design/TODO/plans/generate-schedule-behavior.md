# generate-schedule behavior plan

Changes what generate-schedule does: the standings without `--previous`, an unfinished season, division finish and a coin toss in the standings, and Ctrl+C; the help, options and lines are in generate-schedule-cli.md.

## Decisions

- Without `--previous`, the standings come from the `--upcoming` file, one file for both.
- Without `--previous`, `[renames.<season>]` is ignored.
- An unfinished season is a `WARN`, not a `FAIL`: `WARN <file>: Season not finished: <n> game(s) not played.`, and the run goes on with the games played; the `WARN` never changes the exit code.
- The `WARN` names the file that gives the standings: `--previous`, else `--upcoming`.
- A new league with no games played needs no rule of its own; the coin toss orders its teams.
- The last tiebreak, for the division finish and for the overall order, is a coin toss drawn from the run's seed.
- The overall order is playoff finish, regular-season win percentage, strength of schedule, the previous season's division finish, point differential, coin toss.
- The coin toss replaces the league file's team order; no file's order breaks a tie anywhere.
- Ctrl+C anywhere in the run is `FAIL Interrupted.`, exit 130, nothing written.
- CP-SAT's own Ctrl+C is turned off (`catch_sigint_signal = False`), and a console handler installed for each solve stops the search at the press.
- Outside a solve, Python's own handler gives the same `FAIL Interrupted.`, exit 130.
- The best schedule found so far is not kept.
- The phase-2 progress line stays as today.

## Files to change

- `src/athc/cli/generate_schedule.py`: the previous file is `--previous`, else the upcoming file; `run_generate` gets `warn=console.warn`, as autocontinue passes it.
- `src/athc/scheduler/main.py`: `generate_schedule` takes `warn` and passes it and the seed to `load_league`.
- `src/athc/scheduler/league_files.py`: `load_league` and `league_from_files` take the seed and `warn`; `league_from_files` says `<previous>: Season not finished: <n> game(s) not played.` through `warn` and goes on, instead of raising; one `random.Random(seed)` shuffle of the previous teams, the coin toss, replaces the previous-file order (`position`): it is the order each division's members go into `ranked` in, and the last key of the overall order, whose keys become playoff finish, win percentage, strength of schedule, division finish, point differential, coin toss.
- `src/athc/scheduler/schedulers/utils.py`: `make_solver` sets `solver.parameters.catch_sigint_signal = False`; a solve helper beside it takes the solver and the model, installs a console control handler through `ctypes` (`kernel32.SetConsoleCtrlHandler` with a `WINFUNCTYPE(c_bool, c_ulong)` routine that, for the Ctrl+C event, records the press, calls `solver.stop_search()` and returns true), calls `solver.solve(model)`, removes the handler, raises `KeyboardInterrupt` when the press was recorded, and otherwise returns the status.
- `src/athc/scheduler/schedulers/matchup_builder.py`: line 201 calls the solve helper instead of `solver.solve`; the `solver.value` reads (line 211) stay on the same solver.
- `src/athc/scheduler/schedulers/schedule_builder.py`: line 819 calls the solve helper instead of `solver.solve`; the `solver.value` reads (line 828) stay on the same solver.

## Tests

- `tests/unit/scheduler/test_cli.py`: no `--previous`: `run_generate` gets the upcoming file as both `previous_file` and `upcoming_file`; `--previous <file>`: that file as `previous_file` and the upcoming file as `upcoming_file`.
- No `--previous`, with a `[renames.<season>]` table for the season in `scheduler.toml`: the table is ignored.
- `tests/unit/scheduler/test_league_files.py`: the coin toss: with no game played, every team is level, so the overall order and each division's finish follow `random.Random(seed)`'s shuffle of the previous teams; the same seed gives the same order.
- `tests/unit/scheduler/test_league_files.py`: division finish in the overall order: two teams level on playoff finish, win percentage and strength of schedule rank by division finish, ahead of point differential.
- `tests/unit/scheduler/test_utils.py`: the solve helper with a stub solver whose `solve` records the console handler installed while it runs and whose `stop_search` records its call: a solve with no press returns the status and has removed the handler afterwards.
- `tests/unit/scheduler/test_utils.py`: invoking the installed routine with the Ctrl+C event during the stub's `solve` calls `stop_search`, makes the routine return true, and makes the helper raise `KeyboardInterrupt` once `solve` returns.
- `tests/unit/scheduler/test_utils.py`: another event (Ctrl+Break, the console closing) is not handled: the routine returns false and `stop_search` is not called.
- `tests/unit/scheduler/test_matchups.py` and `test_schedule_builder.py`: each builder's solve goes through the helper, checked with a pass-through spy in the shape of `_spy_on_solver` (records the call, then runs the real helper).
- The real Ctrl+C press stays a probe, not a test.
- `tests/unit/scheduler/test_utils.py::test_solver_is_configured_for_reproducible_parallel_search`: asserts `params.catch_sigint_signal is False` as well.
- `tests/unit/scheduler/test_cli.py::test_requires_previous` becomes the no-`--previous` case above.
- `tests/unit/scheduler/test_cli.py::test_cli_errors_when_the_previous_season_is_not_finished`: passes the upcoming file as `--previous`; stderr is `WARN <file>: Season not finished: 142 game(s) not played.` and, with the file's `_stub_solver`, the real `run_generate` reaches the solver stub.
- `tests/unit/scheduler/test_cli.py::test_main_errors_when_the_previous_season_is_not_finished`: `warn` hears the line and the run reaches the solver stub.
- `tests/unit/scheduler/test_league_files.py`: `_folders`, `_load`, `_build` and the `load_league` calls pass a seed and a `warn`.
- `tests/unit/scheduler/test_league_files.py::test_previous_season_must_be_finished` becomes the `WARN` case: `warn` hears the line, the League is built.
- `tests/unit/scheduler/test_league_files.py`: `test_one_division_per_conference_is_a_league_without_divisions`, `test_level_teams_keep_the_previous_file_order`, `test_level_division_members_keep_the_previous_file_order` and `test_playoff_finish_outranks_record` (its third place) expect the coin toss's order where the file order decided; the two `keep_the_previous_file_order` tests are renamed for the coin toss.
- `tests/integration/league_files.py` (`write_league_files`, `case_league`) and `tests/integration/test_generate_schedule.py` (`_generate`): the case's seed, so the coin toss matches the CLI run's; the slow golden test is never run here.
- These tests' expected orders may change with the coin-toss and division-finish tiebreaks and are updated with the change: `test_2048_league_matches_the_real_final_standings`, `test_2047_league_follows_realignment_and_renames`, `test_a_name_passed_along_a_chain_of_renames_is_accepted`, `test_conference_league_files_reproduce_the_test_league`, and the slow golden files.

## Docs and meta

- `docs/scheduler/README.md`: without `--previous`, the `--upcoming` file gives the standings; Ctrl+C (`FAIL Interrupted.`, 130, nothing written, the search stopped at the press); "The standings": an unfinished season is a `WARN` and the run goes on with the games played, the overall order (playoff finish, win percentage, strength of schedule, division finish, point differential, coin toss), and the coin toss from the run's seed in place of file order, in each division's finish too.
- `docs/scheduler/ARCHITECTURE.md`: League files' "must be finished" becomes the `WARN`; "The standings" gains division finish in the overall order and the coin toss from the seed in place of file order; the Exit codes table gains the `130` row (Ctrl+C, nothing written); "Solver & reproducibility" says `catch_sigint_signal` is off and why, and that a console handler stops the search on Ctrl+C.
- `config/release/docs/SCHEDULER-COMMANDS.txt`: the unfinished-season `WARN` in place of "must be finished", the overall order with division finish and the coin toss, Ctrl+C.
- `STATUS.md`, scheduler: a line for Ctrl+C.
- `CHANGELOG.md`: one line for the unfinished-season `WARN`, the coin toss and division finish in the standings, and Ctrl+C.
- `tests/unit/scheduler/test-matrix-config-loading.md`: rows for the new tests under "CLI" and "Scheduler rules".
