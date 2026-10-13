# generate-schedule

Generates a league's season schedule with OR-Tools, plus a companion sortable HTML report.

## Install

OR-Tools (the solver) is a required dependency, so any install includes it. For development:

```bash
uv sync
```

## Usage

```bash
athc generate-schedule --season 2050 --previous "E:\PNFL\2049 final"
athc generate-schedule --league PCFL --season 2030 --previous D:\PCFL\2029 --upcoming D:\PCFL\2030 --seed 7
```

`--league name` names the league (or `[athc] league` in `athc.ini`). The league data comes from two of the game's own league files, each the league's `<league>.lge`:

- `--previous folder` — the previous season's, saved after its last playoff game: the standings (each team's record, opponents and playoff finish). Required.
- `--upcoming folder` — the upcoming season's: the conferences, divisions and team names. Default: `path` in the league's `league.toml`, the folder that holds the league's files.

Teams are matched by name. A team that changed its name between the two seasons is listed in the league's `scheduler.toml` (in the league's folder under the config dir; find it with `athc config path`), one table per upcoming season: `[renames.2048]` with `Baltimore = "Los Angeles"` (previous name = new name). The same file holds the rule amounts and solver settings; every key defaults.

It writes a `.txt` and `.html` schedule plus a sortable HTML report to the **current directory**, named `schedule_<season>_<timestamp>` (the report adds `_report.html`). Progress (`Generating the <season> schedule`, `Phase 1: ...`, `Phase 2: ...`) prints on stderr as it runs; then `OK   <file>` per file written and `Generated <n> games (seed <s>)`. Exit `0` = written, `2` = an error (`FAIL <why>`: config, a league file, no feasible schedule, I/O, `Missing ortools. Reinstall athc.`) or bad arguments. Shared console and codes: [architecture](../design/architecture.md#console-run-log-and-errors).

## The standings

From the previous season's file, which must be finished (every regular-season and playoff game played):

- Overall order (the 1-18 ranks, and the 1-9 conference ranks the difficulty line uses): playoff finish first (champion, runner-up, then the round each team went out in, then the teams that missed the playoffs), then win percentage, then strength of schedule (opponents' combined record that season, tougher first), then point differential, then file order. This reproduces the PNFL's own published order.
- Each division's finish order (the same-place pairs): the upcoming division's members ranked by their previous season the way the game ranks a finished season (win percentage, then the manual's tie-breakers under the previous season's divisions, then file order; the lge library's `ranked`), so a division whose membership changed still gets an order.

## Teams that moved

A team is matched to its previous season by name, so a team that moved keeps its previous record, games and playoff finish. Two cases:

- Renamed, same division: list it under `[renames.<season>]` and it keeps its division place under the new name (2048: `Baltimore = "Los Angeles"`).
- In a different division (or conference): that division's finish order is its upcoming members ranked on their previous seasons, so the other members' places shift around the newcomer; the overall 1-18 order is unchanged.

2047 AFC East: Miami (11-5 as Houston) and Jacksonville (5-11) came over from the West, Buffalo (10-6) and New England (3-13) stayed, so the East's finish order became Miami, Buffalo, Jacksonville, New England.

## How it works

Two phases. Phase 1 picks every matchup: league structure fixes the same-conference games, the same-place rule and any cross-conference rivalry fix some non-conference games, and CP-SAT picks the rest along a configurable difficulty line. Phase 2 places the matchups into weeks with CP-SAT. The same code serves every league: the upcoming season's league file gives the structure, the previous season's the standings, the rules file the amounts.

## League shapes

| | With divisions (the PNFL) | Conferences only (the PCFL) |
|---|---|---|
| League file | two or more divisions in a conference | one division per conference |
| Weeks | 16 (`[league] weeks`, the default) | 12 |
| Same-conference games | division rivals twice, rest of the conference once | every conference team once |
| Non-conference | same-place pairs fixed, rest by the difficulty line | the cross-conference rivalry fixed, rest by the line |
| Season shape | NFL-style rules ([phase 2](phase-2-schedule.md)) | opening non-conference weeks, conference-sequence cap, rivalry week last |

Conferences and divisions go by their position in the league file (names may be empty or repeat); division sizes are their team counts. Shipped files, in `config/dev/` and `config/release/`: `leagues\PNFL\` and `leagues\PCFL\`, each with its `scheduler.toml`.

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

One test suite runs every league: two divisional standings variants and the conference league. The league-file loader is tested on the PNFL's real 2046-2048 files. Solver-backed tests are `slow` and skipped by default.
