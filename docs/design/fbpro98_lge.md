# fbpro98-lge

Library for reading the conferences, divisions, teams, rosters and standings from a Front Page Sports Football Pro '98 league (`.lge`) file.

## Features

- `.lge` reader for every league size, stock and custom (8 to 30 teams), chunks nested or grouped by kind
- Conference names, each conference's division names, each division's teams
- Team name, nickname and official name, as on the game's Team Settings screen
- Each team's roster: its players by `.pyr` id with their jersey numbers, in the roster screen's four status groups (Assigned, Open Active, Open Inactive, Injured Reserve) and slot order, the Training Camp table, and the two unknown byte runs kept as read
- Which team holds a player (`team_of`)
- Each team's regular-season record: W-L-T, points for, points against
- Division and conference standings, best first, ordered the way the game orders a finished season (the manual's tie-breakers); any teams of the file ranked the same way
- The played games: each regular-season week's and each playoff round's, with the winner and loser; how many games are left
- A mutable model with `validate()`, which checks every roster rule the spec states before an edit is written back
- Unmasks the team and roster chunks while reading
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

denver = lge.teams[4]
denver.roster.assigned[0]                        # RosterPlayer(player_id=6283, jersey=6): first on the depth chart
denver.roster.players                            # every player, in slot order
lge.teams[0].roster.open_inactive[6]             # None: Jacksonville's slot 53 is empty
denver.roster.training_camp[0]                   # the QB row: AC, AG, DI, EN, HA, IN, SP, ST percentages
lge.team_of(6283) is denver                      # the team whose roster holds that .pyr id

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
- `Team.name` ("Team Name"), `Team.nickname`, `Team.official_name` (the two joined by a space; just the one present when the other is empty), `Team.record`, `Team.roster`.
- `Record`: `wins`, `losses`, `ties`, `points_for`, `points_against`, `games`, `win_percentage` (a tie counts as half a win; 0.0 before any game), `point_differential`. Only regular-season games marked played count.
- `Roster`: `team_number` (the chunk's own, in clear); `assigned` (34 slots), `open_active` (12), `open_inactive` (7) and `injured_reserve` (10), the roster screen's status groups, each a list in slot order holding a `RosterPlayer` or `None` for an empty slot; `permutation` (the 10 bytes at 0xBD, as read); `training_camp` (8 rows in the Training Camp screen's group order QB, RB, REC, OL, DL, LB, DB, P/K, each row 8 percentages in `.pyr` ratings order AC, AG, DI, EN, HA, IN, SP, ST; all zero for a team never set up); `unknown` (the 60 bytes at 0x107, as read); `players` (every player, in slot order across the four groups). Depth is not stored: a position's depth is its rank among same-position players in slot order across `assigned` then `open_active`, the position coming from the `.pyr` (see the spec, section 6).
- `RosterPlayer`: `player_id` (the `.pyr` id, 1-65535), `jersey` (jersey number).
- `LgeFile.team_of(player_id)`: the first team in file order whose roster holds the id, else `None`.
- `LgeFile.validate()`: raises `ValueError` on the first roster rule broken, in file order, naming the team by its file-order number, the place as the game's screens name it (status groups with slots counted from 1, camp groups and ratings) and the field (`team 5: roster: Assigned slot 4: player_id: Must be 1-65535, got 65536`, `team 5: roster: training camp: QB: AC: Must be 0-100, got 101`). Checks: `team_number` fits a u16; each status group has its 34, 12, 7 or 10 slots; each player's `player_id` is 1-65535 and `jersey` fits a u8; `permutation` is 10 bytes; `training_camp` is 8 rows of 8 percentages 0-100, each row totalling at most 100; `unknown` is 60 bytes. Names and games are not checked. The reader does not call it: a file's roster fields are fixed-size, so only the training camp percentages could fail, and a tool that never looks at rosters should not be refused its league over them; whether the game would refuse such a file is untested, and no sampled file has one.
- `Division.standings`, `Conference.standings`: teams best first, the way the game orders a finished season's standings: won-lost-tied percentage, then the manual's tie-breakers among level teams (head-to-head, division record, conference record, net points in division games, net points in all games, strength of schedule), then file order; in season the game's screen sorts tied teams by points for instead (see [game behavior](../research/fbpro98-game-behavior.md#standings)). `ranked(lge, teams)` ranks any of the file's teams the same way, every team when `teams` is omitted; `LgeFile.teams` is every team in file order.
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
├── model.py       # LgeFile, Conference, Division, Team, Record, Game, Roster, RosterPlayer; ranked(); validate()
├── _standings.py  # internal: the game's tie-breakers, rank() over team numbers and results
├── schema.py      # chunk tags, sizes, field offsets, the roster layout, mask factor, schedule layout
└── reader.py      # read_lge / parse_lge; InvalidLgeError
```

The model nests teams in divisions and divisions in conferences, the way the file's chunk tree does, in mutable dataclasses with list fields, edited by assignment ([architecture.md](architecture.md#file-libraries)); the library has no writer, but each roster is kept whole, its unknown bytes as read, so one could write the chunk back (but for an empty slot's jersey byte, dropped on read and 0 in every sampled file), and `LgeFile.validate()` checks the roster rules the spec states before an edit is written back; the reader does not call it. Each team carries its record and its roster; each division and conference carries its standings, ranked by the reader from the file's games with `_standings.py`, an internal module the package does not export; `ranked(lge, teams)` ranks any teams of the file the same way and returns a list. The file's played games hang off `LgeFile`, by regular-season week and by playoff round, each naming the file's own team objects. A team is found by identity (`id(team)`), never by value: a mutable model is not hashable, and two teams can look the same.

### What this package does

- Reads any league's `.lge`, stock or custom, into a typed model in file order.
- Knows the `.lge` extension: `read_lge(league, league_dir)` reads `<league_dir>/<league>.lge`.
- Walks the chunks in order with one small cursor (`_Chunks`): each chunk must be the one the tree expects next and the size the spec gives; the conference, division and team counts drive the walk.
- Reads both chunk orders: nested (each team followed by its roster) and grouped by kind (every conference, division, team, then roster). A first team chunk followed by another team chunk means grouped; roster k pairs with team k either way.
- Unmasks each team chunk with its clear team number, and each roster chunk with its own clear u16 team number, which is not checked against the team's.
- Reads each roster's 63 slots at the spec's offsets into the four status groups the screen shows (slots 1-34, 35-46, 47-53, 54-63), an id of 0 as an empty slot whatever its jersey byte, then the permutation, training camp and unknown bytes.
- Reads the schedule after the tree: every played game, regular season or playoff, must name teams 1..N; the regular-season ones tally each team's record; the unplayed ones are counted. Nothing may follow it, so a tree with more parts than its counts say is caught.
- Reads a roster whatever its training camp bytes: the other roster fields are fixed-size, so nothing else could break a rule, `validate()` is for an edit or a future write, and whether the game would refuse such a file is untested (no sampled file has one).
- Ranks standings the way the game orders a finished season: won-lost-tied percentage, then the manual's tie-breakers among level teams (head-to-head, division record, conference record, net points in division games, net points in all games, strength of schedule with each opponent once), then file order. Once a step separates some of a level group, the placed teams and the rest are each ranked again from the first step. Exact arithmetic (`Fraction`), so equal records compare equal.

### What this package does NOT do

- Read any other field: league settings, ids, abbreviations, colors, the schedule's overtime flag and weeks played.
- Know what a roster's permutation or 60-byte table mean, or the depth-chart groups (QB, RB, REC, ...) the spec observed in one file.
- Check names or games in `validate()`: the library writes nothing, and only the rosters are kept whole.
- Refuse a file over a training camp rule: a tool that never looks at rosters is not refused its league.
- Count playoff games in the records, seed the playoffs, rank a playoff finish, or apply the last two tie-breakers (net touchdowns, coin toss), which the file cannot give.
- Reproduce the in-season standings screen, which sorts tied teams by points for.
- Write `.lge` files.
- Know where a league's files are; the caller supplies the folder.

See [formats/lge.md](../formats/lge.md) for the format.

### Testing

- `tests/unit/fbpro98_lge/test_reader.py` — real fixtures for every league size and both chunk orders, a season's weekly files for standings, Denver's and Jacksonville's rosters and every file's roster numbering, built bytes for each check and limit.
- `tests/unit/fbpro98_lge/test_model.py` — nesting, official name, records, games, `ranked`, `players`, `team_of` and `validate()` at each limit and one past it, on built files.
- `tests/unit/fbpro98_lge/test_standings.py` — each tie-breaker on built seasons, the restart after a placement, level teams keeping their order.

Fixtures in `tests/unit/fbpro98_lge/data/` are real game files.
