# PNFL league files: research notes

- Source: `E:\SIERRA\FbPro98\PNFL.*` as of 2026-10-02 (season 2049, 6 weeks played), read-only.
- Specs written from these notes: [lge.md](../../fbpro98_lge/specs/lge.md), [pyr.md](../../fbpro98_pyr/specs/pyr.md), [lg2.md](../../fbpro98_lg2/specs/lg2.md), [cities.md](../../fbpro98_cities/specs/cities.md). Overview: [fbpro98-files.md](../fbpro98-files.md).
- Decoder: [research/pnfl_decode.py](../../../research/pnfl_decode.py) (stdlib, read-only): `python pnfl_decode.py <game folder> teams | roster 5 | player 6283 | freeagents | schedule | champions | draft | tmn | stats 6283`.

## 1. Team order in PNFL.lg2

- The `.lg2` lists teams in `PNFL.lge` team-number order, 1-18.
- `PNFL.lge` is a tree, league > conference > division > team, written depth-first; each team chunk starts with (conference, division, slot) and each division chunk lists its team numbers.
- Inside a division the order is the division's list, not alphabetical.
- Stock leagues do the same (checked by name on `NFLPI97R`).
- Every other file keyed by team uses the same number: rosters, schedule, draft order, `.tmn`, team stat records.

| # | Conf/Div | Team | .lg2 folder |
|---|----------|------|-------------|
| 1 | 0/0 East | Jacksonville Jaguars | Jacksonville (Matt) |
| 2 | 0/0 East | San Diego Chargers | San Diego (Steve) |
| 3 | 0/0 East | New England Patriots | New England (Moxs) |
| 4 | 0/0 East | Miami Dolphins | Miami (Mitch) |
| 5 | 0/1 West | Denver Broncos | Denver (Brian) |
| 6 | 0/1 West | Las Vegas Raiders | Las Vegas (Neil) |
| 7 | 0/1 West | Cincinnati Bengals | Cincinnati (Dan) |
| 8 | 0/1 West | Baltimore Ravens | Baltimore (Larry) |
| 9 | 0/1 West | Pittsburgh Steelers | Pittsburgh (Donovon) |
| 10 | 1/0 East | Atlanta Falcons | Atlanta (Dean) |
| 11 | 1/0 East | New York Giants | New York (Shawn) |
| 12 | 1/0 East | Philadelphia Eagles | Philadelphia (James) |
| 13 | 1/0 East | Washington Redskins | Washington (Jerry) |
| 14 | 1/1 West | Green Bay Packers | Green Bay (Shuggy) |
| 15 | 1/1 West | Chicago Cardinals | Chicago (Justin) |
| 16 | 1/1 West | Detroit Lions | Detroit (Mark) |
| 17 | 1/1 West | Minnesota Vikings | Minnesota (Barney) |
| 18 | 1/1 West | San Francisco 49ers | San Francisco (Charlie) |

## 2. Masks

Two files are scrambled. Everything else is plain; leftover text after a NUL and junk in unused stat fields is uninitialized memory, not a mask.

### 2.1 Running XOR key: `.lge` team and roster chunks, `pnfl.rst`

- Applies to the T03 (team) and R03 (roster) chunks. The team number at the front of the chunk is plain: 1 byte in T03, 2 bytes in R03. Everything after it is masked.
- Key byte for masked byte number `i` (counting from 0 at the first masked byte): `(0x69 * team + i) mod 256`.
- Plain byte = disk byte XOR key byte. Masking again is the same operation.
- Zero bytes therefore show on disk as a run of values stepping up by 1, which is how the key was spotted.
- Example, team 1's T03: the first masked byte on disk is `0x69`; key `0x69 * 1 + 0 = 0x69`; plain `0x00`. Masked byte 3 is `0x7F`; key `0x6C`; plain `0x13`.
- Example, team 1's R03: the first two masked bytes on disk are `7A 66`; keys `0x69`, `0x6A`; plain `13 0C`, player id `0x0C13` = 3091, the first roster slot.

### 2.2 Byte substitution table: `.pyr`

- One table of 256 entries: each plain byte value is written as a fixed other value. In `PNFL.pyr` plain `0x00` is always written as `0xD3`.
- The same table is used for every byte of every record; the 60-byte header is plain.
- Every file has its own table (`0x00` is written as `0x0F` in `NFLPI97R.PYR`). No formula is known and the table is not stored.
- Any file gives up its table: each record starts with the player's id, and the id is known without decoding (record 0 is player 100, record 1 is player 101, and so on). Compare the known plain id bytes with the bytes on disk and each record tells you one or two table entries. Over 256 consecutive records the low id byte runs through all 256 values, so byte 0 alone yields the whole table.
- Example, `PNFL.pyr` record 0: player 100 = `0x0064`, plain bytes `64 00`; on disk `3F D3`. So plain `0x64` is written as `0x3F`, plain `0x00` as `0xD3`.
- Decoding: look up each disk byte in the reversed table. `PNFL.pyr`'s full table is in the appendix.

## 3. File by file

### PNFL.lge (10,495 B)

- Chunk stream: 4-char tag, u32 size, body; order L03, C03, D03, 4x(T03, R03), D03, 5x(T03, R03), C03, D03, 4x(T03, R03), D03, 5x(T03, R03), S03.
- L03 (91 B): next player id 9292 at byte 8, base year 1998 at byte 10 (1998 + 51 completed seasons = 2049), league name "PNFL" at 15, championship name "Super Bowl" at 40. Rest unknown.
- C03 (31 B): id, index, division count, unknown, 25-byte name (empty), division ids.
- D03 (33/34 B): id, conference index, division index, team count, 25-byte name ("East"/"West"), team numbers.
- T03 (171 B), masked after the team byte: conference, division, slot, city index (looks alphabetical), stadium type (0/1/2), `01 01 01 01`, 11 RGB triplets (0-63), 12 zeros, team name[17] @54, nickname[17] @71, abbreviation[5] @88, stadium[17] @93, head coach[17] @110, 19 unknown bytes (leftover text in the middle), 15 zeros, uniform set "DEFAULTn" @161.
- R03 (325 B), masked after the u16 team number: 63 u16 player ids (slots 60-62 held Denver's three inactive players), 63 jersey numbers in slot order, a permutation of 1-9, 65 zeros, a 60-byte table identical in all teams.
- S03 (928 B): 16 regular weeks, 3 playoff rounds, 6 weeks played; per week a count then 6-byte games: team A, score A, team B, score B, overtime, status (0 played, 2 not). Unplayed scores `0xFF`; playoff teams `0xFF`. Each team is A 8 times and B 8 times; which side is home is unverified.
- Every sampled `.lge` (1992 stock to PNFL) has the same chunk set and sizes; the 8-12 team stock leagues have a 90-byte L03.
- Check: team 5 unmasks to `Denver` / `Broncos` / `DEN` / `Empire Field` / `Brian Jacobs` / `DEFAULT8`; its roster starts `6283 6, 8428 2, 4552 31` (C. J. Stroud #6, Cam Ward #2, Isaiah Spiller #31) and matches the league's roster sheet slot for slot. Week 1 game 3 is `10 24 5 23 0 0`: Atlanta 24, Denver 23.

### pnfl.rst (5,994 B)

- The 18 R03 roster chunks, byte-identical to those in `PNFL.lge`.

### PNFL.pyr (551,580 B)

- 60-byte header (u16 key `0xCE5F`, then zeros) + 9,192 x 60-byte records; record `i` is player id `i + 100`.
- Record: id u16 @0, first name[13] @2, last name[13] @15, potential ratings[8] @28, injury[4] @36 (zero when healthy; 75 players non-zero), position group @40, position @41, actual ratings[8] @42, years @50, height @51 and weight u16 @52 (2049 rookies only), 6 unknown bytes.
- Ratings order AC AG DI EN HA IN SP ST. Positions 0 QB 1 FB 2 HB 3 TE 4 WR 5 C 6 G 7 T 8 DE 9 DT 10 LB 11 CB 12 S 13 K 14 P; groups QB 0, LB 10, K 13, P 14, RB 15, WR/TE 16, OL 17, DL 18, DB 19.
- 3,258 "No One" placeholders (ratings all 1), 191 "Delete Me", 114 "2043 Draft".
- Names, numbers, ratings and YRS match the league's roster sheets exactly. Not in the file: draft year/team/pick, depth, age.
- Check: C. J. Stroud (6283) QB, years 5, actual AC 81 AG 81 DI 83 EN 86 HA 71 IN 91 SP 81 ST 95; Dillon Gabriel (8430) QB, years 1, potential 81 81 84 85 71 90 80 95, actual 79 79 83 83 70 89 78 94.

### PNFL.dat (348,160 B) + PNFL.idx (225,280 B)

- `.dat`: 140-byte header (size-1, record count 0x426A = 17,002, record size 20, page size 4096), then 20-byte records: type u16, id u16, 8 x int16. Unused fields hold leftover memory. A 20-byte-stride scan finds 16,946 records.
- type = block + category. Blocks: 0 player last game, 32 player season, 64 player career, 96 team last game, 130 team season, 164 opponents' last game, 198 opponents' season (team records carry the team number as id).
- Categories: 0 field goals (att, made); 1 kicking detail (unresolved); 2 rushing (att, yds, long, TD); 3 passing (att, yds, long, TD, comp, INT, sacked, sack yds); 4 receiving (rec, yds, long, TD); 5 interceptions (n, yds, long, TD); 6 punting (punts, yds, long, 5 unresolved); 7 punt returns (n, yds, long, TD, FC?); 8 kick returns (n, yds, long, TD); 9 fumbles; 10 fumble recoveries (n, yds, long, TD); 11 sacks; 12 unknown defensive count (career only); 13 tackles; 14-17 unresolved.
- Cross-checks: Stroud's last-game passing equals Denver's team last-game line; Denver's season passing equals the sum of its three QBs' lines.
- `.idx`: 512-byte blocks (433 used, 7 unused filled with `0xFF`); 16-byte header (entry count u16 at 8, bytes used at 10) + 8-byte entries: key u16 big-endian (player or team id), 24-bit little-endian `.dat` offset, u16 zero, type byte. The offset lands on the record after the keyed one (unresolved), so scan `.dat` instead.

### PNFL.PYF (1,968 B), PNFL.PYC (10 B)

- `PPD:` tag, u32 size, u16 player ids. `.PYF`: 980 ids, none on a roster: the free-agent pool. `.PYC`: one zero entry.

### PNFL.dft (47 B)

- `DOD:` tag, size, u16 count 18, then 18 team numbers each paired with a 1: 12 PHI, 16 DET, 11 NYG, 8 BAL, 5 DEN, 18 SF, 1 JAX, 10 ATL, 14 GB, 6 LV, 3 NE, 17 MIN, 9 PIT, 2 SD, 7 CIN, 13 WAS, 15 CHI, 4 MIA. Denver 5th matches its rookies' "x-5" picks.

### PNFL.tmn (270 B)

- `FF FF FF`, then 89 x (team u8, player id u16). About 10 are stale (player since moved or released). Purpose unknown; trading block or similar.

### pnfl.lgc (2,244 B)

- 51 `LGC:` records: winner name[17], score u8, loser name[17], score u8. Latest: Miami 34, Chicago 33.

### CITIES.DAT (14,328 B)

- The game's city table, one copy in the game folder, 128 cities: weather odds and home stadium per city. Layout in [cities.md](../../fbpro98_cities/specs/cities.md).
- Check: `PNFL.lge` team chunks name their city by this id: Atlanta `2`, Chicago `8`, Cincinnati `9`, Denver `12`, Detroit `13`, Jacksonville `19`, Miami `24`, Minnesota `26` (Minneapolis), New York `29`, Philadelphia `31`, Pittsburgh `33`, San Diego `36`, San Francisco `37`, Washington `43`, Green Bay `49`, Baltimore `50`, New England `52` (Foxboro); Las Vegas stores `40`, which is Toronto's record, and the game's Team Settings screen indeed shows its City as Toronto.

## 4. Ease of reverse engineering

- Trivial, done: `.PYF`, `.PYC`, `.dft`, `.tmn`, `.lgc`, `.lg2`.
- Easy, done: `.lge` and `.rst` (one XOR formula), `.pyr` (table from the file).
- Medium, mostly done: `.dat` (fixed records, some categories unlabeled). `.idx` matters only for writing.

## 5. Still open

- Not in these files: draft year/team/pick, age, depth (depth is in the `.prf`).
- Unknown: roster 1-9 permutation and 60-byte table; T03 bytes 3, 4, 127-145 and the color slot order; stat categories 1, 12, 14-17; L03 bytes 0-7, 12-14, 65-90; schedule home/away side; `.tmn` purpose; `.pyr` injury sub-fields and header key.

## Appendix: PNFL.pyr substitution table (plain -> coded)

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
