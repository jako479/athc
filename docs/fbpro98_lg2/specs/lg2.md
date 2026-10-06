# .lg2 - Front Page Sports Football Pro '98 League File Format

- **Status:** Draft (9 trailing bytes per team not yet reverse engineered)
- **Owner:** FBPro98 Lg2 Library
- **Encoding:** Strings ASCII.

A `.lg2` lists the coaching profile and game plan files each team in a league uses. It is named after its league (`PNFL.lg2`) and sits in the game folder. It comes in three layouts, each specified in full below: custom league (section 1), modern stock league (section 2), old stock league (section 3).

---

## 1. Custom League

A league whose teams use the coaches' own files. Sample: `PNFL.lg2` (18 teams, 75,474 bytes).

### 1.1 File Layout

One team record per team, back to back, with no header or trailer. Total file length = `teams × 0x1061` (4193). The team count is not stored.

| Offset |   Size | Name    | Description                      |
| -----: | -----: | :------ | :------------------------------- |
| 0x0000 | 0x1061 | team[0] | First team record (section 1.2)  |
| 0x1061 | 0x1061 | team[1] | Second team record (section 1.2) |
|    ... |    ... | ...     | One record per remaining team    |

Team order is unknown.

### 1.2 Team Record (0x1061 bytes)

| Offset | Type       | Name    | Description                                          |
| -----: | :--------- | :------ | :--------------------------------------------------- |
| 0x0000 | file_entry | file[0] | 1st half offensive profile (section 1.3)             |
| 0x020B | file_entry | file[1] | 1st half offensive game plan (section 1.3)           |
| 0x0416 | file_entry | file[2] | 1st half defensive profile (section 1.3)             |
| 0x0621 | file_entry | file[3] | 1st half defensive game plan (section 1.3)           |
| 0x082C | file_entry | file[4] | 2nd half offensive profile (section 1.3)             |
| 0x0A37 | file_entry | file[5] | 2nd half offensive game plan (section 1.3)           |
| 0x0C42 | file_entry | file[6] | 2nd half defensive profile (section 1.3)             |
| 0x0E4D | file_entry | file[7] | 2nd half defensive game plan (section 1.3)           |
| 0x1058 | u8[9]      | unknown | Not reverse engineered; not needed to read the files |

### 1.3 File Entry (0x20B bytes)

| Offset | Type        | Name     | Description                                                                                |
| -----: | :---------- | :------- | :----------------------------------------------------------------------------------------- |
|  0x000 | char[0x105] | folder   | NUL-terminated folder, relative to the game folder (e.g. `PNFL\2049\Plans\Denver (Brian)`) |
|  0x105 | char[0x106] | filename | NUL-terminated filename (e.g. `DEN-OFF1.prf`)                                              |

The file is `folder\filename` under the game folder. Bytes after each NUL are leftovers from an earlier, longer value and are ignored:

```
0x0000  PNFL\2049\Plans\Jacksonville (Matt) 00 Tim) 00 00 ...   folder   = PNFL\2049\Plans\Jacksonville (Matt)
0x0105  JAGS-O1.prf 00 f 00 f 00 00 ...                         filename = JAGS-O1.prf
```

---

## 2. Modern Stock League

A league whose teams use the game's stock files. Samples: `NFLPI96.LG2`, `NFLPI97.LG2`, `NFLPI97R.LG2` (30 teams, 125,790 bytes each).

### 2.1 File Layout

One team record per team, back to back, with no header or trailer. Total file length = `teams × 0x1061` (4193). The team count is not stored.

| Offset |   Size | Name    | Description                      |
| -----: | -----: | :------ | :------------------------------- |
| 0x0000 | 0x1061 | team[0] | First team record (section 2.2)  |
| 0x1061 | 0x1061 | team[1] | Second team record (section 2.2) |
|    ... |    ... | ...     | One record per remaining team    |

Team order is unknown.

### 2.2 Team Record (0x1061 bytes)

| Offset | Type       | Name    | Description                                          |
| -----: | :--------- | :------ | :--------------------------------------------------- |
| 0x0000 | file_entry | file[0] | 1st half offensive profile (section 2.3)             |
| 0x020B | file_entry | file[1] | 1st half offensive game plan (section 2.3)           |
| 0x0416 | file_entry | file[2] | 1st half defensive profile (section 2.3)             |
| 0x0621 | file_entry | file[3] | 1st half defensive game plan (section 2.3)           |
| 0x082C | file_entry | file[4] | 2nd half offensive profile (section 2.3)             |
| 0x0A37 | file_entry | file[5] | 2nd half offensive game plan (section 2.3)           |
| 0x0C42 | file_entry | file[6] | 2nd half defensive profile (section 2.3)             |
| 0x0E4D | file_entry | file[7] | 2nd half defensive game plan (section 2.3)           |
| 0x1058 | u8[9]      | unknown | Not reverse engineered; not needed to read the files |

### 2.3 File Entry (0x20B bytes)

| Offset | Type        | Name     | Description                                                       |
| -----: | :---------- | :------- | :---------------------------------------------------------------- |
|  0x000 | char[0x105] | folder   | `"STOCK"`, NUL, `"A\FBPRO97\STOCK"`, NUL; the same in every entry |
|  0x105 | char[0x106] | filename | NUL-terminated filename (e.g. `BILLSO1.PRF`)                      |

The file is `STOCK\filename` under the game folder. `A\FBPRO97\STOCK` after the first NUL is leftover text, not a real folder:

```
0x0000  STOCK 00 A\FBPRO97\STOCK 00 00 ...   folder   = STOCK
0x0105  BILLSO1.PRF 00 00 ...                filename = BILLSO1.PRF
```

---

## 3. Old Stock League

A stock league from an older version of the game. Samples: `08_TEAMS.LG2` (8 teams, 33,544 bytes), `10_TEAMS.LG2`, `12_TEAMS.LG2`, `18_TEAMS.LG2`, `NFLPA92.LG2`, `NFLPA93.LG2`, `NFLPA93E.LG2`, `NFLPA94.LG2`, `NFLPA94E.LG2`, `NFLPI95.LG2`, `NFLPI95E.LG2`, `NFLPI96E.LG2`.

### 3.1 File Layout

One team record per team, back to back, with no header or trailer. Total file length = `teams × 0x1061` (4193). The team count is not stored.

| Offset |   Size | Name    | Description                      |
| -----: | -----: | :------ | :------------------------------- |
| 0x0000 | 0x1061 | team[0] | First team record (section 3.2)  |
| 0x1061 | 0x1061 | team[1] | Second team record (section 3.2) |
|    ... |    ... | ...     | One record per remaining team    |

Team order is unknown.

### 3.2 Team Record (0x1061 bytes)

| Offset | Type       | Name    | Description                                          |
| -----: | :--------- | :------ | :--------------------------------------------------- |
| 0x0000 | file_entry | file[0] | 1st half offensive profile (section 3.3)             |
| 0x020B | file_entry | file[1] | 1st half offensive game plan (section 3.3)           |
| 0x0416 | file_entry | file[2] | 1st half defensive profile (section 3.3)             |
| 0x0621 | file_entry | file[3] | 1st half defensive game plan (section 3.3)           |
| 0x082C | file_entry | file[4] | 2nd half offensive profile (section 3.3)             |
| 0x0A37 | file_entry | file[5] | 2nd half offensive game plan (section 3.3)           |
| 0x0C42 | file_entry | file[6] | 2nd half defensive profile (section 3.3)             |
| 0x0E4D | file_entry | file[7] | 2nd half defensive game plan (section 3.3)           |
| 0x1058 | u8[9]      | unknown | Not reverse engineered; not needed to read the files |

### 3.3 File Entry (0x20B bytes)

| Offset | Type        | Name     | Description                                           |
| -----: | :---------- | :------- | :---------------------------------------------------- |
|  0x000 | char[0x105] | folder   | NUL, `"SIERRA\FBPRO97"`, NUL; the same in every entry |
|  0x105 | char[0x106] | filename | NUL-terminated filename (e.g. `OFF1.PRF`)             |

The folder is empty: byte `0x000` is NUL. `SIERRA\FBPRO97` after it is leftover text:

```
0x0000  00 SIERRA\FBPRO97 00 00 ...   folder   = (empty)
0x0105  OFF1.PRF 00 00 ...            filename = OFF1.PRF
```

---

## 4. Reader Contract

- API: `read_lg2(path)` → parsed `Lg2File`; `parse_lg2(buffer, path)` parses raw bytes.
- Exposes: `teams`, each with `first_half` / `second_half` → `offense` / `defense` → `profile` / `gameplan`. Each is a string, `folder\filename` relative to the game folder, or just `filename` when the folder is empty.
- Raises `InvalidLg2Error` when the file is empty or not a whole number of team records, a folder or filename field has no NUL, or a filename is empty.
- Raises `UnsupportedLg2Error` when the first folder field starts with `STOCK\0A\FBPRO97\STOCK\0` (section 2) or with a NUL (section 3). Only the first entry decides.
- Checks run in order: size, then stock, then fields.

---

## 5. Validation & Test Vectors

Fixtures: `PNFL.lg2` (custom), `NFLPI97.LG2` (modern stock), `08_TEAMS.LG2` (old stock). Tests pin three custom teams' files, reject both stock layouts, and check each limit on built bytes: file size, folder and filename field length, and empty filename.

---

## 6. Open Questions

- The 9 trailing bytes of each team record
- Team order, and how it maps to the league's other files
- Whether a custom league can mix in stock entries
- Where the game looks for an old stock league's files
