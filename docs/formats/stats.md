# .dat and .idx - Front Page Sports Football Pro '98 Statistics File Format

- **Owner:** FBPro98 Stats Library
- **Encoding:** Integers little-endian, except the index keys (big-endian). Not masked; unused bytes hold leftover memory.

A `.dat` holds a league's player and team statistics (last game, season and career), awards and Hall of Fame records. The `.idx` beside it is a B-tree index of the `.dat` records by type and id. The pair is a FairCom c-tree database; if it will not open, the game deletes both files and starts empty. Both are named after their league (`PNFL.dat`, `PNFL.idx`) and sit with the league's other files. Stock (1994-1997) and custom leagues use the same layout; a fresh stock league ships an empty pair (140 and 512 bytes).

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

Both files are a multiple of 4,096 bytes once they hold records.

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
|   0x2E |    2 | u16    | Growth       | `4096`, the file's growth step; a `.dat` with records is a multiple of it            |
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
|   0x02 |    2 | u16    | Id     | Player id (`.pyr`) in player blocks, team number (`.lge`) in team blocks; category 15 player records have their own ids (section 5.2) |
|   0x04 |   16 | s16[8] | Values | Values 0-7, by category (section 5); values past a category's last one hold leftover memory |

Each type and id pair appears once. A missing record means all its values are zero. In the 2047 PNFL season files no record has all eight values zero, but a Hall of Fame points record can hold a zero count, conference and points.

Values are signed: rushing yards can go below zero. Totals above 32,767 wrap below zero, and the game shows them that way.

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

- Last game is the team's latest game.
- Playoff games update the last-game blocks only, never season, career or awards.
- Each week the game deletes every last-game record; each season, every season record but the All-Pro team (category 15).
- A team's opponents' blocks hold what its opponents did against it.

---

## 5. Categories

Values are listed in order from value 0; the values after the last one listed hold leftover memory.

| Category | Stat                  | Values                                                                                    |
| -------: | :-------------------- | :---------------------------------------------------------------------------------------- |
|      `0` | Extra points          | attempts, made                                                                            |
|      `1` | Field goals           | long, then 5 distance ranges (section 5.1)                                                |
|      `2` | Rushing               | attempts, yards, long, touchdowns                                                         |
|      `3` | Passing               | attempts, yards, long, touchdowns, completions, interceptions, sacked, sack yards         |
|      `4` | Receiving             | receptions, yards, long, touchdowns                                                       |
|      `5` | Interceptions         | interceptions, yards, long, touchdowns                                                    |
|      `6` | Punting               | punts, yards, long, `0` (always), blocked, returns, return yards, touchbacks              |
|      `7` | Punt returns          | returns, yards, long, touchdowns, fair catches                                            |
|      `8` | Kick returns          | returns, yards, long, touchdowns                                                          |
|      `9` | Fumbles               | fumbles                                                                                   |
|     `10` | Fumble recoveries     | recoveries, yards, long, touchdowns                                                       |
|     `11` | Sacks                 | sacks                                                                                     |
|     `12` | Safeties              | safeties                                                                                  |
|     `13` | Tackles               | tackles                                                                                   |
|     `14` | By block, section 5.2 | players: Hall of Fame points; teams: first downs                                          |
|     `15` | By block, section 5.2 | players: Player of the Game, All-Pro team, awards; teams: third and fourth downs          |
|     `16` | By block, section 5.2 | players: penalties, Hall of Fame nominee; teams: game details                             |
|     `17` | Two-point conversions | attempts, made                                                                            |

### 5.1 Field Goal Ranges

Values 1-5 of category 1 each hold two bytes: low byte made, high byte attempts. Each count wraps at 256.

| Value | Range (yards) |
| ----: | :------------ |
|     1 | 10-19         |
|     2 | 20-29         |
|     3 | 30-39         |
|     4 | 40-49         |
|     5 | 50 and over   |

Example, Canon Rooker (1333), career: long `51`; ranges `00 02`, `10 14`, `26 33`, `1d 2f`, `04 06`: 0 of 2, 16 of 20, 38 of 51, 29 of 47, 4 of 6.

### 5.2 Categories 14-16

These categories hold different values in player and team blocks. Opponents' blocks use the team layout.

Team and opponents' blocks:

| Category | Values                                                                                                                       |
| -------: | :--------------------------------------------------------------------------------------------------------------------------- |
|     `14` | first downs: total, rushing, passing, penalty                                                                                |
|     `15` | first downs, third-down attempts, third downs made, fourth-down attempts, fourth downs made                                   |
|     `16` | opponent's team number, penalties, penalty yards, time of possession in seconds, score (own × 256 + opponent's), fumbles lost |

Category 16's opponent and score are the team's own, in its opponents' blocks too: the last game's in last-game blocks, the latest regular-season game's in season blocks. The other values are the block's own, season totals in season blocks.

Player blocks:

| Category | Last game           | Season              | Career               |
| -------: | :------------------ | :------------------ | :------------------- |
|     `14` | Hall of Fame points | Hall of Fame points | Hall of Fame points  |
|     `15` | Player of the Game  | All-Pro team        | awards               |
|     `16` | penalties           | unused              | Hall of Fame nominee |

- Hall of Fame points: count, conference, points.
- Penalties: one count.
- Hall of Fame nominee: value 0 unused (holds leftover memory), value 1 points, value 2 year retired, value 3 year elected (`0` until elected).
- Category 15 records have their own ids, not player ids:

| Block     | Record             | Id                                                                                                                                                 | Values                            |
| :-------- | :----------------- | :------------------------------------------------------------------------------------------------------------------------------------------------- | :-------------------------------- |
| Last game | Player of the Game | game number + 1; `99` = Player of the Week                                                                                                         | points, player id, team, opponent |
| Season    | All-Pro team       | (position + 1) + conference × 16 + pick × 256; pick `0` consensus, `1` first team, `2`-`4` second team                                              | value 1: player id                |
| Season    | Coach of the Year  | `4096`                                                                                                                                             | value 1: team number              |
| Career    | Award              | code + (year mod 100) × 256; codes `90` MVP, `91` and `92` offensive and defensive player of the year of the first conference, `93` and `94` of the second, `99` rookie of the year | value 1: player id                |

---

## 6. Deleted Slots

A deleted slot starts with `0xFF`, which no type uses. The deleted slots form a list headed by the header's deleted list offset (0x04).

| Offset | Size | Type   | Name     | Description                                        |
| -----: | ---: | :----- | :------- | :------------------------------------------------- |
|   0x00 |    1 | u8     | Mark     | `0xFF`                                             |
|   0x01 |    4 | u32    | Next     | Offset of the next deleted slot; `0` ends the list |
|   0x05 |   15 | u8[15] | Leftover |                                                    |

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
|   0x2E |    2 | u16     | Growth     | `4096`, the file's growth step; an `.idx` with entries is a multiple of it     |
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
|   0x48 |    4 | u32     | First leaf | Offset of the leftmost leaf; `0` when empty                                   |
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
|   0x08 |    2 | u16      | Entries  | Entry count                                                                 |
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
- Leaves hold one entry per record.
- A non-leaf key is at or above every key under its child; the last entry of each non-leaf level is `FF FF FF FF`.
- Lookup: from the root, follow the first entry whose key is at or above the wanted key; in the leaf, the entry with that key points at the record.

Example, `PNFL.idx` block 55, entry 20, at 0x6EB2: Stroud's season passing.

```
0x00  a4 ac 04 00   pointer = 0x04ACA4 (the record in section 3)
0x04  00 23         type    = 35
0x06  18 8b         id      = 6283
```

---

## 9. Open Questions

- `.dat` header bytes 0x14, 0x28, 0x30, 0x3A-0x3F, 0x60 and 0x64; `.idx` header bytes 0x04, 0x28, 0x30, 0x34-0x37, 0x3C-0x41, 0x5E and 0x60
- Whether the game reuses deleted slots before growing the file, and what it does with a stale `.idx`
