# .lge - Front Page Sports Football Pro '98 League File Format

- **Owner:** FBPro98 Lge Library
- **Encoding:** Integers little-endian; strings ASCII, NUL-terminated, with leftover text after the NUL. Team and roster chunks are masked (section 8).

A `.lge` holds a league's structure, teams, rosters and schedule. It is named after its league (`PNFL.lge`) and sits in the game folder. One layout in every sampled file, stock (1992-1997) and custom, with the chunks in one of two orders (section 1). Sample: `PNFL.lge` (18 teams, 10,495 bytes).

---

## 1. File Layout

A stream of chunks, each ID (4 bytes) + size (u32) + size bytes of data. The chunks form a tree, written depth-first:

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

Five stock files (`_default.lge`, `Sierra.lge`, `NFLPA93E.LGE`, `NFLPA94E.lge`, `NFLPI95E.lge`) write the same chunks grouped by kind instead: L03, every C03, every D03, every T03, every R03, then S03. The counts nest them the same way, and team numbers still run 1..N. The offsets below are for the nested order.

| Offset           |     Size | Name   | Description                       | Section |
| :--------------- | -------: | :----- | :-------------------------------- | :------ |
| 0                |  89+conf | `L03:` | League                            | 2       |
| L03 + 97 + conf  |   29+div | `C03:` | Conference, one per conference    | 3       |
| C03 + 37 + div   | 29+teams | `D03:` | Division, one per division        | 4       |
| D03 + 37 + teams |      171 | `T03:` | Team record, masked, one per team | 5       |
| T03 + 179        |      325 | `R03:` | Roster, masked, one per team      | 6       |
| last R03 + 333   | variable | `S03:` | Schedule and results              | 7       |

An offset is the start of the chunk named plus that chunk's 8-byte header and size, so it moves with the conference, division and team counts; conf, div and teams are the counts stored in the chunk being skipped. The first chunk of each kind in `PNFL.lge` sits at 0x0000, 0x0063, 0x008A, 0x00B3, 0x0166 and 0x2557.

Teams are numbered 1..N in file order. Every other league file keyed by team uses that number (`.lg2`, `.rst`, `.dft`, `.tmn`, `.dat`).

---

## 2. Chunk: L03 — League (89 + conferences bytes)

Starts at 0x0000; the data below begins 8 bytes in, after the tag and size.

| Offset | Size | Type     | Name           | Description                                                                                                                    |
| -----: | ---: | :------- | :------------- | :----------------------------------------------------------------------------------------------------------------------------- |
|   0x00 |    1 | u8       | Unknown        | `0`-`5`                                                                                                                        |
|   0x01 |    1 | u8       | Conferences    | Conference count<br>`1` in the 8-12 team stock leagues, `2` elsewhere                                                          |
|   0x02 |    6 | u8[6]    | Unknown        | `00 0A 00 01 00 00` in `PNFL.lge`<br>`00 09 00 00 00 00` or `00 09 00 01 00 00` in stock leagues                               |
|   0x08 |    2 | u16      | Next player id | `9292` in `PNFL.lge`<br>`507` in `08_TEAMS`, whose `.pyr` holds ids 100-506                                                    |
|   0x0A |    2 | u16      | Base year      | Year of the first season<br>`1998` PNFL, `1966` NFLPI97R, `1994` small stock leagues<br>Season = base year + completed seasons |
|   0x0C |    3 | u8[3]    | Unknown        | `33 02 BF` in `PNFL.lge`<br>`00 02 3F` or `1F 02 3F` in stock leagues<br>Flips between `BF` and `3F` on some game saves        |
|   0x0F |   25 | char[25] | Name           | `"PNFL"`                                                                                                                       |
|   0x28 |   25 | char[25] | Championship   | `"Super Bowl"`                                                                                                                 |
|   0x41 |   17 | u8[17]   | Zero           |                                                                                                                                |
|   0x52 |    n | u8[n]    | Conference ids | One byte each (`01 02`)<br>n = the conference count                                                                            |
| 0x52+n |    7 | u8[7]    | Unknown        | `00 00 01 00 00 00 00` in `PNFL.lge`<br>`01 00 00 00 00 00 00` in stock leagues                                                |

The size is 89 + the conference count: 90 bytes with one conference, 91 with two.

---

## 3. Chunk: C03 — Conference (29 + divisions bytes)

Starts right after the L03 chunk (0x0063 in `PNFL.lge`); the data below begins 8 bytes in.

| Offset | Size | Type     | Name         | Description                                 |
| -----: | ---: | :------- | :----------- | :------------------------------------------ |
|   0x00 |    1 | u8       | Id           | 1-based                                     |
|   0x01 |    1 | u8       | Index        | 0-based                                     |
|   0x02 |    1 | u8       | Divisions    | Division count                              |
|   0x03 |    1 | u8       | Unknown      | `01`                                        |
|   0x04 |   25 | char[25] | Name         | Empty in `PNFL.lge`                         |
|   0x1D |    n | u8[n]    | Division ids | One byte each; n = the division count       |

---

## 4. Chunk: D03 — Division (29 + teams bytes)

Starts right after its conference's C03 chunk, or after the previous division's last R03 (first one at 0x008A in `PNFL.lge`); the data below begins 8 bytes in.

| Offset | Size | Type     | Name         | Description                              |
| -----: | ---: | :------- | :----------- | :--------------------------------------- |
|   0x00 |    1 | u8       | Id           | 1-based                                  |
|   0x01 |    1 | u8       | Conference   | Conference index, 0-based                |
|   0x02 |    1 | u8       | Index        | Division index within conference         |
|   0x03 |    1 | u8       | Teams        | Team count                               |
|   0x04 |   25 | char[25] | Name         | `"East"`, `"West"`                       |
|   0x1D |    n | u8[n]    | Team numbers | One byte each; n = the team count        |

---

## 5. Chunk: T03 — Team (171 bytes)

Starts right after its division's D03 chunk, or after the previous team's R03 (team 1 at 0x00B3 in `PNFL.lge`); the data below begins 8 bytes in.

Byte 0 is the team number, in clear. Bytes 1-170 are masked (section 8); offsets below are into the unmasked 170 bytes.

| Offset | Size | Type      | Name            | Description                                                                     |
| -----: | ---: | :-------- | :-------------- | :------------------------------------------------------------------------------ |
|   0x00 |    1 | u8        | Conference      | Conference index                                                                |
|   0x01 |    1 | u8        | Division        | Division index within conference                                                |
|   0x02 |    1 | u8        | Slot            | Position in the division's team list                                            |
|   0x03 |    1 | u8        | City id         | `CITIES.DAT` city id (below)<br>"City" on the Team Settings screen              |
|   0x04 |    1 | u8        | Stadium type    | `0` outdoor/grass, `1` other outdoor, `2` dome (below)                          |
|   0x05 |    1 | u8        | Ownership       | `0` Computer, `1` Human                                                         |
|   0x06 |    1 | u8        | Playcall mode   | `0` Basic, `1` Standard, `2` Advanced                                           |
|   0x07 |    1 | u8        | Action mode     | `0` Basic, `1` Standard, `2` Advanced                                           |
|   0x08 |    1 | u8        | Management      | `0` Computer, `1` Human                                                         |
|   0x09 |   33 | u8[11][3] | Colors          | 11 RGB triplets, each component 0-63; slots below                               |
|   0x2A |    6 | u8[6]     | Offense profile | Team Profile weights, pass then rush<br>Each aggressive, balanced, conservative |
|   0x30 |    6 | u8[6]     | Defense profile | Team Profile weights, same order                                                |
|   0x36 |   17 | char[17]  | Team name       | `"Denver"`<br>"Team Name" on the Team Settings screen                           |
|   0x47 |   17 | char[17]  | Nickname        | `"Broncos"`                                                                     |
|   0x58 |    5 | char[5]   | Abbreviation    | `"DEN"`                                                                         |
|   0x5D |   17 | char[17]  | Stadium         | `"Empire Field"`; a 17-character name has no NUL                                |
|   0x6E |   17 | char[17]  | Head coach      | `"Brian Jacobs"`<br>"Head Coach" on the Team Settings screen                    |
|   0x7F |   19 | u8[19]    | Unknown         | Leftover text at 0x88-0x8E; u16 at 0x8F; `0xFF` at 0x91                         |
|   0x92 |   15 | u8[15]    | Zero            |                                                                                 |
|   0xA1 |    9 | char[9]   | Draft profile   | Draft Profile Name, e.g. `"DEFAULT4"`: the game folder's `DEFAULT4.DP`          |

The city id names a city in `CITIES.DAT` ([cities.md](cities.md)). The stadium type appears to come from that city's stadium type, set when the game saves the team; third-party tools may set other values.

Color slots:

| Slot | Color               | Note                                |
| ---: | :------------------ | :---------------------------------- |
|    0 | Helmet              |                                     |
|    1 | Light jersey        | Also the shoes                      |
|    2 | Dark jersey         |                                     |
|    3 | Light pants         | Also the helmet trim                |
|    4 | Dark pants          |                                     |
|    5 | Light jersey stripe |                                     |
|    6 | Dark jersey stripe  |                                     |
|    7 | Light pants stripe  | Also the helmet stripe and facemask |
|    8 | Dark pants stripe   |                                     |
|    9 | Light sock stripe   |                                     |
|   10 | Dark sock stripe    |                                     |

Number colors are in the `.lg2` ([lg2.md](lg2.md)).

---

## 6. Chunk: R03 — Roster (325 bytes)

Starts 179 bytes after its team's T03 (team 1 at 0x0166 in `PNFL.lge`); the data below begins 8 bytes in.

Bytes 0-1 are the team number (u16), in clear. Bytes 2-324 are masked (section 8); offsets below are into the unmasked 323 bytes.

| Offset | Size | Type     | Name          | Description                                                         |
| -----: | ---: | :------- | :------------ | :------------------------------------------------------------------ |
|   0x00 |  126 | u16[63]  | Players       | Player ids (`.pyr`), `0` = empty slot; the slot sets status (below) |
|   0x7E |   63 | u8[63]   | Numbers       | Jersey number per slot, same order                                  |
|   0xBD |   10 | u8[10]   | Unknown       | A permutation of 0-9 (below)                                        |
|   0xC7 |   64 | u8[8][8] | Training camp | Training percentages, one row per position group (below)            |
|  0x107 |   60 | u8[60]   | Unknown       | The same in every team and every season (below)                     |

`pnfl.rst` is these 18 chunks, byte for byte, in the sample, except training camp (below); in the 2048 preseason copies its permutations differ (below).

Slot status, the "A"/"O"/"I"/"IF" column of the game's roster screen; no status byte exists. Slots are counted from 1 here, in array order:

| Slots | Status          | Screen | Note                                                    |
| ----: | :-------------- | :----- | :------------------------------------------------------ |
|  1-34 | Assigned        | "A"    | The depth chart (below)                                 |
| 35-46 | Open Active     | "O"    | Depth numbers carry on (WR5, WR6)                       |
| 47-53 | Open Inactive   | "I"    | No depth number                                         |
| 54-63 | Injured Reserve | "IF"   | The game's ten IR slots; not in the roster counts       |

Checked against Denver's roster screen: Assigned 34, Open Active 12, Open Inactive 7. Denver's slots 54-63 hold two injured players and eight healthy ones: a player stays on IR until the next season, even once healed, and the PNFL also uses the IR slots as a practice squad.

Depth chart slots, the same in all 18 teams of `PNFL.lge`:

| Slots | Group           | Positions |
| ----: | :-------------- | :-------- |
|   1-2 | Quarterbacks    | QB        |
|   3-5 | Running backs   | HB, FB    |
|  6-10 | Receivers       | WR, TE    |
| 11-16 | Offensive line  | C, G, T   |
| 17-20 | Defensive line  | DE, DT    |
| 21-25 | Linebackers     | LB        |
| 26-32 | Defensive backs | S, CB     |
|    33 | Kicker          | K         |
|    34 | Punter          | P         |

Order inside a group is depth: the roster screen numbers each position in slot order (QB1, QB2, DE1). Positions mix inside a group (Las Vegas lists a TE first among its receivers).

Permutation (0xBD), checked against the stock leagues and the league's saved 2048 copies (`E:\PNFL\League - League Files\2048`, 125 `PNFL.lge` and `pnfl.rst` files, preseason to week 17):

- Every team in a file has a different one, except in the 30-team NFL stock leagues: they have only 28, so two pairs of teams share one each.
- The NFL stock leagues (`NFLPA92` to `NFLPI97R`, `_default`, `Sierra`, `Test`) all use the same 28.
- The 8-18 team stock leagues (`08_TEAMS` to `18_TEAMS`) share some of theirs with each other.
- The 0 is last in `PNFL.lge`, its 2048 copies and the NFL stock leagues; the 8-18 team stock leagues put it anywhere.
- It changes once a season, at the rollover (weeks played back to 0), and stays fixed from preseason to the last week. Each team gets its own new one: none is shifted, reversed or passed to another team; two teams kept theirs at the 2049 rollover.
- In the 2048 preseason copies, the `pnfl.rst` permutations differ from the `.lge`'s; from week 1 on they match.

Training camp (0xC7): the game's Training Camp screen, opened with the Camp Setup button and saved with Accept Settings. One 8-byte row per position group, in the screen's column order:

| Offset | Size | Type  | Name  | Description         |
| -----: | ---: | :---- | :---- | :------------------ |
|   0xC7 |    8 | u8[8] | QB's  | Quarterbacks        |
|   0xCF |    8 | u8[8] | RB's  | Running backs       |
|   0xD7 |    8 | u8[8] | REC's | Receivers           |
|   0xDF |    8 | u8[8] | OL's  | Offensive line      |
|   0xE7 |    8 | u8[8] | DL's  | Defensive line      |
|   0xEF |    8 | u8[8] | LB's  | Linebackers         |
|   0xF7 |    8 | u8[8] | DB's  | Defensive backs     |
|   0xFF |    8 | u8[8] | P/K   | Punters and kickers |

Each row holds one byte per attribute (the screen's rows), in the `.pyr` ratings order, not the screen's:

| Byte      | 0   | 1   | 2   | 3   | 4   | 5   | 6   | 7   |
| :-------- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| Attribute | AC  | AG  | DI  | EN  | HA  | IN  | SP  | ST  |

Each byte is a percentage, `0`-`100`, and a row totals at most 100. A team never set up is all zero.

60-byte table (0x107): identical in every team, in all 125 copies of the 2048 season and in the 2049 sample. Every hex digit is 1-7; the last two 4-byte groups are equal.

```
11 22 53 42 23 21 12 54 23 21 14 25
23 21 14 52 23 31 15 14 23 22 13 52
32 22 12 53 15 22 12 52 33 22 11 44
25 22 11 52 22 21 23 44 43 31 22 14
22 31 24 24 11 16 12 71 11 16 12 71
```

---

## 7. Chunk: S03 — Schedule (928 bytes in `PNFL.lge`)

Starts right after the last R03 (0x2557 in `PNFL.lge`); the data below begins 8 bytes in.

| Offset |   Size | Type | Name           | Description                             |
| -----: | -----: | :--- | :------------- | :-------------------------------------- |
|   0x00 |      1 | u8   | Regular weeks  | `16`                                    |
|   0x01 |      1 | u8   | Playoff rounds | `3`                                     |
|   0x02 |      1 | u8   | Weeks played   | `6`; equals the weeks that carry scores; `255` after the last playoff game |
|   0x03 | varies | week | Weeks          | regular weeks + playoff rounds weeks    |

Week: a u8 game count, then that many games of 6 bytes:

| Offset | Size | Type | Name     | Description                                 |
| -----: | ---: | :--- | :------- | :------------------------------------------ |
|   0x00 |    1 | u8   | Team A   | Home team number; `0xFF` when not yet known |
|   0x01 |    1 | u8   | Score A  | `0xFF` when not played                      |
|   0x02 |    1 | u8   | Team B   | Away team number                            |
|   0x03 |    1 | u8   | Score B  |                                             |
|   0x04 |    1 | u8   | Overtime | `1` on 3 of 54 played games                 |
|   0x05 |    1 | u8   | Status   | `0` played, `2` not played                  |

Team A is home, team B away. Each team is home 8 times and away 8 times in `PNFL.lge`. Playoff weeks in `PNFL.lge` hold 4, 2 and 1 games.

---

## 8. Mask

T03 and R03 data is XORed byte by byte with (0x69 × team + i) mod 256, team the team number from the chunk's clear bytes, i the offset into the masked bytes (0 for the first masked byte). A run of zero bytes therefore reads as values stepping up by 1. L03, C03, D03 and S03 are not masked.

---

## 9. Open Questions

- L03 bytes 0x00, 0x02-0x07, 0x0C-0x0E and the 7-byte tail
- C03 byte 0x03
- T03 bytes 0x7F-0x91
- Whether the game shows the T03 stadium name: Denver's weather screen says `Mile High Stadium`, the chunk `Empire Field`
- What the R03 permutation and the 60-byte table mean
