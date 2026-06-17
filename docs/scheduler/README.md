# generate-schedule

Generates a season schedule with OR-Tools, plus a companion text report.

## Install

OR-Tools is large, so it ships as an optional extra (not in the core install):

```bash
uv pip install -e ".[schedule]"
```

## Usage

```bash
athc generate-schedule --output season.html --season 2026
athc generate-schedule --output season.txt --season 2026 --seed 7 --time-limit 600
```

The writer is chosen from `--format`, else the `--output` extension (`htm`/`html`/`txt`). A text report is written alongside the output (`season.html` → `season-report.txt`; override with `--report`). `--league` / `--history` override the default `league.ini` / `nonconf_history.json`. Exit `0` = written, `2` = error.

Two-phase model: phase 1 builds the matchup inventory (divisional + conference games, then all non-conference games chosen together by conference rank); phase 2 places those matchups into weeks via CP-SAT. `--scheduler` picks the phase-1 generator: the default `two-phase-rank`, or the older `fixed-matchup`.

## Design

How the schedule is built, in three docs:

- [Phase 1 — matchup inventory](phase-1-matchups.md) — the default generator
- [Phase 1 — difficulty tuning](phase-1-difficulty-tuning.md) — strength-of-schedule curve & bounds
- [Phase 1 — fixed-rank matchups](phase-1-matchups-fixed-rank.md) — alternate/prototype
- [Phase 2 — schedule placement](phase-2-schedule.md) — shared by both

## Config

No `--config` flag — config is found via `ATHC_CONFIG_DIR` / the default config dir (see [../design/config.md](../design/config.md)):

- `rules/PNFL.scheduler.toml` — scheduler tunables (difficulty `spread`/`shape`, solver `time_limit`, `[phase2]` rule amounts); **optional**, each key defaults when absent (invalid TOML/value is an error). Installed but not advertised.
- `league.ini` (`[Divisions]` + `[Standings]` overall 1–18 `Order` list and/or `[ConferenceRanking]` AFC/NFC 1–9 lists) — **required** league data. `two-phase-rank` needs the overall list; `fixed-matchup` needs the conference order (derived from overall when only `[Standings]` is given). A missing/invalid ranking is an error.
- `nonconf_history.json` — past inter-conference matchups.

## Tests

```bash
pytest                  # fast suite (solver tests excluded)
pytest -m slow          # solver tests only (long-running)
pytest -m ''            # everything
```

Solver-backed tests (any using a solved-schedule fixture) are marked `slow` and skipped by default.
