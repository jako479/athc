# .dat and .idx - Front Page Sports Football Pro '98 Statistics File Format

- **Owner:** FBPro98 Stats Library
- **Encoding:** Integers little-endian, except the index keys (big-endian). Not masked; unused bytes hold leftover memory.
- **Sources:** the PNFL's files; the header field names from FairCom's c-tree file header as laid out in [HPCC-Platform's ctfile.hpp](https://github.com/hpcc-systems/HPCC-Platform/blob/community_7.12.0-1/system/jhtree/ctfile.hpp); deleted records, the serial number and the header size from the [c-tree Plus 6.0 manuals](https://archive.org/details/c-tree-plus-installation-guide) (1990); the game's rules from the [Sierra source notes](../research/sierra-source.md).

A `.dat` holds a league's player and team statistics (last game, season and career), awards and Hall of Fame records. The `.idx` beside it is a B-tree index of the `.dat` records by type and id. The pair is a FairCom c-tree Plus database in c-tree's standard (V6) file format, so both files start with its 128-byte file header. If the pair will not open, the game deletes both files and starts empty. Both are named after their league (`PNFL.dat`, `PNFL.idx`) and sit with the league's other files. Stock (1994-1997) and custom leagues use the same layout; a fresh stock league ships an empty pair (140 and 512 bytes).

---

## 1. File Layout

`.dat`: the 128-byte header (section 2), 12 bytes of fill, then 20-byte slots back to back from offset 140, the first multiple of 20 past the header. A slot holds a record or is deleted. Records are not sorted; the index or a scan of every slot finds them.

```
header
fill
slot 0
slot 1
...
unused, all 0xFF
```

| Offset            |   Size | Name   | Description                       | Section |
| :---------------- | -----: | :----- | :-------------------------------- | :------ |
| 0x0000            |    128 | Header | File header                       | 2       |
| 0x0080            |     12 | Fill   | All `0xFF`, up to the first slot  |         |
| 0x008C            |     20 | Slot 0 | Record, or a deleted slot         | 3, 6    |
| 0x00A0            |     20 | Slot 1 | Record, or a deleted slot         | 3, 6    |
| ...               |    ... | ...    | Slot n at 0x8C + 20 × n           | 3, 6    |
| last slot end + 1 | varies | Unused | All `0xFF` to the end of the file |         |

`.idx`: 512-byte blocks. Block 0 is the file header and fill; the others are tree nodes, freed nodes or unused.

| Offset    | Size | Name   | Description                                                        | Section |
| :-------- | ---: | :----- | :----------------------------------------------------------------- | :------ |
| 0x0000    |  128 | Header | File header                                                        | 2       |
| 0x0080    |  384 | Fill   | All `0xFF`, the rest of block 0                                    |         |
| 0x200 × n |  512 | Node   | Block n, a tree node or a freed node; unused blocks are all `0xFF` | 7       |

Both files grow by 4,096 bytes at a time (Growth = `4096`, header 0x2E), so each is a multiple of 4,096 once it holds records.

---

## 2. File Header (128 bytes)

Starts at 0x0000 in both files. It is c-tree's file header, with c-tree's names; a field only an index uses is `0` in the `.dat`, and one only a data file uses is `0` in the `.idx`. Bytes 0x28-0x7F are set when the file is created and never change, except First leaf (0x48); they are the same in every sample except File mode (0x30).

| Offset | Size | Type   | Name             | Description                                                                                                | `.dat`                  | `.idx`                 |
| -----: | ---: | :----- | :--------------- | :--------------------------------------------------------------------------------------------------------- | :---------------------- | :--------------------- |
|   0x00 |    4 | u32    | File end         | File size − 1                                                                                              | `348159`                | `225279`               |
|   0x04 |    4 | u32    | Delete stack     | Offset of the last deleted slot (section 6) or the last freed node (section 7); `0` when there is none              |                         |                        |
|   0x08 |    4 | u32    | Used end         | Offset of the last byte ever used; never decreases. `.dat` slots = (value − 139) / 20; `.idx` blocks = (value + 1) / 512  | `347379` (17,362 slots) | `0x363FF` (434 blocks) |
|   0x0C |    4 | u32    | Resource header  | `0`                                                                                                        |                         |                        |
|   0x10 |    4 | u32    | Last member      | `0`                                                                                                        |                         |                        |
|   0x14 |    4 | u32    | Serial number    | Count of records ever added, re-adds included; +1 per add, never decreases                                    | `565021`                | `0`                    |
|   0x18 |    4 | u32    | Entries          | `.dat`: records in use; `.idx`: index entries; the two are always equal                                                        | `17002`                 | `17002`                |
|   0x1C |    4 | u32    | Root             | Offset of the root node; `0` when empty                                                                    | `0`                     | `0x8200`               |
|   0x20 |    4 | u32    | File id          | `0`                                                                                                        |                         |                        |
|   0x24 |    4 | u32    | Server id        | `0`                                                                                                        |                         |                        |
|   0x28 |    2 | u16    | Version          | c-tree's configuration when the file was created; bits unknown                                            | `0x81`                  | `0x81`                 |
|   0x2A |    2 | u16    | Node size        |                                                                                                            | `0`                     | `512`                  |
|   0x2C |    2 | u16    | Record size      |                                                                                                            | `20`                    | `0`                    |
|   0x2E |    2 | u16    | Growth           | Bytes added each time the file grows                                                                       | `4096`                  | `4096`                 |
|   0x30 |    2 | u16    | File mode        | c-tree open-mode bits, `1` = shared; `0` in the 1994 and NFLPA93 pairs                                     | `1`                     | `1`                    |
|   0x32 |    2 | u16    | Permanent mode   | The file mode's permanent bits                                                                             | `0`                     | `0`                    |
|   0x34 |    2 | u16    | Leaf bytes       | Maximum entry bytes in a leaf node = 60 entries                                                                     | `0`                     | `484`                  |
|   0x36 |    2 | u16    | Non-leaf bytes   | Maximum entry bytes in a non-leaf node = 61 entries                                                            | `0`                     | `494`                  |
|   0x38 |    1 | u8     | Update flag      | `0` = clean; anything else marks the file corrupt                                                          | `0`                     | `0`                    |
|   0x39 |    1 | u8     | Key type         |                                                                                                            | `0`                     | `0`                    |
|   0x3A |    1 | u8     | Duplicates       | Duplicate-key flag; why the `.dat` holds `1` is unknown                                                    | `1`                     | `0`                    |
|   0x3B |    1 | u8     | Delete type      | Meaning unknown                                                                                            | `0`                     | `0`                    |
|   0x3C |    1 | u8     | Key padding      | The byte that pads short keys                                                                              | `0`                     | `0x20`                 |
|   0x3D |    1 | u8     | Flavor           | Byte-order code                                                                                            | `2`                     | `2`                    |
|   0x3E |    1 | u8     | Alignment        | `1` = byte                                                                                                 | `1`                     | `1`                    |
|   0x3F |    1 | u8     | Pointer size     |                                                                                                            | `0`                     | `0`                    |
|   0x40 |    2 | u16    | File type        | `0` = data file, `1` = index                                                                                 | `0`                     | `1`                    |
|   0x42 |    2 | u16    | Key size         |                                                                                                            | `0`                     | `4`                    |
|   0x44 |    2 | u16    | Members          | `0`                                                                                                        |                         |                        |
|   0x46 |    2 | u16    | Member number    | `0`                                                                                                        |                         |                        |
|   0x48 |    4 | u32    | First leaf       | Offset of the leftmost leaf; `0` when empty                                                                | `0`                     | `0x200`                |
|   0x4C |    4 | u32    | Superfile member | `0`                                                                                                        |                         |                        |
|   0x50 |    4 | u32    | Header position  | `0`                                                                                                        |                         |                        |
|   0x54 |    4 | u32    | Superfile header | `0`                                                                                                        |                         |                        |
|   0x58 |    4 | u32    | Time id          | `0`                                                                                                        |                         |                        |
|   0x5C |    2 | u16    | Superfile type   | `0`                                                                                                        |                         |                        |
|   0x5E |    2 | u16    | Mark entries     | Meaning unknown                                                                                            | `0`                     | `0x80`                 |
|   0x60 |    2 | u16    | Name length      | Maximum file name length at creation                                                            | `255`                   | `255`                  |
|   0x62 |    2 | u16    | Extended mode    | `0`                                                                                                        |                         |                        |
|   0x64 |    4 | u32    | Definition mask  | Meaning unknown                                                                                            | `1`                     | `0`                    |
|   0x68 |    4 | u32    | Transaction mark | `0`                                                                                                        |                         |                        |
|   0x6C |    4 | u32    | Header sequence  | `0`                                                                                                        |                         |                        |
|   0x70 |    4 | u32    | Time stamp       | `0`                                                                                                        |                         |                        |
|   0x74 |   12 | u8[12] | Reserved         | `0`                                                                                                        |                         |                        |

An empty `.dat` is the header and its fill alone (140 bytes): File end = `139`, Used end = `139`, Serial number = `0`, Entries = `0`. An empty `.idx` is block 0 alone: File end = `511`, Used end = `511`, Root = `0`, First leaf = `0`.

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

A deleted slot starts with `0xFF`, which no type uses. Deleted slots form a stack: Delete stack (0x04) holds the last deleted slot, and each deleted slot holds the one deleted before it.

| Offset | Size | Type   | Name     | Description                                                    |
| -----: | ---: | :----- | :------- | :------------------------------------------------------------- |
|   0x00 |    1 | u8     | Mark     | `0xFF`                                                         |
|   0x01 |    4 | u32    | Next     | Offset of the slot deleted before this one; `0` ends the stack |
|   0x05 |   15 | u8[15] | Leftover | Bytes 5-19 of the deleted record                               |

- A delete writes the mark and the link over the record's first 5 bytes, pushes the slot on the stack, removes the record's index entry and lowers Entries (0x18) by one; Serial number does not change.
- An add takes the slot on top of the stack; with the stack empty it takes the slot after Used end (0x08), growing the file by Growth (0x2E) bytes when that slot would pass File end. It raises Entries and Serial number (0x14) by one and inserts an index entry.
- A value change rewrites the record where it is and changes nothing else.
- The file never shrinks: Used end only grows, and a deleted slot stays until reused.

---

## 7. Index Node (512 bytes)

The index is a tree of nodes: the root (Root in the header) at the top, non-leaf nodes below it, and the leaves at the bottom; the PNFL's has three levels. A leaf's entries point at `.dat` records, one entry per record; a non-leaf node's entries point at the nodes below it. The nodes of each level are chained left to right by Next, and the leaves also right to left by Previous, so the first leaf (First leaf in the header) starts a walk through every record in key order. A lookup walks from the root down to the leaf that holds the key.

A node starts at 0x200 × block: an 18-byte header, then the entries, sorted by key. Bytes after the last entry are leftover.

| Offset | Size | Type     | Name     | Description                                                                 |
| -----: | ---: | :------- | :------- | :-------------------------------------------------------------------------- |
|   0x00 |    4 | u32      | Next     | Offset of the next node on the same level, left to right; `0` on the last   |
|   0x04 |    4 | u32      | Previous | Offset of the previous leaf; `0` on the first leaf and on every non-leaf node; `0xFFFFFFFF` on a freed node |
|   0x08 |    2 | u16      | Entries  | Entry count                                                                 |
|   0x0A |    2 | u16      | Bytes    | 8 × entries                                                                 |
|   0x0C |    5 | u8[5]    | Zero     |                                                                             |
|   0x11 |    1 | u8       | Leaf     | `1` = leaf, `0` = non-leaf                                                  |
|   0x12 |  8×n | entry[n] | Entries  | n = the entry count                                                         |

Entry (8 bytes):

| Offset | Size | Type   | Name    | Description                                                             |
| -----: | ---: | :----- | :------ | :---------------------------------------------------------------------- |
|   0x00 |    4 | u32    | Pointer | Leaf: `.dat` offset of the record. Non-leaf: `.idx` offset of the child |
|   0x04 |    2 | u16 BE | Type    | Record type, big-endian                                                 |
|   0x06 |    2 | u16 BE | Id      | Record id, big-endian                                                   |

- The key is type then id, so entries sort by type, then id.
- Leaves hold one entry per record; Entries (0x18) in the header is their total.
- A leaf holds at most 60 entries (Leaf bytes = `484`), a non-leaf node 61 (Non-leaf bytes = `494`).
- When a 61st entry must go into a full leaf, the leaf splits: the lower 31 of the 61 entries stay, and the upper 30 move to a new node (taken from the delete stack, else appended) linked after it on its level, with Previous = the split node and Next = the split node's old Next. The parent gets an entry for the split node with its new highest key, placed before the old entry, which now points at the new node. A full non-leaf node (61 entries) splits the same way, its upper half moving to the new node.
- A root split is not described: the root holds at most 61 entries and has never held more than 12 in any PNFL file, so it does not split at a league's size.
- A non-leaf key is at or above every key under its child; the last entry of each non-leaf level is `FF FF FF FF`.
- Lookup: from the root, follow the first entry whose key is at or above the wanted key; in the leaf, the entry with that key points at the record.
- A delete removes the entry at once; nodes are never merged, so a leaf can run down to a few entries.
- A leaf that runs empty is freed: its entry is removed from its parent, it is unlinked from its level, with Entries = `0`, Bytes = `0`, Previous = `0xFFFFFFFF` and Next = the node freed before it, and Delete stack (0x04) in the header points at it; its old entries stay as leftover. A node is taken from that stack before the file grows.

Example, `PNFL.idx` block 55, entry 20, at 0x6EB2: Stroud's season passing.

```
0x00  a4 ac 04 00   pointer = 0x04ACA4 (the record in section 3)
0x04  00 23         type    = 35
0x06  18 8b         id      = 6283
```
