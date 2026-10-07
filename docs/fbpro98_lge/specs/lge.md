# .lge - Front Page Sports Football Pro '98 League File Format

- **Status:** Draft (reverse engineered from `PNFL.lge`; no library yet)
- **Owner:** none yet
- **Encoding:** Integers little-endian; strings ASCII, NUL-terminated, with leftover text after the NUL. Team and roster chunks are masked (section 8).

A `.lge` holds a league's structure, teams, rosters and schedule. It is named after its league (`PNFL.lge`) and sits in the game folder. One layout in every sampled file, stock (1992-1997) and custom. Sample: `PNFL.lge` (18 teams, 10,495 bytes).

---

## 1. File Layout

A stream of chunks, each `ID (4 bytes)` + `size (u32)` + `size` bytes of data. The chunks form a tree, written depth-first:

```
L03  league
  C03  conference 1
    D03  division 1
      T03 + R03  team 1 (team record, then its roster)
      T03 + R03  team 2
      ...
    D03  division 2
      ...
  C03  conference 2
    ...
S03  schedule
```

| Offset           |     Size | Name   | Description                       | Section |
| :--------------- | -------: | :----- | :-------------------------------- | :------ |
| 0                |  89+conf | `L03:` | League                            | 2       |
| L03 + 97 + conf  |   29+div | `C03:` | Conference, one per conference    | 3       |
| C03 + 37 + div   | 29+teams | `D03:` | Division, one per division        | 4       |
| D03 + 37 + teams |      171 | `T03:` | Team record, masked, one per team | 5       |
| T03 + 179        |      325 | `R03:` | Roster, masked, one per team      | 6       |
| last R03 + 333   | variable | `S03:` | Schedule and results              | 7       |

An offset is the start of the chunk named plus that chunk's 8-byte header and size, so it moves with the conference, division and team counts; `conf`, `div` and `teams` are the counts stored in the chunk being skipped. The first chunk of each kind in `PNFL.lge` sits at 0x0000, 0x0063, 0x008A, 0x00B3, 0x0166 and 0x2557.

Teams are numbered 1..N in file order. Every other league file keyed by team uses that number (`.lg2`, `.rst`, `.dft`, `.tmn`, `.dat`).

---

## 2. Chunk: L03 — League (89 + conferences bytes)

Starts at 0x0000; the data below begins 8 bytes in, after the tag and size.

| Offset | Size | Type     | Name           | Description                                                                                                                    |
| -----: | ---: | :------- | :------------- | :----------------------------------------------------------------------------------------------------------------------------- |
|   0x00 |    1 | u8       | unknown        | `0`-`5`                                                                                                                        |
|   0x01 |    1 | u8       | conferences    | Conference count<br>`1` in the 8-12 team stock leagues, `2` elsewhere                                                          |
|   0x02 |    6 | u8[6]    | unknown        | `00 0A 00 01 00 00` in `PNFL.lge`<br>`00 09 00 00 00 00` or `00 09 00 01 00 00` in stock leagues                               |
|   0x08 |    2 | u16      | next_player_id | `9292` in `PNFL.lge`<br>`507` in `08_TEAMS`, whose `.pyr` holds ids 100-506                                                    |
|   0x0A |    2 | u16      | base_year      | Year of the first season<br>`1998` PNFL, `1966` NFLPI97R, `1994` small stock leagues<br>Season = base year + completed seasons |
|   0x0C |    3 | u8[3]    | unknown        | `33 02 BF` in `PNFL.lge`<br>`00 02 3F` or `1F 02 3F` in stock leagues                                                          |
|   0x0F |   25 | char[25] | name           | `"PNFL"`                                                                                                                       |
|   0x28 |   25 | char[25] | championship   | `"Super Bowl"`                                                                                                                 |
|   0x41 |   17 | u8[17]   | zero           |                                                                                                                                |
|   0x52 |    n | u8[n]    | conference     | Conference ids, one byte each (`01 02`)<br>`n` = `conferences`                                                                 |
| 0x52+n |    7 | u8[7]    | unknown        | `00 00 01 00 00 00 00` in `PNFL.lge`<br>`01 00 00 00 00 00 00` in stock leagues                                                |

The size is 89 + the conference count: 90 bytes with one conference, 91 with two.

---

## 3. Chunk: C03 — Conference (29 + divisions bytes)

Starts right after the L03 chunk (0x0063 in `PNFL.lge`); the data below begins 8 bytes in.

| Offset | Size | Type     | Name      | Description                                    |
| -----: | ---: | :------- | :-------- | :--------------------------------------------- |
|   0x00 |    1 | u8       | id        | 1-based                                        |
|   0x01 |    1 | u8       | index     | 0-based                                        |
|   0x02 |    1 | u8       | divisions | Division count                                 |
|   0x03 |    1 | u8       | unknown   | `01`                                           |
|   0x04 |   25 | char[25] | name      | Empty in `PNFL.lge`                            |
|   0x1D |    n | u8[n]    | division  | Division ids, one byte each; `n` = `divisions` |

---

## 4. Chunk: D03 — Division (29 + teams bytes)

Starts right after its conference's C03 chunk, or after the previous division's last R03 (first one at 0x008A in `PNFL.lge`); the data below begins 8 bytes in.

| Offset | Size | Type     | Name  | Description                                |
| -----: | ---: | :------- | :---- | :----------------------------------------- |
|   0x00 |    1 | u8       | id    | 1-based                                    |
|   0x01 |    1 | u8       | conf  | Conference index, 0-based                  |
|   0x02 |    1 | u8       | index | Division index within conference           |
|   0x03 |    1 | u8       | teams | Team count                                 |
|   0x04 |   25 | char[25] | name  | `"East"`, `"West"`                         |
|   0x1D |    n | u8[n]    | team  | Team numbers, one byte each; `n` = `teams` |

---

## 5. Chunk: T03 — Team (171 bytes)

Starts right after its division's D03 chunk, or after the previous team's R03 (team 1 at 0x00B3 in `PNFL.lge`); the data below begins 8 bytes in.

Byte 0 is the team number, in clear. Bytes 1-170 are masked (section 8); offsets below are into the unmasked 170 bytes.

| Offset | Size | Type      | Name         | Description                                                     |
| -----: | ---: | :-------- | :----------- | :-------------------------------------------------------------- |
|   0x00 |    1 | u8        | conf         | Conference index                                                |
|   0x01 |    1 | u8        | div          | Division index within conference                                |
|   0x02 |    1 | u8        | slot         | Position in the division's team list                            |
|   0x03 |    1 | u8        | city_index   | City id in `CITIES.DAT` ([cities.md](../../fbpro98_cities/specs/cities.md)); the "City" choice on the Team Settings screen |
|   0x04 |    1 | u8        | stadium_type | Same code as `stadium_type` in the `CITIES.DAT` city record: `0` Outdoor/Grass (the game's weather screen shows it for Denver), `2` dome (Atlanta, Washington, Detroit and Minnesota in `PNFL.lge`), `1` the other outdoor value |
|   0x05 |    4 | u8[4]     | unknown      | `01 01 01 01`                                                   |
|   0x09 |   33 | u8[11][3] | colors       | 11 RGB triplets, each component 0-63; slot meaning not mapped   |
|   0x2A |   12 | u8[12]    | zero         |                                                                 |
|   0x36 |   17 | char[17]  | team_name    | `"Denver"`; "Team Name" on the game's Team Settings screen |
|   0x47 |   17 | char[17]  | nickname     | `"Broncos"`                                                     |
|   0x58 |    5 | char[5]   | abbreviation | `"DEN"`                                                         |
|   0x5D |   17 | char[17]  | stadium      | `"Empire Field"`; a 17-character name has no NUL                |
|   0x6E |   17 | char[17]  | head_coach   | `"Brian Jacobs"`; "Head Coach" on the Team Settings screen |
|   0x7F |   19 | u8[19]    | unknown      | Leftover text at `0x88`-`0x8E`; u16 at `0x8F`; `0xFF` at `0x91` |
|   0x92 |   15 | u8[15]    | zero         |                                                                 |
|   0xA1 |    9 | char[9]   | uniform      | `"DEFAULT0"` .. `"DEFAULT9"`                                    |

---

## 6. Chunk: R03 — Roster (325 bytes)

Starts 179 bytes after its team's T03 (team 1 at 0x0166 in `PNFL.lge`); the data below begins 8 bytes in.

Bytes 0-1 are the team number (u16), in clear. Bytes 2-324 are masked (section 8); offsets below are into the unmasked 323 bytes.

| Offset | Size | Type    | Name    | Description                                                                                                  |
| -----: | ---: | :------ | :------ | :----------------------------------------------------------------------------------------------------------- |
|   0x00 |  126 | u16[63] | player  | Player ids (`.pyr`), `0` = empty slot; slots 60-62 are set apart (Denver keeps three inactive players there) |
|   0x7E |   63 | u8[63]  | number  | Jersey number per slot, same order                                                                           |
|   0xBD |    9 | u8[9]   | unknown | A permutation of 1-9                                                                                         |
|   0xC6 |   65 | u8[65]  | zero    |                                                                                                              |
|  0x107 |   60 | u8[60]  | unknown | Identical in all 18 teams                                                                                    |

`pnfl.rst` is these 18 chunks, byte for byte.

---

## 7. Chunk: S03 — Schedule (928 bytes in `PNFL.lge`)

Starts right after the last R03 (0x2557 in `PNFL.lge`); the data below begins 8 bytes in.

| Offset |   Size | Type | Name           | Description                             |
| -----: | -----: | :--- | :------------- | :-------------------------------------- |
|   0x00 |      1 | u8   | regular_weeks  | `16`                                    |
|   0x01 |      1 | u8   | playoff_rounds | `3`                                     |
|   0x02 |      1 | u8   | weeks_played   | `6`; equals the weeks that carry scores |
|   0x03 | varies | week | weeks          | `regular_weeks + playoff_rounds` weeks  |

Week: `u8 games`, then `games` × 6 bytes:

| Offset | Size | Type | Name     | Description                            |
| -----: | ---: | :--- | :------- | :------------------------------------- |
|   0x00 |    1 | u8   | team_a   | Team number; `0xFF` when not yet known |
|   0x01 |    1 | u8   | score_a  | `0xFF` when not played                 |
|   0x02 |    1 | u8   | team_b   |                                        |
|   0x03 |    1 | u8   | score_b  |                                        |
|   0x04 |    1 | u8   | overtime | `1` on 3 of 54 played games            |
|   0x05 |    1 | u8   | status   | `0` played, `2` not played             |

Each team is `team_a` 8 times and `team_b` 8 times in `PNFL.lge`, so a/b is home/away; which side is home is not verified. Playoff weeks in `PNFL.lge` hold 4, 2 and 1 games.

---

## 8. Mask

T03 and R03 data is XORed byte by byte with `(0x69 × team + i) mod 256`, `team` the team number from the chunk's clear bytes, `i` the offset into the masked bytes (0 for the first masked byte). A run of zero bytes therefore reads as values stepping up by 1. L03, C03, D03 and S03 are not masked.

---

## 9. Validation & Test Vectors

`PNFL.lge`: team 5 unmasks to `Denver` / `Broncos` / `DEN` / `Empire Field` / `Brian Jacobs` / `DEFAULT8`; its roster starts `6283 6, 8428 2, 4552 31` (C. J. Stroud #6, Cam Ward #2, Isaiah Spiller #31) and matches the league's roster sheet slot for slot. Week 1 game 3 is `10 24 5 23 0 0`: Atlanta 24, Denver 23.

---

## 10. Open Questions

- L03 bytes `0x00`, `0x02`-`0x07`, `0x0C`-`0x0E` and the 7-byte tail
- T03 `stadium_type` `1`, the color slot order and bytes `0x7F`-`0x91`
- Whether the game shows the T03 `stadium` name: Denver's weather screen says `Mile High Stadium`, the chunk `Empire Field`
- R03 slots 60-62, the 1-9 permutation and the 60-byte table
- Which schedule side is home
