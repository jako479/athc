# fbpro98-standings

Library that ranks a Front Page Sports Football Pro '98 league's teams from its `.lge` files: division, conference and league standings, by the game's, the scheduler's or the NFL's tie-breakers. Each method's steps: [Methods](#methods).

## Features

- Division, conference and league (final) standings, best first
- Three tie-break methods: `game` (the manual's), `scheduler` (generate-schedule's), `nfl` (the NFL's)
- One season, or last season's results for this season's divisions and teams, with team moves for teams whose name changed
- A repeatable coin toss with a seed

## Setup

```bash
uv sync
```

## Usage

```python
from athc.fbpro98_lge import read_lge
from athc.fbpro98_standings import Standings

current = read_lge("PNFL", league_dir)
standings = Standings(current, method="game")
for conference in current.conferences:
    standings.conference(conference)           # its teams, best first
    for division in conference.divisions:
        standings.division(division)           # its teams, best first
standings.league()                             # every team, final order

previous = read_lge("PNFL", previous_dir)
standings = Standings(
    current, previous, {"Baltimore": "Los Angeles"}, method="scheduler", seed=1
)
```

## API

- `Standings(current, previous=None, team_moves=None, *, method, seed=None)`: standings by one method. With `previous`, last season's results for the current file's divisions and teams; `team_moves` maps a renamed team's previous name to its current one; `seed` repeats the coin toss.
- `Standings.division(division)`, `Standings.conference(conference)`, `Standings.league()`: the current file's teams, best first.
- `Method`: `"game"`, `"scheduler"` or `"nfl"`.
- `StandingsError`: the two files and the team moves do not fit together.

## How it works

Tie-breaking is a game rule, not part of the file format, so it lives here; this is the design doc for it.

- Ranks from the games in the file (regular season for records, playoffs for the playoff round), never from the records the file stores. Exact arithmetic (`Fraction`).
- One engine for every method. For division, conference and league standings, a method gives the steps that sort every team and the tie-breakers for the teams still level.
- A level group goes through the tie-breakers in order until one separates it. The game and the scheduler then rank the teams the step placed and the rest again from the first tie-breaker; the NFL places only the best team and sends the rest back to the first tie-breaker.
- Teams level after every step: coin toss. The coin is tossed once per `Standings` (one random order of every team, drawn from the seed) and every answer is kept, so a seed repeats the result and the same question gets the same answer.
- Net touchdowns, in the game's and the NFL's lists, are not in the file and are skipped.
- With the previous season's file: ranks last season as played, under its own divisions, and answers with the current file's teams. Teams match by name plus the team moves; a repeated name, a move naming an unknown team or a name another team keeps, or a team with no match is a `StandingsError` when `Standings` is built.

### Module layout

```
src/athc/fbpro98_standings/
├── __init__.py    # public API: Standings, Method, StandingsError
├── standings.py   # Standings; _Ranker, the one ranking engine
├── methods.py     # each method's steps for division, conference and league standings, as data
├── steps.py       # one function per tie-break step
├── moves.py       # match the previous season's teams to the current season's
├── season.py      # one LgeFile as numbered teams, results and playoff rounds
└── errors.py      # StandingsError
```

### Steps

Every value counts regular-season games only. W-L-T % is (wins + ties / 2) / games, 0 with no game.

| Step | Value |
| :--- | :--- |
| W-L-T % | In every game |
| Head-to-head | W-L-T % in the games among the level teams. Sweep (NFL conference): with three or more teams, only one that beat or lost to every other level team is placed |
| Division / conference W-L-T % | In games against the team's own division / conference |
| Common games | W-L-T % against the opponents every level team played; where a minimum applies, skipped when a team played fewer than four |
| Strength of victory | Combined W-L-T % of the teams beaten, every win counted |
| Strength of schedule | Combined W-L-T % of the opponents, tougher ranks higher: each opponent once (the game) or every game counted (the scheduler, the NFL) |
| Combined ranking | Rank in points scored plus rank in points allowed, among the conference's or the league's teams; lower wins; equal values share a rank |
| Net points | Points for minus points against: all games, division games, conference games or common games |
| Division finish | Level teams all of one division keep their order in its standings (same method); otherwise skipped |
| Playoff round | The round a team went out in, the champion highest; a bye counts by the later round; no playoff game ranks below every playoff team |
| Champion, runner-up | The champion first, the Super Bowl loser second, every other team level |
| Division winners | Each division's first team in its division standings (same method) |

### Methods

The first steps sort every team; after the semicolon come the tie-breakers; the coin toss is always last.

#### game (the manual, pages 129 and 136)

| Standings | Steps |
| :--- | :--- |
| Division | W-L-T %; head-to-head, division W-L-T %, conference W-L-T %, net points in division games, net points in all games, strength of schedule |
| Conference | Division winners first, then the rest, each part by the division steps |
| League | Champion, runner-up, W-L-T %, strength of schedule (the draft order, reversed) |

#### scheduler (generate-schedule's order, which reproduces the PNFL's published standings)

| Standings | Steps |
| :--- | :--- |
| Division | The game's division steps |
| Conference | The conference's teams in league order |
| League | Playoff round, W-L-T %, strength of schedule (every game); division finish, net points in all games |

#### nfl ([NFL Tiebreaking Procedures](https://www.nfl.com/standings/tie-breaking-procedures))

| Standings | Steps |
| :--- | :--- |
| Division | W-L-T %; head-to-head, division W-L-T %, common games, conference W-L-T %, strength of victory, strength of schedule (every game), combined conference ranking, combined league ranking, net points in common games, net points in all games |
| Conference | Division winners first, then the rest, each part by W-L-T %; level teams of one division: the division steps; otherwise only each division's best goes on, by head-to-head (sweep), conference W-L-T %, common games (at least four), strength of victory, strength of schedule (every game), combined conference ranking, combined league ranking, net points in conference games, net points in all games |
| League | Playoff round, W-L-T %, strength of schedule (every game); level teams of one division: the division steps; of one conference: the conference steps; otherwise each division's best, then each conference's best, go on, by head-to-head, common games (at least four), strength of victory, combined league ranking, net points in all games |

### What this package does NOT do

- Read files; the caller passes `LgeFile` objects from `fbpro98_lge`.
- Net touchdowns: not in the file, so that step is skipped.
- Know a league's team moves; the caller passes them.
- Rank for `fbpro98_lge` or generate-schedule, which keep their own ranking for now (`fbpro98_lge/_standings.py`, `scheduler/league_files.py`).

### Sources

- The game's list, and how it was checked against the PNFL's seasons: [fbpro98-game-behavior.md](../research/fbpro98-game-behavior.md#tie-breakers).
- The game's, the NFL's, pnfl.biz's and the scheduler's rules side by side: [standings-tie-breakers.md](../research/standings-tie-breakers.md).

### Testing

- `tests/unit/fbpro98_standings/`: each step on built leagues, each method on built leagues and the PNFL's real files, two seasons, every error. Matrix: [tests/unit/fbpro98_standings/README.md](../../tests/unit/fbpro98_standings/README.md).
