# .dat and .idx - Front Page Sports Football Pro '98 Statistics File Format

- **Owner:** none yet
- **Encoding:** Integers little-endian, except the index keys (big-endian). Not masked; unused bytes hold leftover memory.

A `.dat` holds a league's player and team statistics: last game, season and career. The `.idx` beside it is a B-tree index of the `.dat` records by type and id. Both are named after their league (`PNFL.dat`, `PNFL.idx`) and sit in the game folder. One layout in every sampled pair, stock (1994-1997) and custom; a fresh stock league ships an empty pair (140 and 512 bytes). Sample: `PNFL.dat` (17,002 records, 348,160 bytes) and `PNFL.idx` (225,280 bytes), season 2049 after 6 weeks.

---

## 1. File Layout

`.dat`: a 140-byte header, then 20-byte slots back to back. A slot holds a record or is deleted. Records are not sorted; the index or a scan of every slot finds them.

```
header
slot 0
slot 1
...
unused, all 0xFF
```

| Offset            |   Size | Name   | Description                      | Section |
| :---------------- | -----: | :----- | :------------------------------- | :------ |
| 0x0000            |    140 | Header | Header                           | 2       |
| 0x008C            |     20 | Slot 0 | Record, or a deleted slot        | 3, 6    |
| 0x00A0            |     20 | Slot 1 | Record, or a deleted slot        | 3, 6    |
| ...               |    ... | ...    | Slot n at 0x8C + 20 × n          | 3, 6    |
| last slot end + 1 | varies | Unused | All `0xFF` to the end of the file |         |

`.idx`: 512-byte blocks. Block 0 is the header; the others are tree nodes or unused.

| Offset    | Size | Name   | Description                                      | Section |
| :-------- | ---: | :----- | :----------------------------------------------- | :------ |
| 0x0000    |  512 | Header | Block 0                                          | 7       |
| 0x200 × n |  512 | Node   | Block n, a tree node; unused blocks are all `0xFF` | 8     |

Both files are a multiple of 4,096 bytes once they hold records: `PNFL.dat` is 85 × 4,096, `PNFL.idx` 55 × 4,096.

---

## 2. .dat Header (140 bytes)

Starts at 0x0000. Bytes 0x28-0x8B are the same in every sample except 0x30.

| Offset | Size | Type   | Name         | Description                                                                         |
| -----: | ---: | :----- | :----------- | :---------------------------------------------------------------------------------- |
|   0x00 |    4 | u32    | File end     | File size − 1 (`348159`)                                                            |
|   0x04 |    4 | u32    | Deleted list | Offset of the first deleted slot (section 6); `0` when none                         |
|   0x08 |    4 | u32    | Slots end    | Offset of the last byte of the last slot; slots = (value − 139) / 20 (`17362`)      |
|   0x0C |    8 | u8[8]  | Zero         |                                                                                     |
|   0x14 |    4 | u32    | Unknown      | `565021` in `PNFL.dat`; equals the record count in every sample with no deleted slot |
|   0x18 |    4 | u32    | Records      | Records in use (`17002`); also the `.idx` entry count                               |
|   0x1C |   12 | u8[12] | Zero         |                                                                                     |
|   0x28 |    2 | u16    | Unknown      | `0x0081`                                                                            |
|   0x2A |    2 | u16    | Zero         |                                                                                     |
|   0x2C |    2 | u16    | Record size  | `20`                                                                                |
|   0x2E |    2 | u16    | Unknown      | `4096`; a `.dat` with records is a multiple of it                                   |
|   0x30 |    2 | u16    | Unknown      | `1`; `0` in `1994.DAT` and `NFLPA93.dat`                                            |
|   0x32 |    8 | u8[8]  | Zero         |                                                                                     |
|   0x3A |    2 | u16    | Unknown      | `1`                                                                                 |
|   0x3C |    2 | u16    | Unknown      | `512`                                                                               |
|   0x3E |    2 | u16    | Unknown      | `1`                                                                                 |
|   0x40 |   32 | u8[32] | Zero         |                                                                                     |
|   0x60 |    1 | u8     | Unknown      | `0xFF`                                                                              |
|   0x61 |    3 | u8[3]  | Zero         |                                                                                     |
|   0x64 |    1 | u8     | Unknown      | `1`                                                                                 |
|   0x65 |   27 | u8[27] | Zero         |                                                                                     |
|   0x80 |   12 | u8[12] | Fill         | All `0xFF`                                                                          |

An empty `.dat` is this header alone: file end and slots end are both `139`, the counts `0`.

---

## 3. Stat Record (20 bytes)

Starts at 0x8C + 20 × slot.

| Offset | Size | Type   | Name   | Description                                                                                 |
| -----: | ---: | :----- | :----- | :------------------------------------------------------------------------------------------ |
|   0x00 |    2 | u16    | Type   | Block + category (sections 4 and 5); `0`-`215`                                              |
|   0x02 |    2 | u16    | Id     | Player id (`.pyr`) in player blocks, team number (`.lge`) in team blocks                    |
|   0x04 |   16 | s16[8] | Values | Values 0-7, by category (section 5); values past a category's last one hold leftover memory |

Each type and id pair appears once. A missing record means zero: Denver's last game has no field goal or two-point record, and its 34 points add up without them (section 5).

Values are signed: rushing yards go below zero. Yard totals above 32,767 wrap below zero, and the game shows them that way: Mitch Wishnowsky's printed bio gives his career punting yards as `-32556`.

Example, `PNFL.dat` at 0x04ACA4, C. J. Stroud's season passing:

```
0x00  23 00   type          = 35 (player season, passing)
0x02  8b 18   id            = 6283 (C. J. Stroud)
0x04  1a 01   attempts      = 282
0x06  3c 07   yards         = 1852
0x08  32 00   long          = 50
0x0A  0c 00   touchdowns    = 12
0x0C  a5 00   completions   = 165
0x0E  07 00   interceptions = 7
0x10  0a 00   sacked        = 10
0x12  28 00   sack yards    = 40
```

---

## 4. Blocks

Type = block base + category (section 5).

| Types       | Block                | Id          |
| :---------- | :------------------- | :---------- |
| `0`-`17`    | Player, last game    | Player id   |
| `32`-`49`   | Player, season       | Player id   |
| `64`-`81`   | Player, career       | Player id   |
| `96`-`113`  | Team, last game      | Team number |
| `130`-`147` | Team, season         | Team number |
| `164`-`181` | Opponents, last game | Team number |
| `198`-`215` | Opponents, season    | Team number |

- Last game is the team's latest game: week 6 for all 18 teams in `PNFL.dat`.
- A team's opponents' blocks hold what its opponents did against it: each team's opponents' last-game records equal its week 6 opponent's own team records, in every category but 16.
- League-wide, the player season records add up to the team season records in categories 0-11, 13 and 17 (longs aside).
- Stroud's last-game passing record equals Denver's team last-game passing record value for value.

---

## 5. Categories

Values are listed in order from value 0; the values after the last one listed hold leftover memory. Mostly: the positions that hold the category in `PNFL.dat`, most common first.

| Category | Stat                  | Values                                                                                    | Mostly             |
| -------: | :-------------------- | :---------------------------------------------------------------------------------------- | :----------------- |
|      `0` | Extra points          | attempts, made                                                                            | K                  |
|      `1` | Field goals           | long, then 5 distance ranges (section 5.1)                                                | K                  |
|      `2` | Rushing               | attempts, yards, long, touchdowns                                                         | HB, WR, QB, FB     |
|      `3` | Passing               | attempts, yards, long, touchdowns, completions, interceptions, sacked, sack yards         | QB                 |
|      `4` | Receiving             | receptions, yards, long, touchdowns                                                       | WR, HB, TE, FB     |
|      `5` | Interceptions         | interceptions, yards, long, touchdowns                                                    | CB, LB, S          |
|      `6` | Punting               | punts, yards, long, unknown (always `0`), unknown, unknown, return yards, touchbacks       | P                  |
|      `7` | Punt returns          | returns, yards, long, touchdowns, unknown (`0`-`29`)                                      | WR, CB             |
|      `8` | Kick returns          | returns, yards, long, touchdowns                                                          | WR, HB, T, TE      |
|      `9` | Fumbles               | fumbles                                                                                   | WR, HB, QB         |
|     `10` | Fumble recoveries     | recoveries, yards, long, touchdowns                                                       | every position     |
|     `11` | Sacks                 | sacks                                                                                     | LB, DE, CB, S, DT  |
|     `12` | Unknown               | one count, `1`-`3`; career block only                                                     | LB, DE, S, DT, CB  |
|     `13` | Tackles               | tackles                                                                                   | every position     |
|     `14` | Unknown               | section 5.2                                                                               | every position     |
|     `15` | Unknown               | section 5.2                                                                               |                    |
|     `16` | Unknown               | section 5.2                                                                               |                    |
|     `17` | Two-point conversions | attempts, made                                                                            | WR, HB, QB, TE, FB |

Checked against `PNFL.lge` and the game's printouts:

- Scores: for all 18 teams, season and last game, 6 × touchdowns (categories 2, 3, 5, 7, 8 and 10) + extra points made + 3 × field goals made + 2 × two-point conversions made equals the points in the schedule. Denver's week 6: 1 rushing and 4 passing touchdowns plus 4 extra points make 34, its score against Cincinnati.
- Touchdowns equal extra-point plus two-point attempts for 16 teams; the other two have one touchdown with no try.
- League-wide season totals: completions = receptions (2,378), passing yards = receiving yards (27,573), passing touchdowns = receiving touchdowns (182), interceptions thrown = interceptions (87), sacked = sacks (212), punting return yards = punt return yards (1,550).
- Wishnowsky's bio, printed before this season, shows career punts 769, yards `-32556`, touchbacks 215 and blocked 0; his career record less his season record gives the same punts, yards and touchbacks.
- Denver's defenders have at least the career tackles and sacks of a career report printed in 2025.

### 5.1 Field Goal Ranges

Values 1-5 of category 1 each hold two bytes: low byte made, high byte attempts. Attempts are at or above made in every record, and the made bytes are the field goals of the score check.

| Value | Range (yards) |
| ----: | :------------ |
|     1 | under 20      |
|     2 | 20-29         |
|     3 | 30-39         |
|     4 | 40-49         |
|     5 | 50 and over   |

The ranges fit the long in every record: in all 130 records with a make, the long falls in the highest range with a make.

Example, Canon Rooker (1333), career: long `51`; ranges `00 02`, `10 14`, `26 33`, `1d 2f`, `04 06`: 0 of 2, 16 of 20, 38 of 51, 29 of 47, 4 of 6.

### 5.2 Categories 14-16

Mapped only in part. What is known:

- Category 14, team blocks: four counts; value 0 = value 1 + value 2 + value 3 in all 72 team records, about 21 per game (Denver's last game: 26 = 4 + 21 + 1).
- Category 14, player blocks: every position; the records do not add up across blocks (Wishnowsky's season and career records are both `0 1 70 64 0 0 7 0`).
- Category 15, team blocks: five counts; value 0 equals category 14's value 0, value 2 ≤ value 1 and value 4 ≤ value 3 in all 72 team records (Denver's season: `145 92 45 14 9`).
- Category 15, player blocks: the ids are mostly not player ids (1-9 and 99 in the last-game block, up to 4,096 in season, 4,954-12,387 in career); player ids sit among the values (last-game record 3 holds 6283, Stroud, at value 1).
- Category 16, team blocks: value 0 is the latest opponent's team number, the same in the last-game and season records; value 3 is time of possession in seconds: the two teams of each week 6 game add up to 3,600, or 3,955 in the overtime game. Values 1, 2, 4 and 5 vary. This is the one category where a team's opponents' last-game record differs from its opponent's own record.
- Category 16, player blocks: five last-game records with one count (four defensive backs and an offensive tackle); no season records; career records hold a year (`2042`-`2049`) at value 2 and, in 33 of 34, the player's own id at value 0.

---

## 6. Deleted Slots

A deleted slot starts with `0xFF`, which no type uses. The deleted slots form a list headed by the header's deleted list offset (0x04).

| Offset | Size | Type   | Name     | Description                                        |
| -----: | ---: | :----- | :------- | :------------------------------------------------- |
|   0x00 |    1 | u8     | Mark     | `0xFF`                                             |
|   0x01 |    4 | u32    | Next     | Offset of the next deleted slot; `0` ends the list |
|   0x05 |   15 | u8[15] | Leftover |                                                    |

`PNFL.dat` has 360 deleted slots, all on the list: 17,362 slots − 360 = 17,002 records. The list starts at 0x04F330: `ff 3c 32 00 00`, next 0x00323C.

---

## 7. .idx Header (512 bytes)

Block 0, starts at 0x0000. Bytes 0x28-0x1FF are the same in every sample except 0x30 and 0x48.

| Offset | Size | Type    | Name       | Description                                                                   |
| -----: | ---: | :------ | :--------- | :---------------------------------------------------------------------------- |
|   0x00 |    4 | u32     | File end   | File size − 1 (`225279`)                                                      |
|   0x04 |    4 | u32     | Unknown    | `0` in every sample                                                           |
|   0x08 |    4 | u32     | Blocks end | Offset of the last byte of the last block in use (`0x363FF`: blocks 0-433)     |
|   0x0C |   12 | u8[12]  | Zero       |                                                                               |
|   0x18 |    4 | u32     | Entries    | Leaf entries; equals the `.dat` record count (`17002`)                        |
|   0x1C |    4 | u32     | Root       | Offset of the root node (`0x8200`, block 65); `0` when empty                  |
|   0x20 |    8 | u8[8]   | Zero       |                                                                               |
|   0x28 |    2 | u16     | Unknown    | `0x0081`, as in the `.dat` header                                             |
|   0x2A |    2 | u16     | Block size | `512`                                                                         |
|   0x2C |    2 | u16     | Zero       |                                                                               |
|   0x2E |    2 | u16     | Unknown    | `4096`; an `.idx` with entries is a multiple of it                            |
|   0x30 |    2 | u16     | Unknown    | `1`; `0` in `1994.IDX` and `NFLPA93.idx`                                      |
|   0x32 |    2 | u16     | Zero       |                                                                               |
|   0x34 |    2 | u16     | Unknown    | `484`; a node holds at most 60 entries (480 bytes) in `PNFL.idx`              |
|   0x36 |    2 | u16     | Unknown    | `494`, which is 512 less the 18-byte node header                              |
|   0x38 |    4 | u8[4]   | Zero       |                                                                               |
|   0x3C |    2 | u16     | Unknown    | `0x0220`                                                                      |
|   0x3E |    2 | u16     | Unknown    | `1`                                                                           |
|   0x40 |    2 | u16     | Unknown    | `1`                                                                           |
|   0x42 |    2 | u16     | Key size   | `4`                                                                           |
|   0x44 |    4 | u8[4]   | Zero       |                                                                               |
|   0x48 |    4 | u32     | First leaf | `0x200` in every sample with entries, the leftmost leaf in each; `0` when empty |
|   0x4C |   18 | u8[18]  | Zero       |                                                                               |
|   0x5E |    2 | u16     | Unknown    | `0x0080`                                                                      |
|   0x60 |    1 | u8      | Unknown    | `0xFF`                                                                        |
|   0x61 |   31 | u8[31]  | Zero       |                                                                               |
|   0x80 |  384 | u8[384] | Fill       | All `0xFF`                                                                    |

An empty `.idx` is this block alone: file end and blocks end are both `511`, root and first leaf `0`.

---

## 8. Index Node (512 bytes)

Starts at 0x200 × block. An 18-byte header, then the entries, sorted by key. Bytes after the last entry are leftover.

| Offset | Size | Type     | Name     | Description                                                                 |
| -----: | ---: | :------- | :------- | :-------------------------------------------------------------------------- |
|   0x00 |    4 | u32      | Next     | Offset of the next node on the same level, left to right; `0` on the last   |
|   0x04 |    4 | u32      | Previous | Offset of the previous leaf; `0` on the first leaf and on every non-leaf node |
|   0x08 |    2 | u16      | Entries  | Entry count; at most 60 in `PNFL.idx`                                       |
|   0x0A |    2 | u16      | Bytes    | 8 × entries                                                                 |
|   0x0C |    5 | u8[5]    | Zero     |                                                                             |
|   0x11 |    1 | u8       | Leaf     | `1` leaf, `0` non-leaf                                                      |
|   0x12 |  8×n | entry[n] | Entries  | n = the entry count                                                         |

Entry (8 bytes):

| Offset | Size | Type   | Name    | Description                                                             |
| -----: | ---: | :----- | :------ | :---------------------------------------------------------------------- |
|   0x00 |    4 | u32    | Pointer | Leaf: `.dat` offset of the record. Non-leaf: `.idx` offset of the child |
|   0x04 |    2 | u16 BE | Type    | Record type, big-endian                                                 |
|   0x06 |    2 | u16 BE | Id      | Record id, big-endian                                                   |

- The key is type then id, so entries sort by type, then id.
- Leaves hold one entry per record; all 17,002 in `PNFL.idx` point at their record.
- A non-leaf key is at or above every key under its child: equal to the child's last key in 416 of 432 entries in `PNFL.idx`, above it in 14; the last entry of each non-leaf level is `FF FF FF FF`.
- Lookup: from the root, follow the first entry whose key is at or above the wanted key; in the leaf, the entry with that key points at the record. This finds all 17,002 records in `PNFL.idx`.
- `PNFL.idx`: root block 65, 11 non-leaf nodes, 421 leaves; blocks 1-433 in use, 434-439 unused.

Example, `PNFL.idx` block 55, entry 20, at 0x6EB2: Stroud's season passing.

```
0x00  a4 ac 04 00   pointer = 0x04ACA4 (the record in section 3)
0x04  00 23         type    = 35
0x06  18 8b         id      = 6283
```

---

## 9. Open Questions

- `.dat` header bytes 0x14, 0x28, 0x2E, 0x30, 0x3A-0x3F, 0x60 and 0x64; `.idx` header bytes 0x04, 0x28, 0x2E, 0x30, 0x34-0x37, 0x3C-0x41, 0x5E and 0x60
- Punting values 3-5, and which one is the blocked count the bio shows
- Punt return value 4
- Category 12: a count for defenders, career block only; no season records, and this season's scores add up without safeties
- Categories 14 and 15, and the rest of 16 (section 5.2); whether team category 14 is first downs (total, then three kinds) and category 15 third and fourth downs (attempts, conversions)
- The exact field goal range bounds
- Whether the game reuses deleted slots before growing the file, and what it does with a missing or stale `.idx`
