# scheduler — Architecture

CLI tool that generates a league's season schedule with OR-Tools constraint programming, writes it as `.txt` and `.html`, and emits a companion sortable HTML report. No league name or division name lives in the code: both come from the league's files.

## Module layout

```
src/athc/scheduler/                 # subsystem source
├── __init__.py
├── main.py                         # generate_schedule() orchestration
├── config.py                       # SchedulerConfig, load_scheduler_config(), load_league(), file resolution
├── domain/
│   ├── league.py                   # League, Conference, Division, Team; build_league()
│   └── schedule.py                 # Schedule, Game
├── schedulers/
│   ├── scheduler.py                # the scheduler entry: phase 1 then phase 2
│   ├── matchup_builder.py          # phase 1: MatchupBuilder (structure, same-place pairs, rivalries, CP-SAT line)
│   ├── schedule_builder.py         # phase 2: ScheduleBuilder (CP-SAT week placement)
│   ├── types.py                    # MatchupPlan, SchedulerResult, get_scheduler
│   ├── utils.py                    # make_solver: the CP-SAT solver setup both phases share
│   └── errors.py                   # SchedulerError
└── writers/
    ├── writer.py                   # ScheduleWriter protocol + factory
    ├── html_writer.py              # HTML schedule (titled by league)
    ├── txt_writer.py               # plain-text schedule
    └── report.py                   # HtmlReportWriter + build_schedule_report

src/athc/cli/generate_schedule.py   # Click command (lazy solver import)
```

## What this package does

- Provides a CLI: `athc [--league NAME] generate-schedule --season YEAR [--seed INT] [--time-limit INT]`
- Resolves the league (root `--league` → `ATHC_LEAGUE` → `[athc] league`) with the shared `athc.config.resolve_league`
- Loads `standings\<season>.league.ini` (the standings, which define conferences and divisions) and `rules\scheduler.toml` (optional amounts) from the league's folder
- Solves the schedule in two CP-SAT phases
- Writes `schedule_<season>_<timestamp>.txt` / `.html` and `_report.html` to the current directory, titled by league

## What this package enforces

CLI-level (Click → exit 2):
- `--season` provided; `--time-limit` an integer

Config (`ConfigError`, `LeagueError` → exit 1) — found via `config_dir()` / `ATHC_CONFIG_DIR`, no `--config` flag:
- The league (`--league`, else `[athc] league`) must have a folder `leagues\<NAME>\`.
- `leagues\<NAME>\standings\<season>.league.ini` is **required**: `[OverallStandings]` plus exactly one of `[DivisionStandings]` (keys `<CONFERENCE>_<DIVISION>`, division sizes from the file) or `[ConferenceStandings]` (two conferences of nine).
- `leagues\<NAME>\rules\scheduler.toml` is **optional**; every key defaults; invalid TOML or a bad value is an error.
- League-resolved rules: `weeks` must fit the league, `opening_nonconference_weeks` must leave room for every same-conference game, `[rivalries]` must name every team once with exactly one cross-conference pair.

Domain (`ValueError`, surfaced as `ConfigError`):
- Exactly two conferences of nine teams; no team twice; a division key names its conference.

Solver (`SchedulerError` → exit 1):
- No feasible inventory or schedule within the limits is a one-line error, not a traceback.

## Exit codes

| Exit | Meaning |
|---|---|
| `0` | **OK** — schedule (and report) written. |
| `1` | **Error** — league, config, no feasible schedule, I/O, or missing solver (ortools). |
| `2` | **Usage** — bad `--season` / `--time-limit` (Click). |

## The scheduler

Two-phase CP-SAT. Phase 1 ([phase-1-matchups.md](phase-1-matchups.md)) builds the matchup inventory: structure fixes the same-conference games; the same-place rule (each division place plays the same place in every other-conference division that has that place) and any cross-conference rivalry fix some non-conference games; one CP-SAT solve picks the rest along the `spread` line. Phase 2 ([phase-2-schedule.md](phase-2-schedule.md)) places the inventory into weeks.

## Solver & reproducibility

Both phases run CP-SAT the same way, through one shared setup (`make_solver`): **interleave search** — parallel but reproducible. Two rules make a seed's matchups and schedule identical across runs and machines:

- **Fixed worker count.** Interleave results change with the number of workers, so both phases use the pinned `solver_workers` setting (default 8), not the machine's core count, and it is not CLI-overridable.
- **Deterministic-time budget.** Each solve stops on its own limit — `phase1_time_limit` (default 120) for phase 1, `time_limit` (default 300) for phase 2 — measured in CP-SAT *deterministic time*, so a slow or fast machine reaches the same stopping point.

Also required: the model is built in canonical team order (never Python `set` iteration order). The model checksum test and the golden regression test guard both.

## Testing

One suite in `tests/unit/scheduler/`, parametrized over every league case (two divisional standings variants, the conference league in an even season, an odd season, and with rotation off):

- `test_matchups` (phase 1; matrix in [test-matrix-phase-1-matchups.md](../../tests/unit/scheduler/test-matrix-phase-1-matchups.md)), `test_schedule_builder` (phase-2 model wiring), `test_utils` (the shared solver setup) and `test_schedule_rules` (every rule on a solved schedule, through the shared validator; matrix in [test-matrix-phase-2-schedule.md](../../tests/unit/scheduler/test-matrix-phase-2-schedule.md)).
- `test_cli` / `test_config` (CLI, file resolution, standings and rules loading, every shipped `dev/` and `release/` file; matrix in [test-matrix-config-loading.md](../../tests/unit/scheduler/test-matrix-config-loading.md)), `test_league` (domain), `test_report` (matrix in [test-matrix-report.md](../../tests/unit/scheduler/test-matrix-report.md)), `test_writers`.
- `test_model_checksum` pins both CP-SAT models per league; re-pin only with that league's goldens.

The rule validator is `tests/integration/schedule_validation.py`: it checks every rule that applies to a league and its config, with every amount from the config and the league. The golden regression test ([tests/integration/test_generate_schedule.py](../../tests/integration/test_generate_schedule.py)) runs the CLI per league at a fixed seed, validates the output, and byte-compares the three files to the frozen goldens (regenerate both sets with `python -m tests.integration.test_generate_schedule --bless`). Solver-backed tests are `slow`.
