# CITIES.DAT - Front Page Sports Football Pro '98 City Table Format

- **Owner:** none yet
- **Encoding:** Integers little-endian; strings ASCII, NUL-terminated, with leftover text after the NUL. Not masked.

`CITIES.DAT` is the game's table of cities with their weather odds and home stadium. It sits in the game folder (one copy, not per league). A league's team chunk (`.lge` T03 byte 3) holds a city id from this table. Sample: `E:\SIERRA\FbPro98\CITIES.DAT` (128 cities, 14,328 bytes).

---

## 1. File Layout

A stream of chunks, each ID (4 bytes) + size (u32) + size bytes of data, like `.lge`: four small tables, then one chunk per city.

```
CTL  table, 7 rows of 5 ranges
CTR  table, 5 ranges
CHI  table, 66 signed values
CWC  table, 7 rows of 10 values
CTY  city 1
CTY  city 2
...
CTY  city 128
```

| Offset                 | Size | Name   | Description                                   | Section |
| :--------------------- | ---: | :----- | :-------------------------------------------- | :------ |
| 0x0000                 |   70 | `CTL:` | Table, 7 rows of 5 (low, high) percent ranges | 2       |
| 0x004E                 |   10 | `CTR:` | Table, 5 (low, high) pairs                    | 2       |
| 0x0060                 |   66 | `CHI:` | Table, 66 signed values                       | 2       |
| 0x00AA                 |   70 | `CWC:` | Table, 7 rows of 10 values                    | 2       |
| 0x00F8 + 110 × (k − 1) |  102 | `CTY:` | City with id k, ids 1-128 in order            | 3       |

Each offset is the chunk's tag; its data begins 8 bytes later. Sizes are the data sizes.

---

## 2. Header Tables

Starts at 0x0000; four chunks back to back. Their meaning is not mapped; the shapes are:

- `CTL:` (70 bytes): 7 rows × 5 pairs of (low, high) percentages in the section 3 range encoding; the filled pairs shift one slot left per row (row 0 fills pairs 4-5, row 6 fills pairs 1-2).
- `CTR:` (10 bytes): 5 pairs, `11 36`, `37 49`, `50 71`, `72 84`, `85 105`.
- `CHI:` (66 bytes): signed values, multiples of 5 from `-10` to `20`.
- `CWC:` (70 bytes): 7 rows × 10 values, multiples of 5 from `0` to `45`, rising down and across.

---

## 3. Chunk: CTY — City (102 bytes)

Starts at 0x00F8 + 110 × (k − 1) for the city with id k; the data below begins 8 bytes in.

| Offset | Size | Type     | Name         | Description                                                        | Section |
| -----: | ---: | :------- | :----------- | :----------------------------------------------------------------- | :------ |
|   0x00 |    1 | u8       | Id           | `1`-`128`, in file order; the value a `.lge` team chunk stores     |         |
|   0x01 |   16 | char[16] | Name         | City; longest is 15 characters (`"East Rutherford"`)               |         |
|   0x11 |    1 | u8       | Unknown      | `0`-`18`; `4` in Los Angeles and Phoenix, `18` in London           |         |
|   0x12 |   50 | u8[50]   | Weather      | 5 tables of 10 bytes                                               | 3.1     |
|   0x44 |    1 | u8       | Unknown      | `0`-`32`                                                           |         |
|   0x45 |    1 | u8       | Stadium type | `0` = Outdoor/Grass (the game's weather screen shows it for Denver), `2` on the 16 dome records (`The Metrodome`, `The Louisiana Superdome`, `Carrier Dome`, `Kibbie Activity Center`, twelve `Synergistic Stadium`), `1` the other outdoor value |         |
|   0x46 |   32 | char[32] | Stadium      | `"Dodd Stadium"`; longest is 28 characters; never empty            |         |

City 1 is `CETI ALPHA VI`, a fictional city whose weather is always the first outcome; cities 2-44 are NFL, CFL and World League cities in alphabetical order; 45-128 are later additions, mostly NFL homes and college towns, in no order.

### 3.1 Weather Table (10 bytes)

Five tables per city, at 0x12, 0x1C, 0x26, 0x30 and 0x3A: Aug/Sept, October, November, December and January, the periods the game's weather screen offers.

| Offset | Size | Type     | Name     | Description                                                                 |
| -----: | ---: | :------- | :------- | :-------------------------------------------------------------------------- |
|   0x00 |    8 | u8[4][2] | Outcomes | Four (low, high) percentage ranges: Clear, Partly Cloudy, Cloudy, Rain/Snow |
|   0x08 |    1 | u8       | Unknown  | `65`-`71`                                                                   |
|   0x09 |    1 | u8       | Unknown  | `15`-`85`, multiples of 5                                                   |

Range encoding: the four ranges tile 1-100, each low-high inclusive (`1 30`, `31 60`, `61 70`, `71 100` in Atlanta's first table); `0 0` is an outcome that never happens. The slot order is the order of the game's weather screen (Clear, Partly Cloudy, Cloudy, Rain/Snow), and the data agrees: dry-season cities (Los Angeles, San Diego, San Francisco, Barcelona) zero Rain/Snow in Aug/Sept, Miami, Tampa and Honolulu zero Cloudy, and Eugene and Corvallis zero Clear from November on. `Boise, ID` has a broken first table (`91 110`, `111 100`).

---

## 4. Open Questions

- The four header tables
- Record bytes 0x11, 0x44 and the two trailing bytes of each weather table
- What stadium type `1` is
- Where the stadium name the game shows comes from: Denver's weather screen says `Mile High Stadium`, the city record `Falcon Stadium`, the team chunk `Empire Field`
