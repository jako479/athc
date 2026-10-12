# .pyr - Front Page Sports Football Pro '98 Player File Format

- **Owner:** none yet
- **Encoding:** Integers little-endian; strings ASCII. Every byte after the header is coded (section 3).

A `.pyr` holds every player a league knows: names, ratings, position, years and injury. It is named after its league (`PNFL.pyr`) and sits in the game folder. One layout in every sampled file, stock (1992-1997) and custom. Sample: `PNFL.pyr` (9,192 players, 551,580 bytes).

---

## 1. File Layout

A 60-byte header, then one 60-byte record per player, back to back. Total file length = 60 + players × 60. The player count is not stored.

```
header
player 1  id 100
player 2  id 101
...
```

| Offset |   Size | Name     | Description                     | Section |
| -----: | -----: | :------- | :------------------------------ | :------ |
| 0x0000 |     60 | Header   | Header                          | 2       |
| 0x003C |     60 | Player 1 | Player id 100                   | 4       |
| 0x0078 |     60 | Player 2 | Player id 101                   | 4       |
|    ... |    ... | ...      | Record i is player id 100 + i   | 4       |

---

## 2. Header (60 bytes)

Starts at 0x0000.

| Offset | Size | Type     | Name   | Description                                                |
| -----: | ---: | :------- | :----- | :--------------------------------------------------------- |
| 0x0000 |    2 | u16      | Key    | Picks the coding table (section 3); `0xCE5F` in `PNFL.pyr` |
| 0x0002 |   13 | u8[13]   | Zero   | All `0x00`                                                 |
| 0x000F |   13 | char[13] | Name   | `"SYNERGISTIC1"` in stock files; zeros in `PNFL.pyr`       |
| 0x001C |   27 | u8[27]   | Zero   | All `0x00`                                                 |
| 0x0037 |    2 | u16      | Marker | `0xFFFF` in stock files; `0` in `PNFL.pyr`                 |
| 0x0039 |    3 | u8[3]    | Zero   | All `0x00`                                                 |

The header is laid out like a player record: the key sits where the id goes, the name where the last name goes, and the marker where the newest draft class has `0xFFFF` (section 4). The header is not coded.

---

## 3. Coding

The record bytes are scrambled with a lookup table, not a formula:

- One table of 256 entries: each plain byte value `0x00`-`0xFF` is written as a fixed other value. In `PNFL.pyr` a plain `0x00` is always written as `0xD3`.
- The same table is used for every byte of every record. The header is plain.
- The header key picks the table. In 21 sampled files, files with the same key have the same table and different keys have different tables (18 keys, 18 tables): plain `0x00` is written as `0x0F` in `NFLPI97R.PYR` (key `0xEE0F`). How the game turns the key into the table is unknown; the table is not stored in the file.
- `PNFL.pyr` keeps key `0xCE5F` and the same table in every weekly file from 2047 to 2049.

The file reveals its own table, because every record starts with a value that is known before decoding:

- Record i holds player id 100 + i in its first two bytes (section 4), so the plain id bytes of every record are known.
- Compare them with the two bytes on disk: each record shows what one or two plain values are written as.
- Over 256 consecutive records the low id byte takes every value `0x00`-`0xFF`, so a file with 256 or more players gives the whole table from byte 0 alone.
- Decoding is the reverse lookup: find each disk byte in the table and take the plain value it stands for.

Example, `PNFL.pyr` record 0: player 100 = `0x0064`, plain bytes `64 00`; on disk `3F D3`. So plain `0x64` is written as `0x3F` and plain `0x00` as `0xD3`.

`PNFL.pyr`'s full table is in the appendix.

---

## 4. Player Record (60 bytes, decoded)

Starts at 0x003C + 60 × (id − 100).

| Offset | Size | Type     | Name       | Description                                              |
| -----: | ---: | :------- | :--------- | :------------------------------------------------------- |
|   0x00 |    2 | u16      | Id         | Player id; 100 + record index                            |
|   0x02 |   13 | char[13] | First name | NUL-padded; longer names are cut                         |
|   0x0F |   13 | char[13] | Last name  | NUL-padded; longer names are cut                         |
|   0x1C |    8 | u8[8]    | Potential  | Potential ratings (section 5); not shown in the game     |
|   0x24 |    4 | u8[4]    | Injury     | Injury level, injury and week (section 6)                |
|   0x28 |    1 | u8       | Group      | Position group (section 5)                               |
|   0x29 |    1 | u8       | Position   | Position (section 5)                                     |
|   0x2A |    8 | u8[8]    | Actual     | Actual ratings, same order; the ratings the game shows   |
|   0x32 |    1 | u8       | Years      | Years in the league                                      |
|   0x33 |    1 | u8       | Height     | Inches; filled only for the newest draft class, else `0` |
|   0x34 |    2 | u16      | Weight     | Pounds; filled only for the newest draft class, else `0` |
|   0x36 |    6 | u8[6]    | Unknown    | `0`; the newest draft class has `0xFFFF` at 0x37         |

Potential is at or above actual in every rating, in all but one `PNFL.pyr` record (Blake Watson, 7302: agility 81 potential, 83 actual).

Not in the record: draft year, team and pick, age, jersey number, team, depth, roster status. Jersey numbers, teams, depth and status (Assigned, Open, Inactive) come from the league's rosters: a player's slot in the `.lge` roster sets them ([lge.md](../../fbpro98_lge/specs/lge.md), section 6).

Placeholder records: 3,258 `No One` (all ratings `1`), 191 `Delete Me`, 114 `2043 Draft` in `PNFL.pyr`.

Example, `PNFL.pyr` player 6283, decoded:

```
0x00  8b 18                     id         = 6283
0x02  43 2e 20 4a 2e 00 ...     first name = C. J.
0x0F  53 74 72 6f 75 64 00 ...  last name  = Stroud
0x1C  51 51 53 56 47 5b 51 5f   potential  = 81 81 83 86 71 91 81 95
0x24  00 00 00 00               injury     = healthy
0x28  00                        group      = 0
0x29  00                        position   = 0 (QB)
0x2A  51 51 53 56 47 5b 51 5f   actual     = 81 81 83 86 71 91 81 95
0x32  05                        years      = 5
0x33  00                        height     = 0
0x34  00 00                     weight     = 0
0x36  00 00 00 00 00 00         unknown
```

The game's Player Editor shows the actual ratings (Speed 81, Acceleration 81, Agility 81, Strength 95, Hands 71, Endurance 86, Intelligence 91, Discipline 83), Yrs 5, Ht 0 and Wt 0. Jersey number 6 and status "A" come from Denver's roster.

---

## 5. Codes

Ratings, in file order: AC acceleration, AG agility, DI discipline, EN endurance, HA hands, IN intelligence, SP speed, ST strength; `0`-`99`.

| Position | Name | Group |
| :------- | :--- | :---- |
| `0`      | QB   | `0`   |
| `1`      | FB   | `15`  |
| `2`      | HB   | `15`  |
| `3`      | TE   | `16`  |
| `4`      | WR   | `16`  |
| `5`      | C    | `17`  |
| `6`      | G    | `17`  |
| `7`      | T    | `17`  |
| `8`      | DE   | `18`  |
| `9`      | DT   | `18`  |
| `10`     | LB   | `10`  |
| `11`     | CB   | `19`  |
| `12`     | S    | `19`  |
| `13`     | K    | `13`  |
| `14`     | P    | `14`  |

---

## 6. Injury (4 bytes)

Starts at 0x24 of the player record. An injury level of `0` is healthy; the injury and week stay after the player heals.

| Offset | Size | Type | Name   | Description                                      |
| -----: | ---: | :--- | :----- | :----------------------------------------------- |
|   0x00 |    2 | u16  | Level  | Injury level; `0` = healthy                      |
|   0x02 |    1 | u8   | Injury | Injury name index into `injury.dat`              |
|   0x03 |    1 | u8   | Week   | Week injured − 1; the injury screen's WK − 1     |

Checked against Denver's injury screen:

| Player                 | Bytes        | Injy | Condition             |  WK |
| :--------------------- | :----------- | :--- | :-------------------- | --: |
| Drew Dalman (3422)     | `167 0 25 1` | Q-2  | Broken leg            |   2 |
| Darius Robinson (6672) | `64 0 20 5`  | P-1  | Sore knee             |   6 |
| Tyler Warren (8484)    | `15 0 22 1`  | P-1  | Knee-cartilage injury |   2 |

Other values seen: `25 0 11 5`, `0 0 1 3`, `202 1 32 3`.

---

## 7. Open Questions

- How the header key generates the coding table
- Bytes 0x36-0x3B
- Why height and weight are blank for all but the newest draft class

---

## Appendix: PNFL Coding Table

`PNFL.pyr`, key `0xCE5F`; the same in every PNFL file checked, 2044 to 2049. Row = high digit, column = low digit of the plain byte; each cell is the byte written to disk.

```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00: d3 73 89 a9 2b 4b 41 e1 da ba 70 90 12 f2 48 28
10: 81 a1 d7 b7 59 f9 2f 0f 68 88 9e be 40 20 56 f6
20: 6f cf 85 65 27 07 5d 3d 96 b6 6c cc ee 4e 04 24
30: 7d 9d b3 93 55 35 eb 0b 64 c4 9a 7a fc 1c 52 32
40: ab cb c1 61 e3 03 19 39 92 72 a8 c8 2a 4a 00 e0
50: 79 d9 af 8f 11 31 e7 47 c0 a0 d6 76 f8 18 2e 0e
60: a7 87 bd dd 3f df 15 f5 ce 6e a4 84 26 46 3c 5c
70: b5 d5 6b 8b 0d ed 23 43 7c 9c d2 b2 f4 54 ea 0a
80: 63 83 b9 99 3b 1b 51 f1 ca aa 80 60 22 02 38 58
90: 91 b1 67 c7 49 e9 ff 1f 78 d8 8e ae 30 50 e6 06
a0: 5f bf 75 95 f7 17 4d 2d c6 a6 bc dc 5e fe 34 14
b0: 8d 6d a3 c3 45 25 fb 5b 74 d4 8a 6a 0c 2c e2 42
c0: 9b bb d1 71 f3 53 09 29 a2 82 b8 98 5a 3a f0 10
d0: c9 69 9f 7f 01 21 37 57 b0 d0 86 66 08 e8 1e 3e
e0: 97 77 cd ad ef 4f 05 e5 de 7e b4 94 16 36 4c ec
f0: c5 a5 db 7b 1d fd 33 13 ac 8c 62 c2 44 e4 1a fa
```
