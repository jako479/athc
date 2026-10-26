# fbpro98-pyr

Library for reading the players from a Front Page Sports Football Pro '98 league's player file (`.pyr`).

## Features

- `.pyr` reader for every league, stock and custom
- Every player by id: names, position and group, years, injury, height and weight, potential and actual ratings
- The header fields and the file's coding table, so a writer can put the file back
- A mutable model with `validate()`, which checks every rule the spec states
- In-memory parser (`parse_pyr`)

## Setup

```bash
uv sync
```

## Usage

```python
from athc.fbpro98_pyr import Position, read_pyr

pyr = read_pyr("PNFL", r"E:\SIERRA\FbPro98")      # reads PNFL.pyr in that folder

player = pyr.players[6283]
player.first_name, player.last_name              # "C. J.", "Stroud"
player.position                                  # Position.QB
player.actual.speed                              # 81, the rating the game shows
player.potential.speed                           # 81, not shown in the game
player.years                                     # 5
player.injury.level                              # 0: healthy

for player in pyr.players.values():              # every player, in id order
    ...
[p for p in pyr.players.values() if p.position is Position.K]
```

The values shown are the PNFL's after week 6 of 2049. Ids stay numbers: the `.lge` rosters and the `.dat` stats name players by them. `parse_pyr(buffer)` is the bytes-in entry point; `read_pyr` builds the path from the league name and its folder and wraps file I/O.

## API

- `read_pyr(league, league_dir)` reads `<league_dir>/<league>.pyr` and returns a `PyrFile`; `parse_pyr(buffer, path)` parses raw bytes, `path` only naming the source in errors (`<path>: <reason>`).
- `PyrFile`: `key`, `name` and `unknown` (the header; `unknown` is its last six bytes, as read), `coding_table` (plain byte value to the byte written to disk; the entries the file's ids reveal, all 256 with 256 or more players) and `players`, a dict by player id in id order. `validate()` raises `ValueError` on the first rule broken, naming the field and the value (`player 100: years: Must be 0-255, got 256`).
- `Player`: `id`, `first_name`, `last_name`, `position` (a `Position`), `group`, `years`, `injury`, `height`, `weight`, `potential` and `actual` (each a `Ratings`), `unknown` (the six bytes at 0x36, as read). Height and weight are 0 except for the newest draft class.
- `Position`: an `IntEnum` of the file's codes, `QB` = 0 to `P` = 14. `GROUPS`: the position groups the spec's table lists.
- `Ratings`: `acceleration`, `agility`, `discipline`, `endurance`, `hands`, `intelligence`, `speed`, `strength`, 0-99, in file order.
- `Injury`: `level` (0 is healthy), `injury` (the name index into `injury.dat`), `week` (week injured − 1, as stored). The injury and week stay after the player heals.
- The model is mutable: assign a field, then `validate()`. Every class is a plain dataclass; `players` and `coding_table` are dicts.
- A name is the text up to its NUL, or the whole 13 bytes when it has none; the header name reads the same way.
- `validate()` checks: `key` fits a u16; `name` and both player names are at most 13 characters; the header's `unknown` is 6 bytes; the coding table's values are bytes and no two plain values share a disk byte; the players are keyed 100, 101, ... in order and each key is its player's `id`; every rating is 0-99; `position` is one of the codes; `group` is one of the groups the spec's table lists (0, 10, 13, 14, 15, 16, 17, 18, 19); `years`, `height`, `injury.injury` and `injury.week` fit a u8; `weight` and `injury.level` fit a u16; the player's `unknown` is 6 bytes.
- Not checked, because real files break them: a position paired with its group as the spec's table has it, potential at or above actual, the unknown bytes of the header or a record being zero.
- `InvalidPyrError`, the first problem in file order: empty file; shorter than the 60-byte header; a size that is not the header plus whole 60-byte records; more records than 16-bit ids; a header byte the spec says is zero that is not (the header's six unknown bytes are kept as read, never checked); a plain id byte written two ways, or one disk byte standing for two plain values; a record byte the ids do not reveal; a position outside the codes; then whatever `validate()` finds.

## Testing

```bash
uv run pytest
```

## How it works

### Module layout

```
src/athc/fbpro98_pyr/
├── __init__.py    # public API re-exports
├── model.py       # PyrFile, Player, Position, Ratings, Injury; validate()
├── schema.py      # header and record offsets, sizes, structs
└── reader.py      # read_pyr / parse_pyr; InvalidPyrError
```

The model is one file object holding the header fields, the coding table and the players by id. Each player holds its two rating sets and its injury as small dataclasses. Everything is mutable, edited by assignment ([architecture.md](architecture.md#file-libraries)), and checked by `PyrFile.validate()`, which the reader calls last; a model built or edited in Python is checked the same way.

### What this package does

- Reads any league's `.pyr` into a typed model, one `Player` per record, keyed by id.
- Knows the `.pyr` extension: `read_pyr(league, league_dir)` reads `<league_dir>/<league>.pyr`.
- Learns the coding table from the file itself (spec section 3): record i holds player id 100 + i, so the first two bytes of every record show what two plain values are written as; with 256 or more players the low id byte covers every value. One table must come out: a plain value written two ways, or a disk byte standing for two plain values, is an error naming both records.
- Decodes the whole body in one `bytes.translate` over the inverse table, after checking that every disk byte is one the ids revealed; a byte that is not is an error naming the record and the offset, never a guessed value.
- Checks the size and the header's zero bytes (its six unknown bytes are kept as read), learns the table, unpacks each record with one `Struct`, then checks every value rule the spec states through `validate()`.
- Keeps what a writer needs: the header's key, name and six unknown bytes, the coding table, and the six unknown bytes of each record.

### What this package does NOT do

- Write `.pyr` files.
- Check a player's group against their position, or potential against actual: real files break both.
- Name injuries (`injury.dat`), place players on rosters (`.lge`) or read stats (`.dat`).
- Know where a league's files are; the caller supplies the folder.

See [formats/pyr.md](../formats/pyr.md) for the format.

### Testing

- `tests/unit/fbpro98_pyr/test_reader.py` — real fixtures (the PNFL after week 6 of 2049, the spec's sample; the smallest stock league; the stock league the spec names; a stock league of the old layout, with `FF FF` first in the header's and every record's unknown bytes), the spec's worked examples and appendix table pinned, built bytes for each check and limit.
- `tests/unit/fbpro98_pyr/test_model.py` — `validate()`, each rule at its limit and one past it on models built in Python.

Fixtures in `tests/unit/fbpro98_pyr/data/` are real game files.
