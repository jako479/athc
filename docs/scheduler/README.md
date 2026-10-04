# generate-schedule

Generates a season schedule with OR-Tools, plus a companion sortable HTML report.

## Install

OR-Tools (the solver) is a required dependency, so any install includes it. For development:

```bash
uv sync
```

## Usage

```bash
athc generate-schedule --season 2048
athc generate-schedule --season 2048 --seed 7 --time-limit 600
```

`--season` is required and picks the config-dir input file (find the dir with `athc config path`): `<season>.league.ini`, which must include `[OverallStandings]` and exactly one of `[DivisionStandings]` or `[ConferenceStandings]`. A missing file exits 1 with a clear message. It always writes a `.txt` and `.html` schedule plus a sortable HTML report to the **current directory**, named `schedule_<season>_<timestamp>` (report adds `_report.html`). Exit `0` = written, `1` = error, `2` = bad arguments.

Two-phase model: phase 1 builds the matchup inventory (same-conference games fixed by league structure; fixed non-conference games — the PNFL's division-place matchups, any cross-conference rivalry — forced in; CP-SAT picks the rest along a configurable conference-rank line); phase 2 places those matchups into weeks via CP-SAT.

## League formats

The same two phases serve two league shapes. Which one is in play comes from the league file; the number of weeks from the rules file.

| | PNFL | PCFL |
|---|---|---|
| League file | `[DivisionStandings]` + `[OverallStandings]` | `[ConferenceStandings]` + `[OverallStandings]` |
| Weeks | 16 (`[league] weeks`, the default) | 12 |
| Same-conference games | division rivals twice, rest of the conference once | every conference team once |
| Non-conference | 4-5; two fixed by division place, rest by the SOS line | 4; all by the SOS line (flat by default) |
| Season shape | NFL-style rules ([phase 2](phase-2-schedule.md)) | weeks 1-3 non-conference, one cross-conference game a week after that, rivalry week last |

The PCFL's rules live in `dev/leagues/PCFL/rules/scheduler.toml`; its 2029 league file in `dev/leagues/PCFL/standings/`. Selecting a league from the command line is not wired yet — tests build PCFL schedules directly.

## Design

How the schedule is built, in three docs:

- [Phase 1 — fixed-place + CP-SAT matchups](phase-1-matchups-fixed-cpsat.md)
- [Phase 2 — schedule placement](phase-2-schedule.md)
- [Prior art — the current NFL formula](../design/research/nfl-formula.md) — background, not what athc uses
- [Research — NFL schedule patterns](../design/research/nfl-schedules.md) — provenance of the phase-2 rules
- [Research — CP-SAT rule design patterns](../design/research/cpsat-rule-patterns.md) — hard/soft rules, preventing solver anomalies

## Config

No `--config` flag — config is found via `ATHC_CONFIG_DIR` / the default config dir (see [../design/config.md](../design/config.md)):

- `rules/PNFL.scheduler.toml` — scheduler tunables: difficulty `spread`, solver `time_limit` / `solver_workers`, `[league] weeks` (even; default 16), `[phase2]` rule amounts; **optional**, each key defaults when absent (invalid TOML/value is an error). `solver_workers` is a fixed reproducibility setting — same value everywhere or a seed's schedule changes. Installed but not advertised.
- A league without divisions adds: `[phase2]` `max_consecutive_conference_home_or_away`, `opening_nonconference_weeks` and the three `require_*` toggles for the NFL-pattern home/away rules; `[rivalries]` `pairs` and `rotate_home_by_season`. See the PCFL file under `dev/leagues/PCFL/rules/`.
- `<season>.league.ini` (exactly one of `[DivisionStandings]` (per-division teams in finish order — this defines division membership) or `[ConferenceStandings]` (two conferences of nine, no divisions), plus `[OverallStandings]` overall 1–18 `Order` list) — **required** league data, selected by `--season`. Both schedulers derive their 1–9 conference ranks from the overall order. A missing/invalid `[OverallStandings]`, or a missing/invalid `[DivisionStandings]`/`[ConferenceStandings]`, is an error.

## Tests

```bash
pytest                  # fast suite (solver tests excluded)
pytest -m slow          # solver tests only (long-running)
pytest -m ''            # everything
```

Solver-backed tests (any using a solved-schedule fixture) are marked `slow` and skipped by default.
