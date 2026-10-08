# .ply - Front Page Sports Football Pro '98 Play File Format

- **Owner:** FBPro98 Play Library
- **Encoding:** Integers little-endian; block IDs ASCII.

---

## 1. File Layout

A `.ply` is a single P95 block: an 8-byte header (ID + size) followed by size bytes of data. Total file length = 8 + size. Any block ID other than `"P95:"` is invalid.

```
P95  play
  header  ID + size
  offsets  one per player slot (11)
  play category, special category, user category
  players 1-11  variable length
    pre-snap, play and end-of-play logic-box sequences
      commands
```

| Offset |   Size | Name             | Description                                                                 | Section |
| -----: | -----: | :--------------- | :-------------------------------------------------------------------------- | :------ |
| 0x0000 |      4 | ID               | `"P95:"`                                                                    |         |
| 0x0004 |      4 | Size             | Data size in bytes (everything after this field)                            |         |
| 0x0008 |     22 | Offsets          | 11 player record offsets (u16), relative to 0x0008                          | 2       |
| 0x001E |      1 | Play category    | Category code (bits 5–0) assigned by the game; bits 7–6 shared with 0x0020  | 3       |
| 0x001F |      1 | Special category | `0x00` = normal play, `0x01`–`0x0C` = special                               | 3.3     |
| 0x0020 |      1 | User category    | Category code (bits 5–0) chosen by the coach; bits 7–6 shared with 0x001E   | 3       |
| 0x0021 | varies | Players          | 11 variable-length player records                                           | 2       |

The first offset is `0x0019` in every sampled real file, so the player records start at 0x0021, directly after the category bytes.

---

## 2. Player Records

Each record starts at 0x0008 plus its offset; the first at 0x0021 in every sampled file.

Each of the 11 offsets points to a variable-length player record. Offset index → player slot (from `ply.hsl`):

| Index |  0 |  1 |  2 |  3 |  4 |  5 |  6 |   7 |   8 |   9 |  10 |
| :---- | -: | -: | -: | -: | -: | -: | -: | --: | --: | --: | --: |
| Slot  | QB |  C | LT | LG | RG | RT | TE | RWR | LWR | LHB | RHB |

### 2.1 Player Record (variable length, partially understood)

Leading structure (per HSL):

| Relative Offset |   Size | Type | Name     | Description             |
| --------------: | -----: | :--- | :------- | :---------------------- |
|           +0x00 |      1 | u8   | Rank     | Depth / rank            |
|           +0x01 |      1 | u8   | Type     | Player record type      |
|           +0x02 |      2 | u16  | Position | Position code           |
|           +0x04 | varies | ...  | Data     | Variable logic-box data |

Observed type values: `0x01` pre-snap, `0x02` after-snap, `0x04` kicking. Observed position codes: `0x20` QB, `0x12` C, `0x11` T, `0x10` G, `0x81` TE, `0x80` WR, `0x42` HB.

### 2.2 Logic Boxes (partial)

Each player contains pre-snap, middle-of-play, and end-of-play logic-box sequences:

| Relative Offset |   Size | Type | Name          | Description                   |
| --------------: | -----: | :--- | :------------ | :---------------------------- |
|           +0x00 |      2 | u16  | Logic number  | Logic-box sequence number     |
|           +0x02 |      2 | u16  | X             | X coordinate / field value    |
|           +0x04 |      2 | u16  | Y             | Y coordinate / field value    |
|           +0x06 |      2 | u16  | Command count | Number of commands            |
|           +0x08 | varies | ...  | Commands      | Variable-length command array |

### 2.3 Commands (partial)

| Relative Offset | Size | Type | Name | Description                |
| --------------: | ---: | :--- | :--- | :------------------------- |
|           +0x00 |    2 | u16  | Type | Command type               |
|           +0x02 |    2 | u16  | X    | Command data / field value |
|           +0x04 |    2 | u16  | Y    | Command data / field value |

Command type values are not yet reverse engineered.

---

## 3. Play Categories

Starts at 0x001E.

The three category bytes at 0x001E–0x0020 classify a play. The play category is the game's own classification of the play; the user category is the category the coach picks in the Save Play dialog. The two may hold different codes for one play (section 3.5).

| Offset | Size | Type | Name             | Bits 5–0                          | Bits 7–6                      |
| -----: | ---: | :--- | :--------------- | :-------------------------------- | :---------------------------- |
| 0x001E |    1 | u8   | Play category    | Category code (sections 3.1, 3.2) | Pair shared with 0x0020 (3.4) |
| 0x001F |    1 | u8   | Special category | Special code (section 3.3)        | Always `00`                   |
| 0x0020 |    1 | u8   | User category    | Category code (sections 3.1, 3.2) | Pair shared with 0x001E (3.4) |

**Bit layout** of the play category and user category bytes, most significant bit first:

| Bit   |       7 |       6 |        5 |        4 |         3 |         2 |        1 |    0 |
| :---- | ------: | ------: | -------: | -------: | --------: | --------: | -------: | ---: |
| Field | unknown | unknown | distance | distance | direction | direction | run/pass | side |

| Bits | Mask | Field     | Values                                                 |
| :--- | :--- | :-------- | :----------------------------------------------------- |
| 7–6  | 0xC0 | unknown   | Per-file pair, identical in both bytes; section 3.4    |
| 5–4  | 0x30 | distance  | `00` Short, `01` Medium, `10` Long, `11` Goal Line     |
| 3–2  | 0x0C | direction | `00` Right, `01` Left, `10` Middle, `11` Razzle Dazzle |
| 1    | 0x02 | run/pass  | `0` Run, `1` Pass                                      |
| 0    | 0x01 | side      | `0` Defense, `1` Offense                               |

Bits 5–0 are the category code: mask with 0x3F before looking a byte up in section 3.1 or 3.2. Bit 0 is the side of ball in both bytes: odd = offense / kicking side, even = defense / receiving side, special plays included.

### 3.1 Offensive Categories (bit 0 = 1)

| Code (bits 5–0) | Game Category      |
| :-------------- | :----------------- |
| `0x01`          | Run Right          |
| `0x03`          | Pass Short Right   |
| `0x05`          | Run Left           |
| `0x07`          | Pass Short Left    |
| `0x09`          | Run Middle         |
| `0x0B`          | Pass Short Middle  |
| `0x0D`          | Razzle Dazzle Run  |
| `0x0F`          | Razzle Dazzle Pass |
| `0x13`          | Pass Medium Right  |
| `0x17`          | Pass Medium Left   |
| `0x1B`          | Pass Medium Middle |
| `0x23`          | Pass Long Right    |
| `0x27`          | Pass Long Left     |
| `0x2B`          | Pass Long Middle   |
| `0x31`          | Goal Line Run      |
| `0x33`          | Goal Line Pass     |
| `0xFF`          | User Specific      |

Not seen in the PNFL pool (2,579 offensive files): `0x0D` in either byte, `0x27` and `0x2B` as the user category, and `0xFF`.

### 3.2 Defensive Categories (bit 0 = 0)

| Code (bits 5–0) | Game Category      |
| :-------------- | :----------------- |
| `0x00`          | Run Right          |
| `0x02`          | Pass Short         |
| `0x04`          | Run Left           |
| `0x08`          | Run Middle         |
| `0x0C`          | Razzle Dazzle Run  |
| `0x0E`          | Razzle Dazzle Pass |
| `0x12`          | Pass Medium        |
| `0x22`          | Pass Long          |
| `0x30`          | Goal Line Run      |
| `0x32`          | Goal Line Pass     |
| `0xFE`          | User Specific      |

Not seen in the PNFL pool (2,267 defensive files): `0x0C`, `0x30` and `0x32` as the play category, and `0xFE`.

`0xFF` / `0xFE` (User Specific) is a play saved as Custom + Special; it is a full-byte value, not a bits 5–0 code.

### 3.3 Special Categories

Special category: `0x00` = normal play; otherwise:

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
| `0x0B` | Run Clock         | —                      |
| `0x0C` | Stop Clock        | —                      |

Both sides of the same special category share the same value. Defense has no clock plays.

In a special play the play category and user category are both `0x01` (offense) or `0x00` (defense), with bits 7–6 = `00`. `0x0B` and `0x0C` exist only as offensive stock records in `.pln` game plans ([pln.md section 2.3](../../fbpro98_gameplan/specs/pln.md#23-play-record-variable-size)); no `.ply` in the PNFL pool carries them (309 special files, all `0x01`–`0x0A`).

### 3.4 Bits 7–6

Bits 7–6 hold the same pair in the play category and user category bytes in every file checked: 4,846 offensive and defensive plays, no exceptions. Game plans copy the pair unchanged (pln.md section 2.3). The meaning is unknown; the pair does not follow the play's folder, file size or player records.

| Bits 7–6 | Offensive files | Defensive files | Special files |
| :------- | --------------: | --------------: | ------------: |
| `00`     |             218 |             152 |           309 |
| `01`     |               5 |               0 |             0 |
| `10`     |           2,282 |           2,115 |             0 |
| `11`     |              74 |               0 |             0 |

Counts are from the PNFL play pool on 2026-10-07: 5,155 files, 2,579 offensive, 2,267 defensive, 309 special.

### 3.5 Sample Files

Plays saved under one user category carry different play category codes and different bits 7–6. The four offensive plays are from `Offense\PML`, all saved as Pass Medium Left (`0x17`); the two defensive plays are from `Defense\R&SDefs\PassDazzle`, both saved as Razzle Dazzle Pass (`0x0E`).

| Play     | Side    | 0x1E   | 0x1F   | 0x20   | Bits 7–6 | Game category (0x1E & 0x3F) | User category (0x20 & 0x3F) |
| :------- | :------ | :----- | :----- | :----- | :------- | :-------------------------- | :-------------------------- |
| AT4A3QZX | Offense | `0x17` | `0x00` | `0x17` | `00`     | `0x17` Pass Medium Left     | `0x17` Pass Medium Left     |
| AF4AoutX | Offense | `0x93` | `0x00` | `0x97` | `10`     | `0x13` Pass Medium Right    | `0x17` Pass Medium Left     |
| NE4X18   | Offense | `0x67` | `0x00` | `0x57` | `01`     | `0x27` Pass Long Left       | `0x17` Pass Medium Left     |
| SF7YflyX | Offense | `0xD7` | `0x00` | `0xD7` | `11`     | `0x17` Pass Medium Left     | `0x17` Pass Medium Left     |
| JJ22pd2B | Defense | `0x02` | `0x00` | `0x0E` | `00`     | `0x02` Pass Short           | `0x0E` Razzle Dazzle Pass   |
| JJ22pd2d | Defense | `0x92` | `0x00` | `0x8E` | `10`     | `0x12` Pass Medium          | `0x0E` Razzle Dazzle Pass   |

Byte arrays, first 40 bytes of each file, split at the structure boundaries of section 1:

| Offset | Field      | AT4A3QZX                                                            | AF4AoutX                                                            |
| -----: | :--------- | :------------------------------------------------------------------ | :------------------------------------------------------------------ |
| 0x0000 | ID, size   | `50 39 35 3A 87 01 00 00`                                           | `50 39 35 3A C9 01 00 00`                                           |
| 0x0008 | offsets    | `19 00 49 00 61 00 79 00 95 00 B1 00 CD 00 F5 00 23 01 3B 01 63 01` | `19 00 47 00 63 00 87 00 AB 00 CF 00 F3 00 1B 01 49 01 77 01 A1 01` |
| 0x001E | categories | `17 00 17`                                                          | `93 00 97`                                                          |
| 0x0021 | player 1   | `01 02 20 00 01 00 00`                                              | `01 02 20 00 01 00 0A`                                              |

| Offset | Field      | NE4X18                                                              | SF7YflyX                                                            |
| -----: | :--------- | :------------------------------------------------------------------ | :------------------------------------------------------------------ |
| 0x0000 | ID, size   | `50 39 35 3A CB 01 00 00`                                           | `50 39 35 3A EF 01 00 00`                                           |
| 0x0008 | offsets    | `19 00 55 00 6D 00 85 00 A1 00 BD 00 D5 00 0D 01 3F 01 63 01 A3 01` | `19 00 5F 00 77 00 93 00 AF 00 CB 00 E7 00 21 01 55 01 87 01 A3 01` |
| 0x001E | categories | `67 00 57`                                                          | `D7 00 D7`                                                          |
| 0x0021 | player 1   | `01 02 20 00 01 00 00`                                              | `01 02 20 00 01 00 F5`                                              |

| Offset | Field      | JJ22pd2B                                                            | JJ22pd2d                                                            |
| -----: | :--------- | :------------------------------------------------------------------ | :------------------------------------------------------------------ |
| 0x0000 | ID, size   | `50 39 35 3A B9 01 00 00`                                           | `50 39 35 3A 3B 02 00 00`                                           |
| 0x0008 | offsets    | `19 00 55 00 73 00 97 00 BB 00 F7 00 1D 01 43 01 5B 01 77 01 9D 01` | `19 00 55 00 7D 00 A5 00 DF 00 1B 01 41 01 67 01 A1 01 DB 01 01 02` |
| 0x001E | categories | `02 00 0E`                                                          | `92 00 8E`                                                          |
| 0x0021 | player 1   | `02 00 02 01 01 00 23`                                              | `02 00 02 01 01 00 23`                                              |

---

## 4. Open Questions

- Full player-record layout
- Boundaries between pre-snap / middle-of-play / end-of-play logic sequences
- Command type values
- Whether `.ply` carries a stock/custom play flag
