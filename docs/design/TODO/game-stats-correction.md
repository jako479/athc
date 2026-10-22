# Proposal — game stats correction

Status: proposal; nothing implemented.

## Why

The game records some stats wrong, and athc should fix them in `<league>.dat` (spec: [formats/stats.md](../../formats/stats.md)). This doc says what a fix touches, lays out the library and says how it reads and writes the file; [standings-net-touchdowns.md](standings-net-touchdowns.md) covers net touchdowns in the standings.

## The file

- No game history: the file keeps only running totals (last game, season, career), so a fix adds or subtracts an amount from each total; nothing can be recalculated from the games.
- Last-game records are deleted each week, so they matter only before the next week is played; season records last until the next season; career records are permanent.
- "Long" is the longest play, so it can't simply be adjusted; field goal ranges pack made and attempts into one value.

## Layout

- One package, `fbpro98_stats`, never two installable ones.
- Two subpackages inside it, side by side: `ctree/`, the database layer, and `stats/`, the football layer.
- `fbpro98_stats/__init__.py` exposes the football functions; subcommands never see `ctree`.

```
src/athc/fbpro98_stats/
├── __init__.py     # the library's API
├── ctree/          # the database layer: the files as bytes and raw records; no football knowledge
└── stats/          # the football layer: named stats, the game's rules, one function per bug
```

## One way in

- Both uses read the whole file into memory, work on it there and, when something changed, write the whole file back; the file is small, so this is fast, and one decoder serves everything.
- Net touchdowns: `athc standings` reads the file, builds a record per team (team id, touchdowns scored, touchdowns allowed) and passes the list to `fbpro98_standings`, which never sees the rest.
- Corrections: a fix reads the file, changes records in memory, drops one that goes all-zero, adds one that is missing, and writes the file back.
- Rewriting a small local file whole is the mainstream choice; seeking and overwriting bytes in place belongs to large databases, and is easy to get wrong.

## The database layer, `ctree/`

- Reads the `.dat` and `.idx` whole, as headers and raw records (id, stat type, eight 2-byte values), and writes them back whole.
- Knows nothing of players, teams or what a value means, and decides nothing; given an all-zero record, it writes it.
- Writes atomically: the whole file goes to a temporary file beside the original, which then replaces it in one step, so a crash mid-write leaves the original untouched.
- No transactions: one user, one small local file, and the atomic rewrite makes a fix that touches several records all-or-nothing.

```python
import os
from pathlib import Path


def write_file(path: Path, data: bytes) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp_path.write_bytes(data)
        os.replace(tmp_path, path)  # atomic: the game only ever sees a whole file
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
```

## The football layer, `stats/`

- Turns a raw record into named stats and back; reading the file and fixing a record both go through it.
- Holds the game's rules: a player record carries only a player id and a team record only a team id, so the file never links a player to a team; and no all-zero record exists, a rule of the game, not of the database.
- Applies the rules in memory: a record that goes all-zero is dropped, a stat with no record gets one added, and the whole set goes back to `ctree` to write.

## Net touchdowns

`fbpro98_standings` takes only what it needs, so a change to the stats file never reaches it.

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class TeamTouchdownRecord:
    team_id: int
    touchdowns_scored: int
    touchdowns_allowed: int

    @property
    def net_touchdowns(self) -> int:
        return self.touchdowns_scored - self.touchdowns_allowed
```

`athc standings` does the mapping; a sketch, where `touchdowns()` sums a team's touchdowns across the categories:

```python
stats = fbpro98_stats.read_stats(league, league_dir)
records = [
    TeamTouchdownRecord(
        team_id=team_id,
        touchdowns_scored=touchdowns(stats.team_season[team_id]),
        touchdowns_allowed=touchdowns(stats.opponents_season[team_id]),
    )
    for team_id in stats.team_season
]
fbpro98_standings.calculate_net_touchdowns(records)
```

## Corrections

- Steps: back up the `.dat` and `.idx`, describe the fix (game, player or team, stat, change), read the file, apply the same change to every record that counted it, then write the file back.
- One function per game bug, named for it: `convert_run_to_sack(player_id, team_id, opponent_id, yards)`. The caller passes the ids because the file doesn't link a player to a team or a team to its opponent.
- A function that changes a player stat changes the team's matching stat and the opposing team's opponents' stat in the same call, so they never drift; a team-only stat (first downs, third and fourth downs, penalties, time of possession) touches only the team's and the opponents' records.
- A regular-season fix touches last game, season and career; a playoff fix touches last game only.
- A sack counted as a quarterback run: the quarterback's rushing record loses one attempt and gains the sack yards; the team's sacked record gains one sack and the same yards; the opposing team's opponents' records change the same way. A rushing record that goes all-zero is dropped; a missing sacked record is added; an existing one is updated.
- Applying the same fix twice doubles the change, so record which fixes were applied.

A sketch, for one tier; a regular-season fix does this for last game, season and career:

```python
def convert_run_to_sack(player_id: int, team_id: int, opponent_id: int, yards: int) -> None:
    """Rescore a quarterback run as a sack; `yards` is what the sack lost, positive."""
    records = read_entire_file()

    # The quarterback: one attempt fewer, the lost yards back.
    qb_rush = records.find(player_id, stat_type="RUSHING")
    qb_rush.attempts -= 1
    qb_rush.yards += yards
    if qb_rush.is_all_zero():
        records.remove(qb_rush)

    # The team: one more sack and the yards; a first sack needs a new record.
    team_sacks = records.find(team_id, stat_type="TEAM_SACKS")
    if team_sacks is None:
        records.add(TeamSackRecord(team_id=team_id, count=1, yards=yards))
    else:
        team_sacks.count += 1
        team_sacks.yards += yards

    # The opposing team's opponents' rushing and sacks records: the same two changes.

    write_entire_file(records)
```

## Open questions

- Whether the game recalculates Hall of Fame points or awards from the stats.
- Whether the `.idx` is rebuilt whole from the records on every write or edited entry by entry for the records dropped and added.
