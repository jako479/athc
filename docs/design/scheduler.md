# generate-schedule

Generates a league's season schedule with OR-Tools, plus a companion sortable HTML report.

Usage, options, the standings, teams that moved, league shapes, lines and exit codes: [usage/generate-schedule.txt](../usage/generate-schedule.txt).

## Install

OR-Tools (the solver) is a required dependency, so any install includes it. For development:

```bash
uv sync
```

## Design

- [Phase 1 — matchups](scheduler-phase-1-matchups.md)
- [Phase 2 — schedule placement](scheduler-phase-2-schedule.md)
- [Prior art — the current NFL formula](../research/nfl-formula.md) — background, not what athc uses
- [Research — NFL schedule patterns](../research/nfl-schedules.md) — provenance of the phase-2 rules
- [Research — CP-SAT rule design patterns](../research/cpsat-rule-patterns.md) — hard/soft rules, preventing solver anomalies

## Tests

```bash
pytest                  # fast suite (solver tests excluded)
pytest -m slow          # solver tests only (long-running)
pytest -m ''            # everything
```

One test suite runs every league: two divisional standings variants and the conference league. The league-file loader is tested on the PNFL's real 2046-2048 files. Solver-backed tests are `slow` and skipped by default.

## How it works

Two phases, both CP-SAT: phase 1 picks every matchup, phase 2 places them into weeks. The same code serves every league: the upcoming season's league file gives the structure, the previous season's the standings, the rules file the amounts. Phase 1, league by league:

### PNFL

Two conferences of nine, each with a 4-team and a 5-team division; 16 games a team.

1. **Divisional:** each team plays its division rivals twice, home and away.
2. **Conference:** each team plays the rest of its conference once.
3. **Non-conference:** the other 4 games (a 5-team division) or 5 (a 4-team division).
   1. **Same place:** each team plays the teams that finished in its place in the other conference's two divisions ([the standings](#the-standings) give the places); the two 5th places play each other.
   2. **Difficulty:** the solver picks the rest so that the conference ranks (1-9) of each team's non-conference opponents add up close to a target: hardest for the best team, easiest for the worst.

`difficulty_slope` (`[phase1]`, 2.5) sets how steep that target is from the best team to the worst. At 0 it is flat: every team's opponents average rank 5. At 2.5 the #1 team aims at ranks 1-4, a sum of 10. The slope covers 4 games, the fewest any team has; a 5th game adds an average opponent (rank 5), so a #1 team in a 4-team division aims at 15.

### PCFL

Two conferences of nine, no divisions; 12 games a team.

1. **Conference:** each team plays every conference team once (8 games).
2. **Non-conference:** the other 4 games.
   1. **Rivalry:** the two teams left over from the in-conference rivalries play each other, in the final week (rivalry week).
   2. **Difficulty:** the solver picks the rest, as in the PNFL.

`difficulty_slope` (`[phase1]`, 0.0) makes the target flat: every team's 4 opponents add up near 20, an average rank of 5. `random_nonconference` (`[phase1]`, off) picks the non-conference games at random from the run's seed instead: the rivalry stays, and the slope is ignored.

### Module layout

```
src/athc/scheduler/                 # subsystem source
├── __init__.py
├── main.py                         # generate_schedule() orchestration
├── config.py                       # SchedulerConfig, load_scheduler_config() ([renames] included), rules path
├── league_files.py                 # load_league(): the League from the previous and upcoming .lge files
├── cpu.py                          # this CPU's name and fast threads (Windows), for solver_workers = "auto"
├── domain/
│   ├── league.py                   # League, Conference, Division, Team; build_league()
│   └── schedule.py                 # Schedule, Game
├── schedulers/
│   ├── scheduler.py                # the scheduler entry: phase 1 then phase 2
│   ├── matchup_builder.py          # phase 1: MatchupBuilder (structure, same-place pairs, rivalries, CP-SAT line or random)
│   ├── schedule_builder.py         # phase 2: ScheduleBuilder (CP-SAT week placement)
│   ├── types.py                    # MatchupPlan, SchedulerResult, get_scheduler
│   ├── utils.py                    # make_solver, resolve_workers, run_solver, write_hold: the CP-SAT setup both phases share, and Ctrl+C
│   └── errors.py                   # SchedulerError
└── writers/
    ├── writer.py                   # ScheduleWriter protocol + factory
    ├── html_writer.py              # HTML schedule (titled by league)
    ├── txt_writer.py               # plain-text schedule
    └── report.py                   # HtmlReportWriter + build_schedule_report

src/athc/cli/generate_schedule.py   # Click command (lazy solver import)
```

### What this package does

- Provides a CLI: `athc generate-schedule [OPTIONS] [OUTPUT_FOLDER]`, with `--season YEAR` (required), `--previous FILE`, `--upcoming FILE`, `--seed NUMBER`, `--phase2-time-limit LIMIT` and `--league NAME`
- Resolves the league (`--league` → `[athc] league`) with the shared `athc.config.load_league_config`; `--upcoming` defaults to `<league>.lge` in the league's `path`, and `--previous` to the upcoming file
- Reads the previous season's `.lge` file (standings), then the upcoming season's (conferences, divisions, names), through `fbpro98_lge`, matches the teams by name with `[renames.<season>]` (none when one file gives both), ranks the previous season and builds the `League` (`league_files.py`); loads `scheduler.toml` (optional amounts and the renames) from the league's folder first
- Solves the schedule in two CP-SAT phases
- Writes `schedule_<season>_<timestamp>.txt` / `.html` and `_report.html` to `OUTPUT_FOLDER` (default: the current folder; created in full if missing), titled by league

### What this package enforces

CLI-level (Click → exit 2):
- `--season` provided; `--seed` an integer from 0 to 2147483647 (`must be 0 to 2147483647, got -1.`); `--phase2-time-limit` an integer of 1 or more (`must be 1 or more, got 0.`). The bounds are athc callbacks raising Click's `BadParameter`, so a non-integer keeps Click's `is not a valid integer.`

Config (`ConfigFileError`, `LeagueError` → `FAIL`, exit 2) — found via `config_dir()` / `ATHC_CONFIG_DIR`, no `--config` flag:
- The league (`--league`, else `[athc] league`) must have a folder `leagues\<NAME>\`; without `--upcoming`, its `league.toml` must set `path`, else `League files folder is not set. Run 'athc config set path FOLDER' or pass --upcoming.`
- `leagues\<NAME>\scheduler.toml` is **optional**; every key defaults; invalid TOML, a bad value, an unknown table, or an unknown key in `[league]`, `[solver]`, `[phase1]`, `[phase2]` or `[rivalries]` is an error. `[solver] phase1_time_limit` and `phase2_time_limit` must be positive numbers (`Must be a positive number.`). `[renames.<season>]` keys are season years, values team names; a rename must name a previous-season team and an upcoming-season team, and not a name another previous-season team keeps.
- League-resolved rules: `weeks` must fit the league, `opening_nonconference_weeks` must leave room for every same-conference game, `[rivalries]` must name every team once with exactly one cross-conference pair.

League files (`OSError`, `InvalidLgeError`, `SchedulerError` → `FAIL`, exit 2), each line naming the file:
- Both `.lge` files must exist and parse; a missing one is Windows' own phrase.
- An unfinished previous season is a `WARN`, not an error: `Season not finished. N game(s) not played.`, and the standings come from the games played.
- A team name must not repeat in a file; every previous-season team must match an upcoming one by (renamed) name and vice versa (`Team(s) not in <file>: ...`, with the `[renames.<season>]` hint); no playoff game may be tied.

Domain (`ValueError`, surfaced as `SchedulerError` naming the upcoming file):
- Exactly two conferences of nine teams; no team twice; each division's finish lists exactly its members.

Solver (`SchedulerError` → `FAIL`, exit 2):
- No feasible inventory or schedule within the limits is a one-line error, not a traceback.

### The standings

`league_files.py` ranks the previous season: playoff finish (the last round's winner first, then its loser, then each earlier round's losers; a bye costs nothing), then win percentage, then strength of schedule (opponents' combined regular-season record as a win percentage), then the previous season's division finish (the team's place in the division it played in, ranked with `ranked` and the coin toss last), then point differential, then the coin toss. Each upcoming division's finish is its members ranked by the previous season with the lge library's `ranked` (the game's own order: win percentage, the manual's tie-breakers under the previous season's divisions, then the given order, which is the coin toss). The coin toss is one `random.Random(seed)` shuffle of the previous season's teams, drawn from the run's seed, so no file's team order breaks a tie and a seed reproduces its standings. A league whose conferences each hold one division is the conference-only shape. Conferences and divisions carry their file position as `number`: the identity and sort key, since the PNFL's conference names are empty and both conferences have an `East`. The same order is the standings library's `scheduler` method; the rules beside the game's and the NFL's: [standings-tie-breakers.md](../research/standings-tie-breakers.md).

### Exit codes

| Exit | Meaning |
|---|---|
| `0` | **Done** — schedule (and report) written. |
| `2` | **Error** — a `FAIL` line: league, config, no feasible schedule, I/O, or missing solver (ortools); or usage, bad `--season` / `--seed` / `--phase2-time-limit` (Click). |
| `130` | **Interrupted** — Ctrl+C, `FAIL Interrupted.`: nothing written, or all three files when pressed while they are written. |

The shared scheme: [architecture.md](architecture.md#console-run-log-and-errors).

### The scheduler

Two-phase CP-SAT. Phase 1 ([scheduler-phase-1-matchups.md](scheduler-phase-1-matchups.md)) builds the matchup inventory: structure fixes the same-conference games; the same-place rule (each division place plays the same place in every other-conference division that has that place) and any cross-conference rivalry fix some non-conference games; one CP-SAT solve picks the rest: each team's opponent conference ranks add up close to a target tilted by `difficulty_slope`, or with `random_nonconference` the picks are random from the seed. Phase 2 ([scheduler-phase-2-schedule.md](scheduler-phase-2-schedule.md)) places the inventory into weeks.

### Solver & reproducibility

Both phases run CP-SAT the same way, through one shared setup (`make_solver`): **interleave search** — parallel but reproducible. Two rules make a seed's matchups and schedule identical across runs and machines:

- **Same worker count.** Interleave results change with the number of workers, so both phases run one count from `solver_workers`: a number, or `"auto"` (the default) = this CPU's fast threads minus 2 — the threads on its highest-efficiency-class cores (the P-cores on Intel hybrid CPUs, every core on most AMD CPUs), from Windows' `GetLogicalProcessorInformationEx`. `"auto"` varies by machine, so the report shows the CPU and thread count; setting that number reproduces a seed anywhere. Not CLI-overridable.
- **Deterministic-time budget.** Each solve stops on its own limit — `phase1_time_limit` (default 120) for phase 1, `phase2_time_limit` (default 300) for phase 2 — measured in CP-SAT *deterministic time*, so a slow or fast machine reaches the same stopping point.

Also required: the model is built in canonical team order (never Python `set` iteration order). The model checksum test and the golden regression test guard both.

Ctrl+C: `make_solver` turns CP-SAT's own handling off (`catch_sigint_signal = False`). With it on, a press ends the process at once with no line: OR-Tools keeps its handler on the solving thread, and Windows runs the Ctrl+C handler on a thread of its own. With it off alone, Python hears the press only when the solve returns, up to the whole budget later. So both builders solve through `run_solver`, which installs a console control handler (`SetConsoleCtrlHandler`) for the length of the solve: a press calls `stop_search()`, and `KeyboardInterrupt` follows once the solve returns, which the one place prints as `FAIL Interrupted.`, exit 130. Outside a solve, Python's own handler does the same. The three output files are written inside `write_hold`, whose handler only records a press, so a press there takes effect once all three are written. The best schedule found so far is not kept.

### Testing

One suite in `tests/unit/scheduler/`, parametrized over every league case (two divisional standings variants, the conference league in an even season, an odd season, and with rotation off):

- `test_matchups` (phase 1; matrix in [test-matrix-phase-1-matchups.md](../../tests/unit/scheduler/test-matrix-phase-1-matchups.md)), `test_schedule_builder` (phase-2 model wiring), `test_utils` (the shared solver setup, the Ctrl+C solve and the write hold), `test_cpu` (fast-thread count and CPU name) and `test_schedule_rules` (every rule on a solved schedule, through the shared validator; matrix in [test-matrix-phase-2-schedule.md](../../tests/unit/scheduler/test-matrix-phase-2-schedule.md)).
- `test_cli` / `test_config` (CLI, the rules file and `[renames]`, every shipped `config/dev/` and `config/release/` rules file; matrix in [test-matrix-config-loading.md](../../tests/unit/scheduler/test-matrix-config-loading.md)), `test_league_files` (the League from two `.lge` files: the PNFL's real 2047 -> 2048 files reproduce the league's published 2048 order, 2046 -> 2047 covers a realignment with four renames, built `LgeFile`s cover every error and ranking rule), `test_league` (domain), `test_report` (matrix in [test-matrix-report.md](../../tests/unit/scheduler/test-matrix-report.md)), `test_writers`.
- `test_model_checksum` pins both CP-SAT models per league; re-pin only with that league's goldens.

The rule validator is `tests/integration/schedule_validation.py`: it checks every rule that applies to a league and its config, with every amount from the config and the league. The golden regression test ([tests/integration/test_generate_schedule.py](../../tests/integration/test_generate_schedule.py)) runs the CLI per league at a fixed seed, validates the output, and byte-compares the three files to the frozen goldens. The divisional case is the real 2048 PNFL season (`PNFL-2047-after-super-bowl.lge`, `PNFL-2048-after-week1.lge`); the conference case's league files are built by [tests/integration/league_files.py](../../tests/integration/league_files.py) from the test league's tables. Regenerate the built files and both golden sets with `python -m tests.integration.test_generate_schedule --bless`. Solver-backed tests are `slow`.
