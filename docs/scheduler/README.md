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
athc generate-schedule --season 2048 --seed 7 --time-limit 600 --scheduler D
athc generate-schedule --season 2048 --scheduler C
```

`--season` is required and picks the config-dir input file (find the dir with `athc config path`): `<season>.league.ini`, which must include `[DivisionStandings]`. A missing file exits 1 with a clear message. It always writes a `.txt` and `.html` schedule plus a sortable HTML report to the **current directory**, named `schedule_<season>_<C|D>_<timestamp>` (report adds `_report.html`); `C` = fixed-place + CP-SAT, `D` = fixed-place + CP-SAT free-only. Exit `0` = written, `1` = error, `2` = bad arguments.

Two-phase model: phase 1 builds the matchup inventory (divisional + conference games fixed by structure; division standings fix two non-conference games per team, NFL-style same-place matchups; CP-SAT picks the rest along a configurable conference-rank line); phase 2 places those matchups into weeks via CP-SAT. `--scheduler` picks the phase-1 generator: the default `C` (the line covers the whole non-conference slate) or `D` (the line covers only the picked games).

## Design

How the schedule is built, in three docs:

- [Phase 1 — fixed-place + CP-SAT matchups](phase-1-matchups-fixed-cpsat.md) — Scheduler C (default)
- [Phase 1 — fixed-place + CP-SAT free-only matchups](phase-1-matchups-fixed-cpsat-free.md) — Scheduler D
- [Phase 2 — schedule placement](phase-2-schedule.md) — shared by all three
- [Prior art — the current NFL formula](nfl-formula.md) — background, not what athc uses

## Config

No `--config` flag — config is found via `ATHC_CONFIG_DIR` / the default config dir (see [../design/config.md](../design/config.md)):

- `rules/PNFL.scheduler.toml` — scheduler tunables (difficulty `spread`/`amplitude`, solver `time_limit`, `[phase2]` rule amounts); **optional**, each key defaults when absent (invalid TOML/value is an error). Installed but not advertised.
- `<season>.league.ini` (`[Divisions]` + `[Standings]` overall 1–18 `Order` list) — **required** league data, selected by `--season`. All schedulers use the overall order; Schedulers A and C derive their 1–9 conference ranks from it. A missing/invalid `[Standings]` is an error.

## Tests

```bash
pytest                  # fast suite (solver tests excluded)
pytest -m slow          # solver tests only (long-running)
pytest -m ''            # everything
```

Solver-backed tests (any using a solved-schedule fixture) are marked `slow` and skipped by default.
