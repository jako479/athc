# fbpro98-lge

Library for reading the conferences, divisions, teams and standings from a Front Page Sports Football Pro '98 league (`.lge`) file.

## Features

- `.lge` reader for every league size, stock and custom (8 to 30 teams), chunks nested or grouped by kind
- Conference names, each conference's division names, each division's teams
- Team name, nickname and official name, as on the game's Team Settings screen
- Each team's regular-season record: W-L-T, points for, points against
- Division and conference standings, best first, ordered the way the game orders a finished season (the manual's tie-breakers); any teams of the file ranked the same way
- The played games: each regular-season week's and each playoff round's, with the winner and loser; how many games are left
- Unmasks the team chunks while reading
- In-memory parser (`parse_lge`)

## Setup

```bash
uv sync
```

## Usage

```python
from athc.fbpro98_lge import ranked, read_lge

lge = read_lge("PNFL", r"E:\SIERRA\FbPro98")     # reads PNFL.lge in that folder

for conference in lge.conferences:
    print(conference.name)                       # "" in PNFL.lge
    for division in conference.divisions:
        print(division.name)                     # "East"
        for team in division.standings:          # best first
            team.official_name                   # "Jacksonville Jaguars"
            team.record                          # Record(wins=5, losses=1, ties=0, points_for=164, points_against=112)
    conference.standings                         # every team in the conference, best first

lge.weeks[0]                                     # week 1's played games
lge.playoffs[-1][0].winner                       # the champion, once the last round is played
lge.unplayed_games                               # 0 after the last playoff game
ranked(lge, lge.teams[:4])                       # any teams of the file, best first
ranked(lge)                                      # every team, best first
```

`parse_lge(buffer)` is the bytes-in entry point; `read_lge` builds the path from the league name and its folder and wraps file I/O.

## API

- `read_lge(league, league_dir)` reads `<league_dir>/<league>.lge` and returns an `LgeFile`; `parse_lge(buffer, path)` parses raw bytes, `path` only naming the source in errors (`<path>: <reason>`).
- `LgeFile.conferences` → `Conference.name`, `Conference.divisions` → `Division.name`, `Division.teams` → `Team`, all in file order. Walking them in order gives the team numbers 1..N that key the other league files.
- `Team.name` ("Team Name"), `Team.nickname`, `Team.official_name` (the two joined by a space; just the one present when the other is empty), `Team.record`.
- `Record`: `wins`, `losses`, `ties`, `points_for`, `points_against`, `games`, `win_percentage` (a tie counts as half a win; 0.0 before any game), `point_differential`. Only regular-season games marked played count.
- `Division.standings`, `Conference.standings`: teams best first, the way the game orders a finished season's standings: won-lost-tied percentage, then the manual's tie-breakers among level teams (head-to-head, division record, conference record, net points in division games, net points in all games, strength of schedule), then file order; in season the game's screen sorts tied teams by points for instead (see [game behavior](fbpro98-game-behavior.md#standings)). `ranked(lge, teams)` ranks any of the file's teams the same way, every team when `teams` is omitted; `LgeFile.teams` is every team in file order.
- `LgeFile.weeks`: each regular-season week's played games; `LgeFile.playoffs`: each playoff round's; `LgeFile.unplayed_games`: how many games, regular season and playoffs, are not played yet.
- `Game`: `home`, `home_score`, `away`, `away_score` (the file's teams), `winner` and `loser` (None on a tie).
- A name is the text up to its NUL, or the whole field when it has none; an empty name is `""`.
- `InvalidLgeError`: empty file, a chunk header cut short, a chunk running past the end, a chunk other than the one expected next, a chunk of the wrong size, a schedule cut short or followed by data, data after the schedule, or a played game, regular season or playoff, naming a team outside 1..N. The first problem in file order is reported.

## Testing

```bash
uv run pytest
```

## How it works

### Module layout

```
src/athc/fbpro98_lge/
├── __init__.py    # public API re-exports
├── model.py       # LgeFile, Conference, Division, Team, Record, Game; ranked()
├── standings.py   # the game's tie-breakers: rank() over team numbers and results
├── schema.py      # chunk tags, sizes, field offsets, mask factor, schedule layout
└── reader.py      # read_lge / parse_lge; InvalidLgeError
```

The model nests teams in divisions and divisions in conferences, the way the file's chunk tree does. Each team carries its record; each division and conference carries its standings, ranked by the reader from the file's games with `standings.py`; `ranked(lge, teams)` ranks any teams of the file the same way. The file's played games hang off `LgeFile`, by regular-season week and by playoff round, each naming the file's own team objects.

### What this package does

- Reads any league's `.lge`, stock or custom, into a typed model in file order.
- Knows the `.lge` extension: `read_lge(league, league_dir)` reads `<league_dir>/<league>.lge`.
- Walks the chunks in order with one small cursor (`_Chunks`): each chunk must be the one the tree expects next and the size the spec gives; the conference, division and team counts drive the walk.
- Reads both chunk orders: nested (each team followed by its roster) and grouped by kind (every conference, division, team, then roster). A first team chunk followed by another team chunk means grouped.
- Unmasks each team chunk with its clear team number.
- Reads the schedule after the tree: every played game, regular season or playoff, must name teams 1..N; the regular-season ones tally each team's record; the unplayed ones are counted. Nothing may follow it, so a tree with more parts than its counts say is caught.
- Ranks standings the way the game orders a finished season: won-lost-tied percentage, then the manual's tie-breakers among level teams (head-to-head, division record, conference record, net points in division games, net points in all games, strength of schedule with each opponent once), then file order. Once a step separates some of a level group, the placed teams and the rest are each ranked again from the first step. Exact arithmetic (`Fraction`), so equal records compare equal.

### What this package does NOT do

- Read any other field: league settings, ids, abbreviations, colors, rosters, the schedule's overtime flag and weeks played.
- Count playoff games in the records, seed the playoffs, rank a playoff finish, or apply the last two tie-breakers (net touchdowns, coin toss), which the file cannot give.
- Reproduce the in-season standings screen, which sorts tied teams by points for.
- Write `.lge` files.
- Know where a league's files are; the caller supplies the folder.

See [formats/lge.md](formats/lge.md) for the format.

### Testing

- `tests/unit/fbpro98_lge/test_reader.py` — real fixtures for every league size and both chunk orders, a season's weekly files for standings, built bytes for each check and limit.
- `tests/unit/fbpro98_lge/test_model.py` — nesting, official name, records, games, `ranked` on built files.
- `tests/unit/fbpro98_lge/test_standings.py` — each tie-breaker on built seasons, the restart after a placement, level teams keeping their order.

Fixtures in `tests/unit/fbpro98_lge/data/` are real game files.
