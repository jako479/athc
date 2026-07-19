# scheduler — Architecture

CLI tool that generates a PNFL season schedule using OR-Tools constraint programming, writes the result in the requested format (HTML or TXT), and emits a companion sortable HTML report.

## Module layout

```
src/athc/scheduler/                 # subsystem source
├── __init__.py
├── main.py                         # generate_schedule() orchestration
├── config.py                       # Config dataclass, load_config(), load_league()
├── domain/
│   ├── league.py                   # League, Conference, Division, Team
│   ├── schedule.py                 # Schedule, Game, Week
│   └── history.py                  # NonConfHistory — past inter-conference matchups
├── schedulers/
│   ├── schedule_builder.py         # CP-SAT model + constraints (phase 2, shared)
│   ├── fixed_cpsat_scheduler.py    # Scheduler C (fixed-place + CP-SAT) entry
│   ├── fixed_cpsat_builder.py      # phase-1 matchup solver (Scheduler C)
│   ├── fixed_cpsat_free_scheduler.py  # Scheduler D (free-only variant) entry
│   ├── fixed_cpsat_free_builder.py    # phase-1 matchup solver (Scheduler D)
│   ├── types.py                    # SchedulerFunc, SchedulerResult, A/B/C registry
│   └── errors.py
└── writers/
    ├── writer.py                   # ScheduleWriter protocol + factory
    ├── html_writer.py              # HTML output
    ├── txt_writer.py               # plain-text output
    └── report.py                   # HtmlReportWriter + build_schedule_report

src/athc/cli/generate_schedule.py   # Click command (lazy solver import)
```

## What this package does

- Provides a CLI: `athc generate-schedule --season YEAR [--seed INT] [--time-limit INT] [--scheduler C|D]`
- Loads league structure (conferences, divisions, teams) and rule weights from an INI config
- Loads the non-conference history file (past inter-conference pairings to penalize / avoid)
- Solves the schedule with the default Scheduler C (fixed-place + CP-SAT); Scheduler D (free-only variant) is also available
- Writes both a `.txt` and `.html` schedule to the current directory, named `schedule_<season>_<A|B|C|D>_<timestamp>` (`C` = fixed-place + CP-SAT, `D` = fixed-place + CP-SAT free-only)
- Writes a companion `<base>_report.html`: a sortable per-team strength-of-schedule table (ranks 1–9/1–18, SOS averages) plus run info (scheduler, seed, elapsed time, command line)

## What this package assumes

- The selected scheduler can solve within `time-limit`; if not, the partial / infeasible result surfaces via `SchedulerResult`

## What this package enforces

CLI-level (Click → exit 2):
- `--season` provided; `--time-limit` an integer; `--scheduler` a known name

Config (raise `ConfigError`) — found via `config_dir()` / `ATHC_CONFIG_DIR`, no `--config` flag:
- `<season>.league.ini` (`[Divisions]` + `[Standings]` overall 1–18) is **required** data, selected by the required `--season`. All schedulers use the overall order; Schedulers A and C derive their 1–9 conference ranks from it.
- `rules/PNFL.scheduler.toml` scheduler tunables (difficulty `spread`/`amplitude`, solver `time_limit`) are **optional** (each key defaults when absent); invalid TOML or a non-numeric value is an error. The difficulty curve drives Schedulers B and C.
- Invalid INI, or league data that fails domain validation, surfaces as a `ConfigError`

Domain (raise `ValueError`):
- Each conference has the expected number of divisions; each division the expected number of teams
- League invariants (e.g., team count, division balance) are validated at load time

Solver (`SchedulerResult.feasible == False`):
- Infeasible models surface a structured failure rather than a crash; the writer is skipped and the report records why

## What this package does NOT do

- Persist league or history changes — both inputs are read-only
- Produce stat workbooks (lives in `pdbtoexcel`) or play catalogs (lives in `playcatalog`)
- Run the generated schedule against any game engine

## Exit codes

| Exit | Meaning |
|---|---|
| `0` | **OK** — schedule (and report) written. |
| `1` | **Error** — config, I/O, or missing solver (ortools). |
| `2` | **Usage** — bad `--season` / `--scheduler` / `--time-limit` (Click). |

## Scheduler dispatch

`schedulers/types.py` is the single registry and the one place that defines what C and D are. Both share phase 2 (week placement); they differ only in phase 1 (non-conference matchup selection):

- **C — fixed-place + CP-SAT** (default) — phase 1 fixes two non-conference games per team by division place (NFL-style same-place matchups, from the league file's `[DivisionStandings]`; 5ths play each other), then one CP-SAT solve picks the rest along the configurable `c_spread` line.
- **D — fixed-place + CP-SAT, free-only** — like C, but the line (`d_spread`) targets only the picked games; the fixed games don't count toward it.

Each scheduler's `generate_schedule` matches the `SchedulerFunc` signature and returns a `SchedulerResult` with the schedule and the matchup plan.

## Testing

Under `tests/unit/scheduler/`:

- shared — `test_cli` / `test_config` (CLI + config/league/history loading; matrix in [test-matrix-config-loading.md](../../tests/unit/scheduler/test-matrix-config-loading.md)), `test_schedule_builder` (phase-2 placement), `test_history_costs`, `test_report` (HTML report; matrix in [test-matrix-report.md](../../tests/unit/scheduler/test-matrix-report.md)), `test_writers`.
- `fixed_cpsat/` (Scheduler C) — `test_fixed_cpsat_inventory` (phase-1) plus `test_schedule_structure` / `test_schedule_rules` (end-to-end, solved with Scheduler C).
- `fixed_cpsat_free/` (Scheduler D) — same shape, solved with Scheduler D.

Each scheduler folder solves end-to-end, so the placement rules are validated against all three schedulers. Solver-backed tests (any using a solved-schedule fixture) are marked `slow` and skipped by default; run them with `pytest -m slow`. League-parametrized tests use three ranking variants (`5/6/7-free-slots`) spanning the playoff-distribution splits — the 4-team division supplying 1, 2, or 3 of its conference's 4 playoff teams (Schedulers B and C use overall rank, A the derived conference rank, not playoffs).
