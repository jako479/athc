# generate-schedule

Generates a season schedule with OR-Tools, plus a companion sortable HTML report.

## Install

OR-Tools (the solver) is a required dependency, so any install includes it. For development:

```bash
uv pip install -e ".[dev]"
```

## Usage

```bash
athc generate-schedule --season 2048
athc generate-schedule --season 2048 --seed 7 --time-limit 600
```

`--season` is required and picks the config-dir input file (find the dir with `athc config path`): `<season>.league.ini`, which must include `[DivisionStandings]`. A missing file exits 1 with a clear message. It always writes a `.txt` and `.html` schedule plus a sortable HTML report to the **current directory**, named `schedule_<season>_<timestamp>` (report adds `_report.html`). Exit `0` = written, `1` = error, `2` = bad arguments.

Two-phase model: phase 1 builds the matchup inventory (divisional + conference games fixed by structure; division standings fix two non-conference games per team, NFL-style same-place matchups; CP-SAT picks the rest along a configurable conference-rank line covering the whole non-conference slate); phase 2 places those matchups into weeks via CP-SAT.

## Design

How the schedule is built, in three docs:

- [Phase 1 — fixed-place + CP-SAT matchups](phase-1-matchups-fixed-cpsat.md)
- [Phase 2 — schedule placement](phase-2-schedule.md)
- [Prior art — the current NFL formula](../design/research/nfl-formula.md) — background, not what athc uses
- [Research — NFL schedule patterns](../design/research/nfl-schedules.md) — provenance of the phase-2 rules
- [Research — CP-SAT rule design patterns](../design/research/cpsat-rule-patterns.md) — hard/soft rules, preventing solver anomalies

## Config

No `--config` flag — config is found via `ATHC_CONFIG_DIR` / the default config dir (see [../design/config.md](../design/config.md)):

- `rules/PNFL.scheduler.toml` — scheduler tunables (difficulty `spread`, solver `time_limit` / `solver_workers`, `[phase2]` rule amounts); **optional**, each key defaults when absent (invalid TOML/value is an error). `solver_workers` is a fixed reproducibility setting — same value everywhere or a seed's schedule changes. Installed but not advertised.
- `<season>.league.ini` (`[DivisionStandings]` per-division teams in finish order — this defines division membership — plus `[OverallStandings]` overall 1–18 `Order` list) — **required** league data, selected by `--season`. Both schedulers derive their 1–9 conference ranks from the overall order. A missing/invalid `[OverallStandings]` or `[DivisionStandings]` is an error.

## Tests

```bash
pytest                  # fast suite (solver tests excluded)
pytest -m slow          # solver tests only (long-running)
pytest -m ''            # everything
```

Solver-backed tests (any using a solved-schedule fixture) are marked `slow` and skipped by default.
