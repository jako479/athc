# .ply - Front Page Sports Football Pro '98 Play File Format

- **Status:** Draft (reverse-engineering of personnel actions incomplete)
- **Owner:** FBPro98 Play Library
- **Encoding:** Integers little-endian; block IDs ASCII.

---

## 1. Container Overview

A `.ply` contains a single `P95` block: `ID (4 bytes)` + `size (4 bytes)` + data, where `size` excludes the 8-byte header. Total file length = `8 + size`.

---

## 2. Block: P95 — Play Definition

### 2.1 Header (8 bytes)

| Offset | Type    | Name | Description                                      |
| -----: | :------ | :--- | :----------------------------------------------- |
| 0x0000 | char[4] | ID   | `"P95:"`                                         |
| 0x0004 | u32     | size | Data size in bytes (everything after this field) |

The parser rejects any block ID other than `"P95:"`.

### 2.2 Player Offsets Table (22 bytes, data offset `0x00`)

11 × `u16` little-endian, each pointing to a player record. Offset base is the end of the 8-byte header (file offset `0x08`). First entry is `0x0019` in every sampled real file.

Slot order (from `fbpro_ply.hsl`): QB, C, LT, LG, RG, RT, TE, RWR, LWR, LHB, RHB.

### 2.3 Metadata (3 bytes, file offset `0x1E`)

| Offset | Type | Name             | Description                              |
| -----: | :--- | :--------------- | :--------------------------------------- |
| 0x001E | u8   | play_category    | Category byte supplied by the game       |
| 0x001F | u8   | special_category | Special-teams category (0 = not special) |
| 0x0020 | u8   | user_category    | User category byte                       |

**Side of ball:** bit 0 of `play_category` (or `user_category`). Odd = offense / kicking side; even = defense / receiving side. The same odd/even rule applies for special teams.

**Special-teams category** (`special_category`): `0x00` = not special teams; otherwise:

| Value  | Offense (kicking) | Defense (receiving)    |
| ------ | ----------------- | ---------------------- |
| `0x01` | FG/PAT            | FG/PAT Defense         |
| `0x02` | Kickoff           | Kick Return            |
| `0x03` | Punt              | Punt Return            |
| `0x04` | Onside Kick       | Onside Return          |
| `0x05` | Fake FG Run       | Fake FG Run Defense    |
| `0x06` | Fake FG Pass      | Fake FG Pass Defense   |
| `0x07` | Fake Punt Run     | Fake Punt Run Defense  |
| `0x08` | Fake Punt Pass    | Fake Punt Pass Defense |
| `0x09` | Free Kick         | Free Kick Return       |
| `0x0A` | Squib Kick        | Squib Return           |

Both sides of the same special-teams category share the same `special_category` value.

**Game category encoding in `user_category`:** the game's play category is in bits 5–0; bits 7–6 vary across plays in the same category (purpose unknown). Bit 0 follows the same odd/even rule as `play_category`.

Offensive categories (bit 0 = 1):

| Base (bits 5-0) | Game Category      |
| --------------- | ------------------ |
| 0x01            | Run Right          |
| 0x03            | Pass Short Right   |
| 0x05            | Run Left           |
| 0x07            | Pass Short Left    |
| 0x09            | Run Middle         |
| 0x0B            | Pass Short Middle  |
| 0x0D            | Razzle Dazzle Run  |
| 0x0F            | Razzle Dazzle Pass |
| 0x13            | Pass Medium Right  |
| 0x17            | Pass Medium Left   |
| 0x1B            | Pass Medium Middle |
| 0x23            | Pass Long Right    |
| 0x27            | Pass Long Left     |
| 0x2B            | Pass Long Middle   |
| 0x31            | Goal Line Run      |
| 0x33            | Goal Line Pass     |
| 0xFF            | User Specific      |

Defensive categories (bit 0 = 0):

| Base (bits 5-0) | Game Category      |
| --------------- | ------------------ |
| 0x00            | Run Right          |
| 0x02            | Pass Short         |
| 0x04            | Run Left           |
| 0x08            | Run Middle         |
| 0x0C            | Razzle Dazzle Run  |
| 0x0E            | Razzle Dazzle Pass |
| 0x12            | Pass Medium        |
| 0x22            | Pass Long          |
| 0x30            | Goal Line Run      |
| 0x32            | Goal Line Pass     |
| 0xFE            | User Specific      |

`0xFF` / `0xFE` (User Specific) is a play saved as Custom + Special. Validated against 2092 offensive and 1879 defensive plays.

Bit-level encoding within the base:

| Bit | Values                                                 |
| --- | ------------------------------------------------------ |
| 0   | 0 = Defense, 1 = Offense                               |
| 1   | 0 = Run, 1 = Pass                                      |
| 2-3 | 00 = Right, 01 = Left, 10 = Middle, 11 = Razzle Dazzle |
| 4-5 | 00 = Short, 01 = Medium, 10 = Long, 11 = Goal Line     |
| 6   | 0/1 = UNKNOWN; 0 for all DEF and vast majority OFF     |
| 7   | 0/1 = UNKNOWN; 1 for vast majority OFF and DEF         |

### 2.4 Player Records (variable length, partially understood)

Each of the 11 offsets points to a variable-length player record. Leading structure (per HSL):

| Relative Offset | Type | Name     | Description             |
| --------------: | :--- | :------- | :---------------------- |
|         `+0x00` | u8   | rank     | Depth / rank            |
|         `+0x01` | u8   | type     | Player record type      |
|         `+0x02` | u16  | position | Position code           |
|         `+0x04` | ...  | data     | Variable logic-box data |

Observed `type` values: `0x01` pre-snap, `0x02` after-snap, `0x04` kicking. Observed `position` codes: `0x20` QB, `0x12` C, `0x11` T, `0x10` G, `0x81` TE, `0x80` WR, `0x42` HB.

### 2.5 Logic Boxes (partial)

Each player contains pre-snap, middle-of-play, and end-of-play logic-box sequences:

| Relative Offset | Type | Name         | Description                   |
| --------------: | :--- | :----------- | :---------------------------- |
|         `+0x00` | u16  | numLogic     | Logic-box sequence number     |
|         `+0x02` | u16  | x            | X coordinate / field value    |
|         `+0x04` | u16  | y            | Y coordinate / field value    |
|         `+0x06` | u16  | commandCount | Number of commands            |
|         `+0x08` | ...  | commands     | Variable-length command array |

### 2.6 Commands (partial)

| Relative Offset | Type | Name | Description                |
| --------------: | :--- | :--- | :------------------------- |
|         `+0x00` | u16  | type | Command type               |
|         `+0x02` | u16  | x    | Command data / field value |
|         `+0x04` | u16  | y    | Command data / field value |

Command type values are not yet reverse engineered.

---

## 3. Reader Contract

- API: `read_play(path)` → parsed `PlayFile`; `parse_play(buffer, path)` parses raw bytes.
- Validates `ID == "P95:"`, `len(file) == 8 + size`, file large enough for the offsets table + 3 metadata bytes + 11 player headers.
- Exposes: `file_path`, `stream_length`, `player_offsets`, `player_headers`, `play_category`, `special_category`, `user_category`.
- Raises `InvalidPlayFileError` for bad block ID, size mismatch, or truncated metadata / player headers.

---

## 4. Validation & Test Vectors

Fixtures cover offensive, defensive, special-teams plays, plus one zero-byte invalid file. Tests verify `len(file) == 8 + size`, exact offset tables and player-header tuples for all valid fixtures, the 3 metadata bytes at `0x1E..0x20`, resolved category names, and rejection of the zero-byte file.

---

## 5. Open Questions

- Full player-record layout
- Boundaries between pre-snap / middle-of-play / end-of-play logic sequences
- Command type values
- Whether `.ply` carries a stock/custom play flag
