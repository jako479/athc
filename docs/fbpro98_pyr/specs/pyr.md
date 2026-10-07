# .pyr - Front Page Sports Football Pro '98 Player File Format

- **Status:** Draft (reverse engineered from `PNFL.pyr`; no library yet)
- **Owner:** none yet
- **Encoding:** Integers little-endian; strings ASCII. Every byte after the header is coded (section 3).

A `.pyr` holds every player a league knows: names, ratings, position, years and injury. It is named after its league (`PNFL.pyr`) and sits in the game folder. One layout in every sampled file, stock (1992-1997) and custom. Sample: `PNFL.pyr` (9,192 players, 551,580 bytes).

---

## 1. File Layout

A 60-byte header, then one 60-byte record per player, back to back. Total file length = `60 + players × 60`. The player count is not stored.

```
header
player[0]  id 100
player[1]  id 101
...
```

| Offset |   Size | Name      | Description                       | Section |
| -----: | -----: | :-------- | :-------------------------------- | :------ |
| 0x0000 |     60 | header    | Header                            | 2       |
| 0x003C |     60 | player[0] | Player id 100                     | 4       |
| 0x0078 |     60 | player[1] | Player id 101                     | 4       |
|    ... |    ... | ...       | Record `i` is player id `100 + i` | 4       |

---

## 2. Header (60 bytes)

Starts at 0x0000.

| Offset | Size | Type   | Name | Description                                                |
| -----: | ---: | :----- | :--- | :--------------------------------------------------------- |
| 0x0000 |    2 | u16    | key  | Differs per file (`0xCE5F` in `PNFL.pyr`); meaning unknown |
| 0x0002 |   58 | u8[58] | zero | All `0x00`                                                 |

The header is not coded.

---

## 3. Coding

The record bytes are scrambled with a lookup table, not a formula:

- One table of 256 entries: each plain byte value `0x00`-`0xFF` is written as a fixed other value. In `PNFL.pyr` a plain `0x00` is always written as `0xD3`.
- The same table is used for every byte of every record. The header is plain.
- Each file has its own table: plain `0x00` is written as `0x0F` in `NFLPI97R.PYR`. The table is not stored in the file and no formula for it is known.

The file reveals its own table, because every record starts with a value that is known before decoding:

- Record `i` holds player id `100 + i` in its first two bytes (section 4), so the plain id bytes of every record are known.
- Compare them with the two bytes on disk: each record shows what one or two plain values are written as.
- Over 256 consecutive records the low id byte takes every value `0x00`-`0xFF`, so a file with 256 or more players gives the whole table from byte 0 alone.
- Decoding is the reverse lookup: find each disk byte in the table and take the plain value it stands for.

Example, `PNFL.pyr` record 0: player 100 = `0x0064`, plain bytes `64 00`; on disk `3F D3`. So plain `0x64` is written as `0x3F` and plain `0x00` as `0xD3`.

`PNFL.pyr`'s full table is in [pnfl-formats.md](../../design/research/pnfl-formats.md).

---

## 4. Player Record (60 bytes, decoded)

Starts at `0x003C + 60 × (id − 100)`.

| Offset | Size | Type     | Name       | Description                                                  |
| -----: | ---: | :------- | :--------- | :----------------------------------------------------------- |
|   0x00 |    2 | u16      | id         | Player id; `100 + record index`                              |
|   0x02 |   13 | char[13] | first_name | NUL-padded; longer names are cut                             |
|   0x0F |   13 | char[13] | last_name  | NUL-padded; longer names are cut                             |
|   0x1C |    8 | u8[8]    | potential  | Potential ratings, order AC AG DI EN HA IN SP ST (section 5) |
|   0x24 |    4 | u8[4]    | injury     | All `0x00` when healthy (section 6)                          |
|   0x28 |    1 | u8       | group      | Position group (section 5)                                   |
|   0x29 |    1 | u8       | position   | Position (section 5)                                         |
|   0x2A |    8 | u8[8]    | actual     | Actual ratings, same order as `potential`                    |
|   0x32 |    1 | u8       | years      | Years in the league                                          |
|   0x33 |    1 | u8       | height     | Inches; filled only for the newest draft class, else `0`     |
|   0x34 |    2 | u16      | weight     | Pounds; filled only for the newest draft class, else `0`     |
|   0x36 |    6 | u8[6]    | unknown    | `0`; the newest draft class has `0xFFFF` at `0x37`           |

Not in the record: draft year, team and pick, age, jersey number, team, depth. Jersey numbers and teams come from the league's rosters (`.lge`), depth from the `.prf`.

Placeholder records: 3,258 `No One` (all ratings `1`), 191 `Delete Me`, 114 `2043 Draft` in `PNFL.pyr`.

---

## 5. Codes

Ratings: `AC` acceleration, `AG` agility, `DI` discipline, `EN` endurance, `HA` hands, `IN` intelligence, `SP` speed, `ST` strength; `0`-`99`.

| position | Name | group |
| :------- | :--- | :---- |
| 0        | QB   | 0     |
| 1        | FB   | 15    |
| 2        | HB   | 15    |
| 3        | TE   | 16    |
| 4        | WR   | 16    |
| 5        | C    | 17    |
| 6        | G    | 17    |
| 7        | T    | 17    |
| 8        | DE   | 18    |
| 9        | DT   | 18    |
| 10       | LB   | 10    |
| 11       | CB   | 19    |
| 12       | S    | 19    |
| 13       | K    | 13    |
| 14       | P    | 14    |

---

## 6. Injury (4 bytes)

Observed values on injured players: `15 0 22 1`, `167 0 25 1`, `25 0 11 5`, `0 0 1 3`, `202 1 32 3`. Byte 2 looks like a length and byte 3 a status; bytes 0-1 look like a u16 type. Not confirmed.

---

## 7. Validation & Test Vectors

`PNFL.pyr` decoded with the rebuilt table matches the league's own roster sheets: C. J. Stroud (6283) QB, years 5, actual AC 81 AG 81 DI 83 EN 86 HA 71 IN 91 SP 81 ST 95; Dillon Gabriel (8430) QB, years 1, potential 81 81 84 85 71 90 80 95, actual 79 79 83 83 70 89 78 94.

---

## 8. Open Questions

- What the header key is and whether it generates the table
- The injury bytes
- Bytes `0x36`-`0x3B`
- Why height and weight are blank for all but the newest draft class
