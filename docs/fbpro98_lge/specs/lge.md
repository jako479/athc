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

| ID     |     Size | Count | Description                       | Section |
| :----- | -------: | ----: | :-------------------------------- | :------ |
| `L03:` | 90 or 91 |     1 | League                            | 2       |
| `C03:` | 31 or 32 |  conf | Conference                        | 3       |
| `D03:` |    32-34 |   div | Division; size grows with teams   | 4       |
| `T03:` |      171 |  team | Team record, masked               | 5       |
| `R03:` |      325 |  team | Roster, masked                    | 6       |
| `S03:` | variable |     1 | Schedule and results              | 7       |

Teams are numbered 1..N in file order. Every other league file keyed by team uses that number (`.lg2`, `.rst`, `.dft`, `.tmn`, `.dat`).

---

## 2. Chunk: L03 — League (91 bytes in `PNFL.lge`)

| Offset | Type     | Name            | Description                                          |
| -----: | :------- | :-------------- | :--------------------------------------------------- |
|   0x00 | u8[8]    | unknown         | `03 02 00 0A 00 01 00 00`                            |
|   0x08 | u16      | next_player_id  | `9292`; the `.pyr` holds ids 100-9291               |
|   0x0A | u16      | base_year       | `1998`; season = base year + completed seasons       |
|   0x0C | u8[3]    | unknown         | `33 02 BF`                                           |
|   0x0F | char[25] | name            | `"PNFL"`                                             |
|   0x28 | char[25] | championship    | `"Super Bowl"`                                       |
|   0x41 | u8[26]   | unknown         | Mostly `0x00`; `01 02 00 00 01` at `0x52`            |

The 8-12 team stock leagues have a 90-byte L03; the difference is not mapped.

---

## 3. Chunk: C03 — Conference (31 bytes)

| Offset | Type     | Name      | Description                              |
| -----: | :------- | :-------- | :--------------------------------------- |
|   0x00 | u8       | id        | 1-based                                  |
|   0x01 | u8       | index     | 0-based                                  |
|   0x02 | u8       | divisions | Division count                           |
|   0x03 | u8       | unknown   | `01`                                     |
|   0x04 | char[25] | name      | Empty in `PNFL.lge`                      |
|   0x1D | u8[n]    | division  | Division ids, one byte each              |

---

## 4. Chunk: D03 — Division (33 or 34 bytes)

| Offset | Type     | Name     | Description                       |
| -----: | :------- | :------- | :-------------------------------- |
|   0x00 | u8       | id       | 1-based                           |
|   0x01 | u8       | conf     | Conference index, 0-based         |
|   0x02 | u8       | index    | Division index within conference  |
|   0x03 | u8       | teams    | Team count                        |
|   0x04 | char[25] | name     | `"East"`, `"West"`                |
|   0x1D | u8[n]    | team     | Team numbers, one byte each       |

---

## 5. Chunk: T03 — Team (171 bytes)

Byte 0 is the team number, in clear. Bytes 1-170 are masked (section 8); offsets below are into the unmasked 170 bytes.

| Offset | Type     | Name         | Description                                                   |
| -----: | :------- | :----------- | :------------------------------------------------------------ |
|   0x00 | u8       | conf         | Conference index                                              |
|   0x01 | u8       | div          | Division index within conference                              |
|   0x02 | u8       | slot         | Position in the division's team list                          |
|   0x03 | u8       | city_index   | 2-52 in `PNFL.lge`, alphabetical by city; table not located   |
|   0x04 | u8       | stadium_type | `0`, `1` or `2`; `2` on the domed teams                       |
|   0x05 | u8[4]    | unknown      | `01 01 01 01`                                                 |
|   0x09 | u8[11][3]| colors       | 11 RGB triplets, each component 0-63; slot meaning not mapped |
|   0x2A | u8[12]   | zero         |                                                               |
|   0x36 | char[17] | city         | `"Denver"`                                                    |
|   0x47 | char[17] | nickname     | `"Broncos"`                                                   |
|   0x58 | char[5]  | abbreviation | `"DEN"`                                                       |
|   0x5D | char[17] | stadium      | `"Empire Field"`; a 17-character name has no NUL              |
|   0x6E | char[17] | owner        | `"Brian Jacobs"`                                              |
|   0x7F | u8[19]   | unknown      | Leftover text at `0x88`-`0x8E`; u16 at `0x8F`; `0xFF` at `0x91` |
|   0x92 | u8[15]   | zero         |                                                               |
|   0xA1 | char[9]  | uniform      | `"DEFAULT0"` .. `"DEFAULT9"`                                  |

---

## 6. Chunk: R03 — Roster (325 bytes)

Bytes 0-1 are the team number (u16), in clear. Bytes 2-324 are masked (section 8); offsets below are into the unmasked 323 bytes.

| Offset | Type    | Name    | Description                                                        |
| -----: | :------ | :------ | :----------------------------------------------------------------- |
|   0x00 | u16[63] | player  | Player ids (`.pyr`), `0` = empty slot; slots 60-62 are set apart (Denver keeps three inactive players there) |
|   0x7E | u8[63]  | number  | Jersey number per slot, same order                                 |
|   0xBD | u8[9]   | unknown | A permutation of 1-9                                               |
|   0xC6 | u8[65]  | zero    |                                                                    |
|  0x107 | u8[60]  | unknown | Identical in all 18 teams                                          |

`pnfl.rst` is these 18 chunks, byte for byte.

---

## 7. Chunk: S03 — Schedule (928 bytes in `PNFL.lge`)

| Offset | Type  | Name           | Description                                   |
| -----: | :---- | :------------- | :-------------------------------------------- |
|   0x00 | u8    | regular_weeks  | `16`                                          |
|   0x01 | u8    | playoff_rounds | `3`                                           |
|   0x02 | u8    | weeks_played   | `6`; equals the weeks that carry scores       |
|   0x03 | week  | weeks          | `regular_weeks + playoff_rounds` weeks        |

Week: `u8 games`, then `games` × 6 bytes:

| Offset | Type | Name     | Description                                    |
| -----: | :--- | :------- | :--------------------------------------------- |
|   0x00 | u8   | team_a   | Team number; `0xFF` when not yet known         |
|   0x01 | u8   | score_a  | `0xFF` when not played                         |
|   0x02 | u8   | team_b   |                                                |
|   0x03 | u8   | score_b  |                                                |
|   0x04 | u8   | overtime | `1` on 3 of 54 played games                    |
|   0x05 | u8   | status   | `0` played, `2` not played                     |

Each team is `team_a` 8 times and `team_b` 8 times in `PNFL.lge`, so a/b is home/away; which side is home is not verified. Playoff weeks in `PNFL.lge` hold 4, 2 and 1 games.

---

## 8. Mask

T03 and R03 data is XORed byte by byte with `(0x69 × team + i) mod 256`, `team` the team number from the chunk's clear bytes, `i` the offset into the masked bytes (0 for the first masked byte). A run of zero bytes therefore reads as values stepping up by 1. L03, C03, D03 and S03 are not masked.

---

## 9. Validation & Test Vectors

`PNFL.lge`: team 5 unmasks to `Denver` / `Broncos` / `DEN` / `Empire Field` / `Brian Jacobs` / `DEFAULT8`; its roster starts `6283 6, 8428 2, 4552 31` (C. J. Stroud #6, Cam Ward #2, Isaiah Spiller #31) and matches the league's roster sheet slot for slot. Week 1 game 3 is `10 24 5 23 0 0`: Atlanta 24, Denver 23.

---

## 10. Open Questions

- L03 bytes `0x00`-`0x07`, `0x0C`-`0x0E` and `0x41`-`0x5A`, and the 90-byte variant
- T03 `city_index` table, `stadium_type` values, the color slot order and bytes `0x7F`-`0x91`
- R03 slots 60-62, the 1-9 permutation and the 60-byte table
- Which schedule side is home
