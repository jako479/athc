# .pln - Front Page Sports Football Pro '98 Game Plan File Format

- **Status:** Complete
- **Owner:** FBPro98 Gameplan Library
- **Encoding:** Integers are little-endian; strings are ASCII unless noted.

---

## 1. File Layout

A `.pln` is three blocks in order: **G95** (offsets and play records), **J95** (summary counts), **S98** (stock map filename). Each block begins with a header: ID (4 bytes) + size (4 bytes). Size is the data length excluding the 8 bytes of ID + size.

```
G95  index + play records
  header  ID + size
  audible
  offsets  one per play slot (86)
  play records  one per filled slot, custom or stock
J95  summary counts
S98  stock map filename
pad  defense only
```

| Offset        |     Size | Name | Description                       | Section |
| :------------ | -------: | :--- | :-------------------------------- | :------ |
| 0x0000        |        8 | G95  | Header: ID + size                 | 2.1     |
| 0x0008        |        4 | G95  | Audible                           | 2.1     |
| 0x000C        |      172 | G95  | Play record offsets (u16 × 86)    | 2.2     |
| 0x00B8        | variable | G95  | Play records, packed back-to-back | 2.3, 3  |
| 8 + G95 size  |       15 | J95  | Header + 7 bytes of counts        | 4       |
| 23 + G95 size |       20 | S98  | Header + `"STOCK98.MAP\0"`        | 5       |
| 43 + G95 size |   0 or 1 | —    | Trailing parity pad, defense only | 6       |

---

## 2. Block: G95 — Index + Play Records

Starts at 0x0000.

### 2.1 Header (12 bytes)

Starts at 0x0000.

| Offset | Size | Type    | Name    | Description                                      |
| -----: | ---: | :------ | :------ | :----------------------------------------------- |
| 0x0000 |    4 | char[4] | ID      | `"G95:"`                                         |
| 0x0004 |    4 | u32     | Size    | Data size in bytes (everything after this field) |
| 0x0008 |    4 | u8[4]   | Audible | Audible play indices; always `00 01 02 03`       |

Total G95 block length = 8 + size. Any audible other than `00 01 02 03` is invalid.

### 2.2 Offsets Table (172 bytes)

Starts at 0x000C.

| Offset | Size | Type    | Name    | Description                             |
| -----: | ---: | :------ | :------ | :-------------------------------------- |
| 0x000C |  172 | u16[86] | Offsets | Play record offsets; `0x0000` = no play |

Always 86 entries, in both offensive and defensive game plans. Offsets are relative to byte 0x0C (end of G95 header). The first play record begins at byte 0xB8 (12 header + 172 offsets). Which play each offset points to is in section 3.

### 2.3 Play Record (variable size)

Records are packed from 0x00B8; each one is reached through the offsets table (section 2.2).

| Offset | Size | Type | Name             | Description                                                                               |
| -----: | ---: | :--- | :--------------- | :---------------------------------------------------------------------------------------- |
|   0x00 |    1 | u8   | Stock flag       | `0` = custom play, `1` = stock play                                                       |
|   0x01 |    1 | u8   | Play category    | Copy of the play file's byte 0x001E; values in ply.md section 3                           |
|   0x02 |    1 | u8   | Special category | Copy of the play file's byte 0x001F; `0x00` = normal, `0x01`–`0x0C` = special (section 3) |
|   0x03 |    1 | u8   | User category    | Copy of the play file's byte 0x0020; values in ply.md section 3                           |

The game plan defines no category values of its own. For a custom play the three bytes are a verbatim copy of bytes 0x001E–0x0020 of the referenced `.ply`, bits 7–6 included; every custom record in the PNFL 2049 plans matched its play file (1,835 of 1,835 on 2026-10-07). The values are defined once, in [ply.md section 3](../../fbpro98_play/specs/ply.md#3-play-categories).

Stock plays have no `.ply` to copy from. The game writes play category = user category = `0x01` (offense) or `0x00` (defense) and the slot's special category. `0x0B` (Run Clock) and `0x0C` (Stop Clock) exist only here, as offensive stock records; no play file carries them.

Trailing fields after the 4-byte header depend on the stock flag:

If the stock flag is `0` (custom play):

| Offset |   Size | Type | Name     | Description                                                               |
| -----: | -----: | :--- | :------- | :------------------------------------------------------------------------ |
|   0x04 | varies | cstr | Filename | NUL-terminated ASCII play file path (cstr = ASCII bytes ending in `0x00`) |

If the stock flag is `1` (stock play):

| Offset | Size | Type    | Name       | Description                           |
| -----: | ---: | :------ | :--------- | :------------------------------------ |
|   0x04 |    8 | char[8] | Play name  | Fixed 8-byte ASCII name (NUL-padded)  |
|   0x0C |    4 | u32     | Map offset | Opaque pointer into unknown game file |
|   0x10 |    2 | u16     | Map size   | Opaque size into unknown game file    |

Map offset and map size reference the external `STOCK98.MAP` file; the gameplan library carries them through unchanged on round-trip.

---

## 3. Play Slots

Coaches assign plays to slots. The Game Plan Editor shows the normal slots as a 16 × 4 grid, 1-1 through 16-4, and the special slots on its Special Plays screen.

The offsets are fixed: offsets 0–63 always correspond to game plan slots 1-1 through 16-4, row-major, and offsets 64–85 always correspond to the special slots, keyed by special category (`0x01`–`0x0C`). Defensive game plans have no clock plays, so their offsets 84 and 85 are always `0x0000`.

An empty slot has its offset zeroed and contributes no play record. The play records are packed back-to-back regardless of any empty slots. Normal and non-stock special slots are optional; the stock specials are always present (10 on defense, 12 on offense with the two clock plays).

### 3.1 Offensive Game Plans (86 slots)

| Offsets | Count | Purpose                                         |
| :------ | ----: | :---------------------------------------------- |
| 0–63    |    64 | Normal slots 1-1–16-4 (special category `0x00`) |
| 64–85   |    22 | Special slots (special category `0x01`–`0x0C`)  |

Categories `0x01`–`0x0A` get two slots each, non-stock then stock; categories `0x0B` and `0x0C` get one stock slot each.

| Offsets | Special category | Category Name  | Version          |
| :------ | :--------------- | :------------- | :--------------- |
| 64–65   | `0x01`           | FG/PAT         | non-stock, stock |
| 66–67   | `0x02`           | Kickoff        | non-stock, stock |
| 68–69   | `0x03`           | Punt           | non-stock, stock |
| 70–71   | `0x04`           | Onside Kick    | non-stock, stock |
| 72–73   | `0x05`           | Fake FG Run    | non-stock, stock |
| 74–75   | `0x06`           | Fake FG Pass   | non-stock, stock |
| 76–77   | `0x07`           | Fake Punt Run  | non-stock, stock |
| 78–79   | `0x08`           | Fake Punt Pass | non-stock, stock |
| 80–81   | `0x09`           | Free Kick      | non-stock, stock |
| 82–83   | `0x0A`           | Squib Kick     | non-stock, stock |
| 84      | `0x0B`           | Run Clock      | stock            |
| 85      | `0x0C`           | Stop Clock     | stock            |

### 3.2 Defensive Game Plans (84 slots)

| Offsets | Count | Purpose                                         |
| :------ | ----: | :---------------------------------------------- |
| 0–63    |    64 | Normal slots 1-1–16-4 (special category `0x00`) |
| 64–83   |    20 | Special slots (special category `0x01`–`0x0A`)  |

There are no defensive clock plays, so offsets 84 and 85 are always `0x0000`. Categories `0x01`–`0x0A` get two slots each, non-stock then stock.

| Offsets | Special category | Category Name          | Version          |
| :------ | :--------------- | :--------------------- | :--------------- |
| 64–65   | `0x01`           | FG/PAT Defense         | non-stock, stock |
| 66–67   | `0x02`           | Kick Return            | non-stock, stock |
| 68–69   | `0x03`           | Punt Return            | non-stock, stock |
| 70–71   | `0x04`           | Onside Return          | non-stock, stock |
| 72–73   | `0x05`           | Fake FG Run Defense    | non-stock, stock |
| 74–75   | `0x06`           | Fake FG Pass Defense   | non-stock, stock |
| 76–77   | `0x07`           | Fake Punt Run Defense  | non-stock, stock |
| 78–79   | `0x08`           | Fake Punt Pass Defense | non-stock, stock |
| 80–81   | `0x09`           | Free Kick Return       | non-stock, stock |
| 82–83   | `0x0A`           | Squib Return           | non-stock, stock |

---

## 4. Block: J95 — Summary Counts

Starts at 8 + G95 size.

### 4.1 Header (8 bytes)

Starts at 8 + G95 size.

| Offset | Size | Type    | Name | Description            |
| -----: | ---: | :------ | :--- | :--------------------- |
| 0x0000 |    4 | char[4] | ID   | `"J95:"`               |
| 0x0004 |    4 | u32     | Size | Data size (always `7`) |

### 4.2 Data (7 bytes)

Starts at 16 + G95 size.

| Offset | Size | Type | Name          | Description                       |
| -----: | ---: | :--- | :------------ | :-------------------------------- |
|     +0 |    1 | u8   | Profile type  | `0` = defense, `1` = offense      |
|     +1 |    2 | u16  | Custom plays  | Count of custom (non-stock) plays |
|     +3 |    2 | u16  | Stock plays   | Count of stock plays              |
|     +5 |    2 | u16  | Special plays | Count of special plays            |

These counts must be recomputed from the G95 play records when writing.

---

## 5. Block: S98 — Stock Map Filename

Starts at 23 + G95 size.

### 5.1 Header (8 bytes)

Starts at 23 + G95 size.

| Offset | Size | Type    | Name | Description                                      |
| -----: | ---: | :------ | :--- | :----------------------------------------------- |
| 0x0000 |    4 | char[4] | ID   | `"S98:"`                                         |
| 0x0004 |    4 | u32     | Size | Data size in bytes (everything after this field) |

### 5.2 Data

Starts at 31 + G95 size.

ASCII `"STOCK98.MAP"` followed by a single NUL (`0x00`). Total data size: 12 bytes.

---

## 6. File Size Parity

The pad, when present, starts at 43 + G95 size.

Total file size: **even** for offense, **odd** for defense. FbPro98's file-open dialog filters by parity. A defense file is padded with a trailing `0x00` when needed.

---

## 7. Reader Validation

Reader raises `InvalidGamePlanError` for:

- Bad block ID, size, or offset
- Truncated play record
- Missing NUL on custom play filename
- `stock_flag ∉ {0, 1}`
- Play category bytes that no category table recognizes (see ply.md section 3)
- `profile_type ∉ {0, 1}`
- `audible` bytes ≠ `00 01 02 03`
- J95 counts don't match parsed records
- S98 data ≠ `"STOCK98.MAP\x00"`
- File-size parity wrong for profile type

---

## 8. Writer Contract

Emit play records in slot order 0–85, recompute J95 counts, pad parity per section 6. Round-trip identity required: `write_gameplan(read_gameplan(p), q)` produces bytes identical to `p`.
