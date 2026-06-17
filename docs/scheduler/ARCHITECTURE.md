# scheduler — Architecture

CLI tool that generates a PNFL season schedule using OR-Tools constraint programming, writes the result in the requested format (HTML or TXT), and emits a companion human-readable report.

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
│   ├── scheduler.py                # two-phase-rank scheduler (matchups → weeks)
│   ├── schedule_builder.py         # CP-SAT model + constraints
│   ├── matchup_builder.py          # phase-one matchup solver (two-phase-rank)
│   ├── fixed_matchup_scheduler.py  # fixed-matchup scheduler (matchups → weeks)
│   ├── fixed_matchup_builder.py    # phase-one matchup solver (fixed-matchup)
│   ├── types.py                    # SchedulerFunc, SchedulerResult, registry
│   └── errors.py
└── writers/
    ├── writer.py                   # ScheduleWriter protocol + factory
    ├── html_writer.py              # HTML output
    ├── txt_writer.py               # plain-text output
    └── report.py                   # TxtReportWriter + build_schedule_report

src/athc/cli/generate_schedule.py   # Click command (lazy solver import)
```

## What this package does

- Provides a CLI: `athc generate-schedule --output FILE --season YEAR [--format X] [--league FILE] [--history FILE] [--report FILE] [--seed INT] [--time-limit SECONDS] [--scheduler NAME]`
- Loads league structure (conferences, divisions, teams) and rule weights from an INI config
- Loads the non-conference history file (past inter-conference pairings to penalize / avoid)
- Solves the schedule with the default `two-phase-rank` scheduler (`fixed-matchup` remains available)
- Writes the schedule in the format inferred from the output extension (`.html` → HTML; `.txt` → text)
- Writes a companion `<output-stem>-report.txt` summarizing the run (matchup plan, constraint slack, seed, elapsed time, command line)

## What this package assumes

- The history file is consistent with the league structure (every team referenced is a known team)
- The selected scheduler can solve within `time-limit`; if not, the partial / infeasible result surfaces via `SchedulerResult`

## What this package enforces

CLI-level (Click → exit 2):
- `--output` and `--season` provided
- output format resolves to `htm`/`html`/`txt`

Config (raise `ConfigError`) — found via `config_dir()` / `ATHC_CONFIG_DIR`, no `--config` flag:
- `league.ini` (`[Divisions]` + `[Standings]` overall 1–18 and/or `[ConferenceRanking]` AFC/NFC 1–9) is **required** data
- `rules/PNFL.scheduler.toml` scheduler tunables (difficulty `spread`/`shape`, solver `time_limit`) are **optional** (each key defaults when absent); invalid TOML or a non-numeric value is an error
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

## Scheduler dispatch

Schedulers register themselves in `schedulers/types.py`. Registered:

- `two-phase-rank` (default) — phase one chooses all non-conference matchups together by overall 1–18 rank, shaped toward a soft difficulty curve (minimax); phase two assigns each matchup to a week.
- `fixed-matchup` — phase one builds the matchup inventory from divisional/conference rules, a fixed non-conference rank table, and history; phase two assigns each matchup to a week.

`generate_schedule` matches the `SchedulerFunc` signature and returns a `SchedulerResult` with the schedule and the matchup plan.

## Testing

Under `tests/unit/scheduler/`:

- shared — `test_cli` / `test_config` (CLI + config), `test_schedule_builder` (phase-2 placement), `test_history_costs`, `test_report`, `test_writers`.
- `two_phase_rank/` (new scheduler) — `test_matchup_builder` (rank-only phase-1) plus `test_schedule_structure` / `test_schedule_rules` (end-to-end, solved with two-phase-rank).
- `fixed_matchup/` (old scheduler) — `test_fixed_matchup_inventory` (phase-1) plus `test_schedule_structure` / `test_schedule_rules` (end-to-end, solved with fixed-matchup).

Each scheduler folder solves end-to-end, so the placement rules are validated against both schedulers. Solver-backed tests (any using a solved-schedule fixture) are marked `slow` and skipped by default; run them with `pytest -m slow`. League-parametrized tests use three ranking variants (`5/6/7-free-slots`) spanning the playoff-distribution splits — the 4-team division supplying 1, 2, or 3 of its conference's 4 playoff teams (the new scheduler uses overall rank, the old derived conference rank, not playoffs).
