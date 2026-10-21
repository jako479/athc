# fbpro98-stats

Library for reading a Front Page Sports Football Pro '98 league's stats file (`.dat`).

## Features

- Player stats for the last game, the season and the career
- Team stats, and what each team's opponents did against it, for the last game and the season
- Honors: Players of the Game and of the Week, the All-Pro team, Coach of the Year, awards, Hall of Fame points and nominees
- Records grouped by player or team, in id order
- In-memory parser (`parse_stats`)

## Setup

```bash
uv sync
```

## Usage

```python
from athc.fbpro98_stats import read_stats

stats = read_stats("PNFL", r"E:\SIERRA\FbPro98")   # reads PNFL.dat in that folder

stats.player_season[4037].passing          # Passing(attempts=615, yards=4386, ...)
stats.team_season[3].rushing.touchdowns    # 18
stats.opponents_season[3].rushing          # what team 3's opponents ran for
stats.coach_of_the_year                    # 7, a team number
stats.awards[-1].kind                      # AwardKind.ROOKIE_OF_THE_YEAR
```

The values shown are the PNFL's after week 16 of 2047. Ids stay numbers: player ids from the `.pyr`, team numbers from the `.lge`. `parse_stats(buffer)` is the bytes-in entry point; `read_stats` builds the path from the league name and its folder and wraps file I/O.

## API

- `read_stats(league, league_dir)` reads `<league_dir>/<league>.dat` and returns a `StatsFile`; `parse_stats(buffer, path)` parses raw bytes, `path` only naming the source in errors (`<path>: <reason>`).
- `StatsFile`: one mapping per block, id to stats (`player_last_game`, `player_season`, `player_career` to `PlayerStats`; `team_last_game`, `team_season`, `opponents_last_game`, `opponents_season` to `TeamStats`), then the honors: `players_of_the_game`, `all_pro`, `coach_of_the_year` (a team number) and `awards`. Every field defaults to empty, so an empty `.dat` is `StatsFile()`.
- `PlayerStats`, `TeamStats`: one field per category, `None` where the file has no record, never a zero object, so a writer can tell an insert from a change. A one-value category is an `int`.
- Stat classes, values in the spec's order: `ExtraPoints`, `FieldGoals` (`long` and five `FieldGoalRange(made, attempts)`), `Rushing`, `Passing`, `Receiving`, `Interceptions`, `Punting`, `PuntReturns`, `KickReturns`, `FumbleRecoveries`, `TwoPointConversions`; player only `HallOfFamePoints`, `HallOfFameNominee`; team only `FirstDowns`, `Downs`, `GameDetails`.
- Honors: `PlayerOfTheGame` (`game` from 0, `None` for the Player of the Week), `AllProPick`, `Award` with its `AwardKind`.
- `InvalidStatsError`: the first problem found, in this order: shorter than the 140-byte header; file end not the size less one; record size not 20; slots end below the header, not whole slots, or past the file end; then per slot, in slot order, a type that is not a stats type, a type and id seen before, or an honor id that does not decode; last, a record count that is not the live slots.

| Category | `PlayerStats` | `TeamStats` |
| ---: | :--- | :--- |
| 0-13 | `extra_points`, `field_goals`, `rushing`, `passing`, `receiving`, `interceptions`, `punting`, `punt_returns`, `kick_returns`, `fumbles`, `fumble_recoveries`, `sacks`, `safeties`, `tackles` | the same |
| 14 | `hall_of_fame_points` | `first_downs` |
| 15 | the honors, in `StatsFile` | `downs` |
| 16 | `penalties` (last game), `hall_of_fame_nominee` (career) | `game_details` |
| 17 | `two_point_conversions` | `two_point_conversions` |

## Testing

```bash
uv run pytest
```

## How it works

### Module layout

```
src/athc/fbpro98_stats/
├── __init__.py    # public API re-exports
├── model.py       # StatsFile, PlayerStats, TeamStats, the stat and honor classes, AwardKind
├── schema.py      # header offsets, record struct, block bases, categories, honor ids, award codes
└── reader.py      # read_stats / parse_stats; InvalidStatsError
```

Built for the standings' net-touchdowns tie-breaker, which needs touchdowns the `.lge` lacks; a writer for stat corrections can build on it.

The file is a database of 20-byte records keyed by type (block + category) and id, in no order. The reader scans every slot once, skips deleted ones (first byte `0xFF`), and files each record under its block and id; category 15 player records go to the honors. Mappings and tuples come out in id order, the `.idx` order, since the game reuses deleted slots.

### What this package does

- Reads every record of a `.dat` into a typed model.
- Reads values signed, as the game shows them: a total past 32,767 reads negative. Field goal ranges and the game score are split from the unsigned 16 bits, each byte 0-255.
- Leaves out leftover memory (the values past a category's last one, and the nominee's value 0) and punting's value 3, always 0.
- `GameDetails`: opponent and score are the team's own, in its opponents' blocks too: the last game's, or in season blocks the latest regular-season game's; the other values are the block's own.
- `HallOfFameNominee.year_elected` is `None` while the file holds 0.
- Decodes the honor ids:
  - Player of the Game: `game` is id − 1; id 99 is the Player of the Week.
  - All-Pro: id = (position + 1) + conference × 16 + pick × 256; id 4096 is the Coach of the Year.
  - Award: id = code + (year mod 100) × 256; codes 90 MVP, 91 and 93 offensive and 92 and 94 defensive player of the year (conference 0, then 1), 99 rookie of the year; `year` keeps the file's two digits.
- Validates the header and each record (the checks above).

### What this package does NOT do

- Read or write the `.idx`; a scan of the slots finds every record.
- Write the `.dat` (a later writer, for stat corrections).
- Add anything up: no totals, net touchdowns or points; the caller does that.
- Name players or teams, or check ids against the `.pyr` or `.lge`.
- Follow the deleted-slot list, or read the header's other bytes.

See [formats/stats.md](formats/stats.md) for the format.

### Testing

- `tests/unit/fbpro98_stats/test_reader.py` — real 2047 PNFL files (checked against their `.lge`), every category and honor from built bytes, every check at its limit and one past it.

Fixtures in `tests/unit/fbpro98_stats/data/` are real game files; the test matrix is [tests/unit/fbpro98_stats/README.md](../tests/unit/fbpro98_stats/README.md).
