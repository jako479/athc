# fbpro98_standings — design

Date: 2026-10-13. Status: implemented.

## Goal

A new library, `src/athc/fbpro98_standings/`, that ranks a league's teams
from its `.lge` files: division, conference and league (final) standings,
by one of three tie-break methods (the game's, the scheduler's, the NFL's).
Tie-breaking is a game rule, not part of the file format, so it lives in its
own library.

## Scope

- In: the library, its tests, its docs, STATUS and CHANGELOG lines.
- Out: `fbpro98_lge` (its own standings and `ranked()` stay for now) and
  generate-schedule; switching them over and a standings command are later
  work.

## How a caller uses it

```python
current = read_lge("PNFL", upcoming_dir)     # fbpro98_lge.LgeFile
previous = read_lge("PNFL", previous_dir)    # fbpro98_lge.LgeFile

standings = Standings(current, method="game")                  # one season
standings = Standings(current, previous, team_moves,
                      method="scheduler", seed=seed)           # two seasons

standings.division(d)    # teams best first
standings.conference(c)  # teams best first
standings.league()       # every team, final order
```

```python
Standings(
    current: LgeFile,
    previous: LgeFile | None = None,
    team_moves: Mapping[str, str] | None = None,   # previous name -> current name
    *,
    method: Method,                                # Literal["game", "scheduler", "nfl"]
    seed: int | None = None,
)
```

- The caller reads each file with `fbpro98_lge`; the library never reads files.
- `method` is required, no default.
- `team_moves` lists only teams whose name changed; a team that only moved
  division needs nothing, since the current file says where it is.
- `seed` is used only for the coin toss; no seed means a fresh toss.
- Every result is a tuple of the current file's own `Team` objects.

## One season or two

- **Current file only**: ranks the current file's regular-season games as
  played (a season in progress is fine).
- **With the previous file**: ranks the previous file's games as played,
  under the previous season's divisions and conferences. `division(d)` and
  `conference(c)` take a division or conference of the current file, rank
  its teams on last season and return current teams. `league()` returns every
  current team in last season's final order.

## Modules

| Module | Job |
| :--- | :--- |
| `standings.py` | `Standings`: takes the inputs, runs the checks, answers `division`, `conference`, `league` |
| `moves.py` | Matches each previous-season team to its current team by name plus `team_moves`; raises the errors |
| `season.py` | From one `LgeFile`: each team's regular-season results (opponent, points for and against, division game or not, conference game or not) and the playoff round it reached |
| `steps.py` | One small function per tie-break step (list below) |
| `methods.py` | Each method as ordered step lists for division, conference and league standings |
| `errors.py` | `StandingsError(ValueError)` |
| `__init__.py` | Exports `Standings`, `Method`, `StandingsError` |

## Ranking (one algorithm for every method)

1. Order the teams by the method's first step.
2. Each group still level goes through the method's steps in order until one
   separates it.
   - game and scheduler: the teams the step placed and the rest are each
     ranked again from the first tie-breaker.
   - NFL: only the best club advances; the rest start over at step 1.
3. Teams level after every step: coin toss. The coin is tossed once per
   `Standings`: one random order of every team, drawn from the seed, so every
   request breaks a last tie the same way and a given seed always gives the
   same result.
4. A step the file cannot give (net touchdowns) is skipped.

## Definitions

- **W-L-T %**: (wins + ties / 2) / games; 0 with no games. Regular season
  only.
- **Playoff round reached**: the round a team went out in; the champion is
  one more than the last round; a team with a bye counts by the later round;
  a team with no playoff game is below every playoff team.
- **Head-to-head**: W-L-T % in games among the level teams only.
- **Division / conference W-L-T %**: W-L-T % in games against the team's own
  division / conference, in the season being ranked.
- **Common games**: W-L-T % in games against opponents every level team
  played.
- **Strength of victory**: combined W-L-T % of the teams beaten, every win
  counted.
- **Strength of schedule**: combined W-L-T % of the opponents, either each
  opponent once or every game counted (per method); tougher ranks higher.
- **Combined ranking**: a team's rank in points scored plus its rank in
  points allowed, among the conference's or the league's teams; lowest wins;
  equal values share a rank.
- **Net points**: points for minus points against, in the games named.
- **Division winners**: each division's first team in its division
  standings (same method), in the season being ranked.
- **Division finish**: level teams that were all in one division keep their
  order in that division's standings (same method); otherwise the step is
  skipped.

## Methods

Steps after W-L-T % are tie-breakers. "Coin toss" is always last.

### game (the FbPro98 manual, pages 129 and 136)

| Standings | Steps |
| :--- | :--- |
| Division | W-L-T %, head-to-head, division W-L-T %, conference W-L-T %, net points in division games, net points in all games, strength of schedule (each opponent once), net touchdowns (skipped), coin toss |
| Conference | Division winners first, then the rest; each part by the division steps |
| League | Champion first, Super Bowl loser second; every other team by regular-season W-L-T %, then strength of schedule (each opponent once), coin toss |

### scheduler

| Standings | Steps |
| :--- | :--- |
| Division | W-L-T %, head-to-head, division W-L-T %, conference W-L-T %, net points in division games, net points in all games, strength of schedule (each opponent once), coin toss |
| Conference | The conference's teams in `league()` order |
| League | Playoff round reached, regular-season W-L-T %, strength of schedule (every game counted), division finish, point differential, coin toss |

### nfl ([NFL Tiebreaking Procedures](https://www.nfl.com/standings/tie-breaking-procedures))

| Standings | Steps |
| :--- | :--- |
| Division | W-L-T %, head-to-head, division W-L-T %, common games, conference W-L-T %, strength of victory, strength of schedule (every game counted), combined conference ranking, combined league ranking, net points in common games, net points in all games, net touchdowns (skipped), coin toss |
| Conference | Division winners first, then the rest. Level teams all in one division: the division steps. Otherwise: with 3+ teams, first keep only each division's best (division steps); then W-L-T %, head-to-head (3+ teams: only a clean sweep), conference W-L-T %, common games (at least four), strength of victory, strength of schedule, combined conference ranking, combined league ranking, net points in conference games, net points in all games, net touchdowns (skipped), coin toss |
| League | Playoff round reached, W-L-T %, strength of schedule (every game counted). Still level: one division, the division steps; one conference, the conference steps; otherwise each division's best (division steps), then each conference's best (conference steps), then head-to-head, common games (at least four), strength of victory, combined league ranking, net points in all games, net touchdowns (skipped), coin toss |

## Checks

All raise `StandingsError` when `Standings` is built, before any request,
naming the team and which file (previous or current):

- with two files, a team name repeats in either file;
- a team move names a team not in the previous file, or a name not in the
  current file, or a name another previous-season team keeps (unless that
  team moves too), or a name another move already took;
- a team has no match in the other file.

Caller mistakes raise `ValueError`: an unknown method, `team_moves` without
`previous`, a division or conference not of the current file.

## Tests

`tests/unit/fbpro98_standings/`, on the real `.lge` test files in
`tests/unit/fbpro98_lge/data/` and `tests/integration/data/`, plus small
leagues built in code for single steps:

- each step on its own, both sides of every limit (common games: four
  accepted, three skipped; clean sweep: swept, not swept);
- game: division orders equal the `fbpro98_lge` tests' expected orders where
  no coin toss is reached;
- scheduler: `league()` on `PNFL-2047-after-super-bowl.lge` equals the old
  `2048.league.ini` overall order (git `dade898^`, Baltimore for Los Angeles);
  on `PNFL-2046-after-super-bowl.lge`, Chicago ahead of Green Bay (level
  through strength of schedule, same division);
- nfl: each restart rule and the 3+ team paths;
- two seasons: a renamed team, a team that changed division (2046 -> 2047);
- every check, both sides; the caller-mistake `ValueError`s;
- coin toss: the same seed gives the same order; conference standings agree
  with division standings when the coin decides.

## Docs

- New `docs/fbpro98_standings/README.md` and `ARCHITECTURE.md`; new
  `tests/unit/fbpro98_standings/README.md` (test matrix).
- `docs/design/architecture.md` package tree and library list.
- `STATUS.md`, `CHANGELOG.md`.

## Out of scope

- Changing `fbpro98_lge` or generate-schedule; the standings command.
- Net touchdowns (not in the file).
