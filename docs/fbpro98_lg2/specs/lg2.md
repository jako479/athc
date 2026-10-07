# .lg2 - Front Page Sports Football Pro '98 League File Format

- **Status:** Draft (the 9 trailing bytes per team have no known meaning)
- **Owner:** FBPro98 Lg2 Library
- **Encoding:** Strings ASCII.

A `.lg2` lists the coaching profile and game plan files each team in a league uses. It is named after its league (`PNFL.lg2`) and sits in the game folder. It comes in three layouts, each specified in full below: custom league (section 2), modern stock league (section 3), old stock league (section 4).

---

## 1. Team Order

- Teams come in the league's `.lge` team-number order, 1 first ([lge.md](../../fbpro98_lge/specs/lge.md)).
- That is the `.lge` tree order: conference, then division, then the division's team list.
- Verified by name for the custom league (`PNFL`) and the modern stock league (`NFLPI97R`); an old stock league's entries all carry the same filenames, so its order cannot be checked.
- Team `n` of the `.lg2` is team `n` in every other league file: rosters, schedule, draft order and stats.

---

## 2. Custom League

A league whose teams use the coaches' own files. Sample: `PNFL.lg2` (18 teams, 75,474 bytes).

### 2.1 File Layout

One team record per team, back to back, with no header or trailer. Total file length = `teams × 0x1061` (4193). The team count is not stored.

```
team[0]
  file[0..7]  folder + filename
  trailer
team[1]
...
```

| Offset |   Size | Name    | Description                   | Section |
| -----: | -----: | :------ | :---------------------------- | :------ |
| 0x0000 | 0x1061 | team[0] | First team record             | 2.2     |
| 0x1061 | 0x1061 | team[1] | Second team record            | 2.2     |
|    ... |    ... | ...     | One record per remaining team | 2.2     |

Team order is the league's `.lge` team order: team 1 first (see section 1).

### 2.2 Team Record (0x1061 bytes)

Starts at `team index × 0x1061`.

| Offset |   Size | Name    | Description                   | Section |
| -----: | -----: | :------ | :---------------------------- | :------ |
| 0x0000 |  0x20B | file[0] | 1st half offensive profile    | 2.3     |
| 0x020B |  0x20B | file[1] | 1st half offensive game plan  | 2.3     |
| 0x0416 |  0x20B | file[2] | 1st half defensive profile    | 2.3     |
| 0x0621 |  0x20B | file[3] | 1st half defensive game plan  | 2.3     |
| 0x082C |  0x20B | file[4] | 2nd half offensive profile    | 2.3     |
| 0x0A37 |  0x20B | file[5] | 2nd half offensive game plan  | 2.3     |
| 0x0C42 |  0x20B | file[6] | 2nd half defensive profile    | 2.3     |
| 0x0E4D |  0x20B | file[7] | 2nd half defensive game plan  | 2.3     |
| 0x1058 |      9 | trailer | Unknown 9-byte entry          | 2.2.1   |

#### 2.2.1 Trailer (9 bytes)

Starts at 0x1058 of the team record.

| Offset | Size | Type | Name    | Description                |
| -----: | ---: | :--- | :------ | :------------------------- |
|   0x00 |    1 | u8   | unknown | `0` or `1`                 |
|   0x01 |    4 | u32  | unknown | `0`-`5`, mostly `2` or `3` |
|   0x05 |    4 | u32  | unknown | `0`-`5`, mostly `2` or `3` |

Meaning unknown; nothing in the league's other files matches. Teams in `PNFL.lg2` outside the common values:

- Byte: none, all `1`.
- First u32: Las Vegas `0`; Pittsburgh, Atlanta, Green Bay `4`; the rest `2` or `3`.
- Second u32: Pittsburgh `0`; Green Bay `5`; Jacksonville, Las Vegas, Chicago `4`; the rest `2` or `3`.

### 2.3 File Entry (0x20B bytes)

Starts at `entry index × 0x20B` of the team record.

| Offset |  Size | Type        | Name     | Description                                                                                |
| -----: | ----: | :---------- | :------- | :----------------------------------------------------------------------------------------- |
|  0x000 | 0x105 | char[0x105] | folder   | NUL-terminated folder, relative to the game folder (e.g. `PNFL\2049\Plans\Denver (Brian)`) |
|  0x105 | 0x106 | char[0x106] | filename | NUL-terminated filename (e.g. `DEN-OFF1.prf`)                                              |

The file is `folder\filename` under the game folder. Bytes after each NUL are leftovers from an earlier, longer value and are ignored:

```
0x0000  PNFL\2049\Plans\Jacksonville (Matt) 00 Tim) 00 00 ...   folder   = PNFL\2049\Plans\Jacksonville (Matt)
0x0105  JAGS-O1.prf 00 f 00 f 00 00 ...                         filename = JAGS-O1.prf
```

---

## 3. Modern Stock League

A league whose teams use the game's stock files. Samples: `NFLPI96.LG2`, `NFLPI97.LG2`, `NFLPI97R.LG2` (30 teams, 125,790 bytes each).

### 3.1 File Layout

One team record per team, back to back, with no header or trailer. Total file length = `teams × 0x1061` (4193). The team count is not stored.

```
team[0]
  file[0..7]  folder + filename
  trailer
team[1]
...
```

| Offset |   Size | Name    | Description                   | Section |
| -----: | -----: | :------ | :---------------------------- | :------ |
| 0x0000 | 0x1061 | team[0] | First team record             | 3.2     |
| 0x1061 | 0x1061 | team[1] | Second team record            | 3.2     |
|    ... |    ... | ...     | One record per remaining team | 3.2     |

Team order is the league's `.lge` team order: team 1 first (see section 1).

### 3.2 Team Record (0x1061 bytes)

Starts at `team index × 0x1061`.

| Offset |   Size | Name    | Description                   | Section |
| -----: | -----: | :------ | :---------------------------- | :------ |
| 0x0000 |  0x20B | file[0] | 1st half offensive profile    | 3.3     |
| 0x020B |  0x20B | file[1] | 1st half offensive game plan  | 3.3     |
| 0x0416 |  0x20B | file[2] | 1st half defensive profile    | 3.3     |
| 0x0621 |  0x20B | file[3] | 1st half defensive game plan  | 3.3     |
| 0x082C |  0x20B | file[4] | 2nd half offensive profile    | 3.3     |
| 0x0A37 |  0x20B | file[5] | 2nd half offensive game plan  | 3.3     |
| 0x0C42 |  0x20B | file[6] | 2nd half defensive profile    | 3.3     |
| 0x0E4D |  0x20B | file[7] | 2nd half defensive game plan  | 3.3     |
| 0x1058 |      9 | trailer | Unknown 9-byte entry          | 3.2.1   |

#### 3.2.1 Trailer (9 bytes)

Starts at 0x1058 of the team record.

| Offset | Size | Type | Name    | Description                |
| -----: | ---: | :--- | :------ | :------------------------- |
|   0x00 |    1 | u8   | unknown | `0` or `1`                 |
|   0x01 |    4 | u32  | unknown | `0`-`5`, mostly `2` or `3` |
|   0x05 |    4 | u32  | unknown | `0`-`5`, mostly `2` or `3` |

Meaning unknown; nothing in the league's other files matches. Teams in `NFLPI97R.LG2` outside the common values:

- Byte: Dolphins, Cowboys `0`; the rest `1`.
- First u32: Buccaneers `5`; Ravens, Packers `4`; the rest `2` or `3`.
- Second u32: Bears, Falcons `0`; Ravens, Oilers, Giants, Packers, Buccaneers `5`; Jaguars, Steelers, Raiders, Lions `4`; the rest `2` or `3`.

### 3.3 File Entry (0x20B bytes)

Starts at `entry index × 0x20B` of the team record.

| Offset |  Size | Type        | Name     | Description                                                       |
| -----: | ----: | :---------- | :------- | :---------------------------------------------------------------- |
|  0x000 | 0x105 | char[0x105] | folder   | `"STOCK"`, NUL, `"A\FBPRO97\STOCK"`, NUL; the same in every entry |
|  0x105 | 0x106 | char[0x106] | filename | NUL-terminated filename (e.g. `BILLSO1.PRF`)                      |

The file is `STOCK\filename` under the game folder. `A\FBPRO97\STOCK` after the first NUL is leftover text, not a real folder:

```
0x0000  STOCK 00 A\FBPRO97\STOCK 00 00 ...   folder   = STOCK
0x0105  BILLSO1.PRF 00 00 ...                filename = BILLSO1.PRF
```

---

## 4. Old Stock League

A stock league from an older version of the game. Samples: `08_TEAMS.LG2` (8 teams, 33,544 bytes), `10_TEAMS.LG2`, `12_TEAMS.LG2`, `18_TEAMS.LG2`, `NFLPA92.LG2`, `NFLPA93.LG2`, `NFLPA93E.LG2`, `NFLPA94.LG2`, `NFLPA94E.LG2`, `NFLPI95.LG2`, `NFLPI95E.LG2`, `NFLPI96E.LG2`.

### 4.1 File Layout

One team record per team, back to back, with no header or trailer. Total file length = `teams × 0x1061` (4193). The team count is not stored.

```
team[0]
  file[0..7]  folder + filename
  trailer
team[1]
...
```

| Offset |   Size | Name    | Description                   | Section |
| -----: | -----: | :------ | :---------------------------- | :------ |
| 0x0000 | 0x1061 | team[0] | First team record             | 4.2     |
| 0x1061 | 0x1061 | team[1] | Second team record            | 4.2     |
|    ... |    ... | ...     | One record per remaining team | 4.2     |

Team order is the league's `.lge` team order: team 1 first (see section 1).

### 4.2 Team Record (0x1061 bytes)

Starts at `team index × 0x1061`.

| Offset |   Size | Name    | Description                   | Section |
| -----: | -----: | :------ | :---------------------------- | :------ |
| 0x0000 |  0x20B | file[0] | 1st half offensive profile    | 4.3     |
| 0x020B |  0x20B | file[1] | 1st half offensive game plan  | 4.3     |
| 0x0416 |  0x20B | file[2] | 1st half defensive profile    | 4.3     |
| 0x0621 |  0x20B | file[3] | 1st half defensive game plan  | 4.3     |
| 0x082C |  0x20B | file[4] | 2nd half offensive profile    | 4.3     |
| 0x0A37 |  0x20B | file[5] | 2nd half offensive game plan  | 4.3     |
| 0x0C42 |  0x20B | file[6] | 2nd half defensive profile    | 4.3     |
| 0x0E4D |  0x20B | file[7] | 2nd half defensive game plan  | 4.3     |
| 0x1058 |      9 | trailer | Unknown 9-byte entry          | 4.2.1   |

#### 4.2.1 Trailer (9 bytes)

Starts at 0x1058 of the team record.

| Offset | Size | Type | Name    | Description                |
| -----: | ---: | :--- | :------ | :------------------------- |
|   0x00 |    1 | u8   | unknown | `0` or `1`                 |
|   0x01 |    4 | u32  | unknown | `0`-`5`, mostly `2` or `3` |
|   0x05 |    4 | u32  | unknown | `0`-`5`, mostly `2` or `3` |

Meaning unknown; nothing in the league's other files matches. Teams in `08_TEAMS.LG2` outside the common values:

- Byte: none, all `1`.
- First u32: Calgary `4`; the rest `2` or `3`.
- Second u32: none, all `2` or `3`.

### 4.3 File Entry (0x20B bytes)

Starts at `entry index × 0x20B` of the team record.

| Offset |  Size | Type        | Name     | Description                                           |
| -----: | ----: | :---------- | :------- | :---------------------------------------------------- |
|  0x000 | 0x105 | char[0x105] | folder   | NUL, `"SIERRA\FBPRO97"`, NUL; the same in every entry |
|  0x105 | 0x106 | char[0x106] | filename | NUL-terminated filename (e.g. `OFF1.PRF`)             |

The folder is empty: byte `0x000` is NUL. `SIERRA\FBPRO97` after it is leftover text:

```
0x0000  00 SIERRA\FBPRO97 00 00 ...   folder   = (empty)
0x0105  OFF1.PRF 00 00 ...            filename = OFF1.PRF
```
