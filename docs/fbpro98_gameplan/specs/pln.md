# .pln - Front Page Sports Football Pro '98 Game Plan File Format

- **Status:** Complete
- **Owner:** FBPro98 Gameplan Library
- **Encoding:** Integers are little-endian; strings are ASCII unless noted.

---

## 1. File Layout

A `.pln` is three blocks in order: **G95** (offsets and play records), **J95** (summary counts), **S98** (stock map filename). Each block begins with a header: `ID (4 bytes)` + `size (4 bytes)`. `size` is the data length excluding the 8 bytes of `ID+size`.

| Offset          |     Size | Block | Region                            | Section |
| :-------------- | -------: | :---- | :-------------------------------- | :------ |
| 0x0000          |        8 | G95   | Header: `ID` + `size`             | 2.1     |
| 0x0008          |        4 | G95   | `audible`                         | 2.1     |
| 0x000C          |      172 | G95   | Play record offsets (`u16[86]`)   | 2.2     |
| 0x00B8          | variable | G95   | Play records, packed back-to-back | 2.3, 3  |
| `8 + G95.size`  |       15 | J95   | Header + 7 bytes of counts        | 4       |
| `23 + G95.size` |       20 | S98   | Header + `"STOCK98.MAP\0"`        | 5       |
| `43 + G95.size` |   0 or 1 | —     | Trailing parity pad, defense only | 6       |

---

## 2. Block: G95 — Index + Play Records

### 2.1 Header (12 bytes)

| Offset | Type    | Name    | Description                                      |
| -----: | :------ | :------ | :----------------------------------------------- |
| 0x0000 | char[4] | ID      | `"G95:"`                                         |
| 0x0004 | u32     | size    | Data size in bytes (everything after this field) |
| 0x0008 | u8[4]   | audible | Audible play indices; always `00 01 02 03`       |

Total G95 block length = `8 + size`. The reader rejects any `audible` ≠ `00 01 02 03`.

### 2.2 Offsets Table (172 bytes)

| Offset | Type    | Name    | Description                             |
| -----: | :------ | :------ | :-------------------------------------- |
| 0x000C | u16[86] | offsets | Play record offsets; `0x0000` = no play |

Always 86 entries, in both offensive and defensive game plans. Offsets are relative to byte `0x0C` (end of G95 header). The first play record begins at byte `0xB8` (12 header + 172 offsets). Which play each offset points to is in section 3.

### 2.3 Play Record (variable size)

| Offset | Type | Name             | Description                                                                   |
| -----: | :--- | :--------------- | :---------------------------------------------------------------------------- |
|   0x00 | u8   | stock_flag       | `0` = custom play, `1` = stock play                                           |
|   0x01 | u8   | play_category    | Play attribute; value semantics owned by the `.ply` format                    |
|   0x02 | u8   | special_category | Play attribute; `0x00` = normal play, `0x01`–`0x0C` = special (see section 3) |
|   0x03 | u8   | user_category    | Play attribute; value semantics owned by the `.ply` format                    |

In special plays, `play_category` and `user_category` are set per profile: `1` for offense, `0` for defense.

Trailing fields after the 4-byte header depend on `stock_flag`:

If `stock_flag = 0` (custom play):

| Offset | Type | Name     | Description                                                                 |
| -----: | :--- | :------- | :-------------------------------------------------------------------------- |
|   0x04 | cstr | filename | NUL-terminated ASCII play file path (`cstr` = ASCII bytes ending in `0x00`) |

If `stock_flag = 1` (stock play):

| Offset | Type    | Name       | Description                           |
| -----: | :------ | :--------- | :------------------------------------ |
|   0x04 | char[8] | play_name  | Fixed 8-byte ASCII name (NUL-padded)  |
|   0x0C | u32     | map_offset | Opaque pointer into unknown game file |
|   0x10 | u16     | map_size   | Opaque size into unknown game file    |

`map_offset` / `map_size` reference the external `STOCK98.MAP` file; the gameplan library carries them through unchanged on round-trip.

---

## 3. Play Slots

Coaches assign plays to slots. The Game Plan Editor shows the normal slots as a 16 × 4 grid, `1-1` through `16-4`, and the special slots on its Special Plays screen.

The offsets are fixed: offsets 0–63 always correspond to game plan slots `1-1` through `16-4`, row-major, and offsets 64–85 always correspond to the special slots, keyed by `special_category` (`0x01`–`0x0C`). Defensive game plans have no clock plays, so their offsets 84 and 85 are always `0x0000`.

An empty slot has its offset zeroed and contributes no play record. The play records are packed back-to-back regardless of any empty slots. Normal and non-stock special slots are optional; the 10 stock specials are always present.

### 3.1 Offensive Game Plans (86 slots)

| Offsets | Count | Purpose                                            |
| :------ | ----: | :------------------------------------------------- |
| 0–63    |    64 | Normal slots `1-1`–`16-4` (`special_category` = 0) |
| 64–85   |    22 | Special slots (`special_category` `0x01`–`0x0C`)   |

Categories `0x01`–`0x0A` get two slots each, non-stock then stock; categories `0x0B` and `0x0C` get one stock slot each.

| Offsets | special_category | Category Name  | Version          |
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

| Offsets | Count | Purpose                                            |
| :------ | ----: | :------------------------------------------------- |
| 0–63    |    64 | Normal slots `1-1`–`16-4` (`special_category` = 0) |
| 64–83   |    20 | Special slots (`special_category` `0x01`–`0x0A`)   |

There are no defensive clock plays, so offsets 84 and 85 are always `0x0000`. Categories `0x01`–`0x0A` get two slots each, non-stock then stock.

| Offsets | special_category | Category Name          | Version          |
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

### 4.1 Header (8 bytes)

| Offset | Type    | Name | Description            |
| -----: | :------ | :--- | :--------------------- |
| 0x0000 | char[4] | ID   | `"J95:"`               |
| 0x0004 | u32     | size | Data size (always `7`) |

### 4.2 Data (7 bytes)

| Offset | Type | Name              | Description                       |
| -----: | :--- | :---------------- | :-------------------------------- |
|     +0 | u8   | profile_type      | `0` = DEFENSE, `1` = OFFENSE      |
|     +1 | u16  | num_custom_plays  | Count of custom (non-stock) plays |
|     +3 | u16  | num_stock_plays   | Count of stock plays              |
|     +5 | u16  | num_special_plays | Count of special plays            |

These counts must be recomputed from the G95 play records when writing.

---

## 5. Block: S98 — Stock Map Filename

### 5.1 Header (8 bytes)

| Offset | Type    | Name | Description                                      |
| -----: | :------ | :--- | :----------------------------------------------- |
| 0x0000 | char[4] | ID   | `"S98:"`                                         |
| 0x0004 | u32     | size | Data size in bytes (everything after this field) |

### 5.2 Data

ASCII `"STOCK98.MAP"` followed by a single NUL (`0x00`). Total data size: 12 bytes.

---

## 6. File Size Parity

Total file size: **even** for offense, **odd** for defense. FbPro98's file-open dialog filters by parity. Writer pads defense files with a trailing `\x00` when needed.

---

## 7. Reader Validation

Reader raises `InvalidGamePlanError` for:

- Bad block ID, size, or offset
- Truncated play record
- Missing NUL on custom play filename
- `stock_flag ∉ {0, 1}`
- `profile_type ∉ {0, 1}`
- `audible` bytes ≠ `00 01 02 03`
- J95 counts don't match parsed records
- S98 data ≠ `"STOCK98.MAP\x00"`
- File-size parity wrong for profile type

---

## 8. Writer Contract

Emit play records in slot order 0–85, recompute J95 counts, pad parity per section 6. Round-trip identity required: `write_gameplan(read_gameplan(p), q)` produces bytes identical to `p`.
