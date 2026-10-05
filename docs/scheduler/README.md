# generate-schedule

Generates a league's season schedule with OR-Tools, plus a companion sortable HTML report.

## Install

OR-Tools (the solver) is a required dependency, so any install includes it. For development:

```bash
uv sync
```

## Usage

```bash
athc generate-schedule --season 2048
athc generate-schedule --league PCFL --season 2029 --seed 7
```

`--league name` names the league (or `[athc] league` in `athc.ini`); `--season` picks its standings file. Both files live in the league's folder under the config dir (find it with `athc config path`):

- `standings\<season>.league.ini` — the standings: `[OverallStandings]` plus `[DivisionStandings]` (a league with divisions) or `[ConferenceStandings]` (two conferences, no divisions). Required.
- `rules\scheduler.toml` — rule amounts and solver settings. Optional; every key defaults.

It writes a `.txt` and `.html` schedule plus a sortable HTML report to the **current directory**, named `schedule_<season>_<timestamp>` (the report adds `_report.html`). Exit `0` = written, `1` = error (config, no feasible schedule, I/O), `2` = bad arguments.

## How it works

Two phases. Phase 1 picks every matchup: league structure fixes the same-conference games, the same-place rule and any cross-conference rivalry fix some non-conference games, and CP-SAT picks the rest along a configurable difficulty line. Phase 2 places the matchups into weeks with CP-SAT. The same code serves every league: the standings file gives the structure, the rules file the amounts.

## League shapes

| | With divisions (the PNFL) | Conferences only (the PCFL) |
|---|---|---|
| Standings file | `[DivisionStandings]` + `[OverallStandings]` | `[ConferenceStandings]` + `[OverallStandings]` |
| Weeks | 16 (`[league] weeks`, the default) | 12 |
| Same-conference games | division rivals twice, rest of the conference once | every conference team once |
| Non-conference | same-place pairs fixed, rest by the difficulty line | the cross-conference rivalry fixed, rest by the line |
| Season shape | NFL-style rules ([phase 2](phase-2-schedule.md)) | opening non-conference weeks, conference-sequence cap, rivalry week last |

Division names are the standings keys (`<CONFERENCE>_<DIVISION>`); division sizes are the line counts. Shipped files, in `dev/` and `release/`: `leagues\PNFL\` and `leagues\PCFL\`, each with its `standings\<season>.league.ini` files and `rules\scheduler.toml`.

## Design

- [Phase 1 — matchups](phase-1-matchups.md)
- [Phase 2 — schedule placement](phase-2-schedule.md)
- [Prior art — the current NFL formula](../design/research/nfl-formula.md) — background, not what athc uses
- [Research — NFL schedule patterns](../design/research/nfl-schedules.md) — provenance of the phase-2 rules
- [Research — CP-SAT rule design patterns](../design/research/cpsat-rule-patterns.md) — hard/soft rules, preventing solver anomalies

## Tests

```bash
pytest                  # fast suite (solver tests excluded)
pytest -m slow          # solver tests only (long-running)
pytest -m ''            # everything
```

One test suite runs every league: two divisional standings variants and the conference league. Solver-backed tests are `slow` and skipped by default.
