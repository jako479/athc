# .ply - Front Page Sports Football Pro '98 Play File Format

- **Owner:** FBPro98 Play Library
- **Encoding:** Integers little-endian; coordinates signed; block IDs ASCII. Not masked.

A `.ply` holds one play: its categories and, for each of the 11 players, a position and the logic the coach set in the game's play editor. This spec covers the layout and the parts of the logic athc reads (section 5).

---

## 1. File Layout

A `.ply` is a single P95 block: an 8-byte header (ID + size) followed by size bytes of data. Total file length = 8 + size.

```
P95  play
  header      ID + size
  offsets     one per player slot (11)
  categories  play, special, user
  player 1-11
    rank, role, position
    pre-snap    logic boxes
    after snap  logic boxes
      logic box  x, y, commands
```

| Offset |   Size | Name             | Description                                                                | Section |
| -----: | -----: | :--------------- | :------------------------------------------------------------------------- | :------ |
| 0x0000 |      4 | ID               | `"P95:"`                                                                   |         |
| 0x0004 |      4 | Size             | Data size in bytes (everything after this field)                           |         |
| 0x0008 |     22 | Offsets          | 11 player record offsets (u16), relative to 0x0008                         | 2       |
| 0x001E |      1 | Play category    | Category code (bits 5–0) assigned by the game; bits 7–6 shared with 0x0020 | 3       |
| 0x001F |      1 | Special category | `0x00` = normal play, `0x01`–`0x0C` = special                              | 3.3     |
| 0x0020 |      1 | User category    | Category code (bits 5–0) chosen by the coach; bits 7–6 shared with 0x001E  | 3       |
| 0x0021 | varies | Players          | 11 variable-length player records                                          | 2       |

The first offset is `0x0019` in every sampled file, so the player records start at 0x0021, directly after the category bytes.

---

## 2. Player Records

Record k starts at 0x0008 + offset k and ends where record k + 1 starts; the last ends at the end of the file. The records are back to back, in slot order.

Slot names:

| Slot |   0 |   1 |   2 |   3 |   4 |   5 |   6 |   7 |   8 |   9 |  10 |
| :--- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| Name |  QB |   C |  LT |  LG |  RG |  RT |  TE | RWR | LWR | LHB | RHB |

The names describe one default offensive formation. A slot can hold any position (section 4.1) on either side of the ball: in `AT4AcrsB` the LT slot lines up on the right.

### 2.1 Player Record (variable length)

Starts at 0x0008 + its offset.

| Offset |   Size | Type     | Name       | Description                                              | Section |
| -----: | -----: | :------- | :--------- | :------------------------------------------------------- | :------ |
|   0x00 |      1 | u8       | Rank       | Depth chart number at the position: `1` = QB1, `3` = HB3 |         |
|   0x01 |      1 | u8       | Role       | Bit flags                                                | 4.2     |
|   0x02 |      2 | u16      | Position   | Position code                                            | 4.1     |
|   0x04 | varies | box list | Pre-snap   | Logic boxes before the snap                              | 2.2     |
| varies | varies | box list | After snap | Logic boxes from the snap on                             | 2.2     |

The record holds nothing after the after-snap list.

### 2.2 Box List (variable length)

| Offset |   Size | Type   | Name  | Description           | Section |
| -----: | -----: | :----- | :---- | :-------------------- | :------ |
|   0x00 |      2 | u16    | Count | Number of logic boxes |         |
|   0x02 | varies | box[n] | Boxes | Logic boxes, in order | 2.3     |

- The pre-snap list starts with the player's starting spot.
- The after-snap list holds 1 or more boxes. Its first box is the player's spot at the snap.
- Each box's spot is where the player stands when its commands start.

### 2.3 Logic Box (variable length)

| Offset |   Size | Type       | Name     | Description                        | Section |
| -----: | -----: | :--------- | :------- | :--------------------------------- | :------ |
|   0x00 |      2 | i16        | X        | Sideways spot                      | 2.6     |
|   0x02 |      2 | i16        | Y        | Downfield spot                     | 2.6     |
|   0x04 |      2 | u16        | Count    | Number of commands; `0` is allowed |         |
|   0x06 | varies | command[n] | Commands | Commands, carried out in order     | 2.4     |

### 2.4 Command (variable length)

| Offset | Size | Type   | Name           | Description                       | Section |
| -----: | ---: | :----- | :------------- | :-------------------------------- | :------ |
|   0x00 |    1 | u8     | Code           | Command code                      | 2.5     |
|   0x01 |    1 | u8     | Argument count | n, `0`-`2`                        |         |
|   0x02 |   2n | i16[n] | Arguments      | Command arguments; a spot is x, y |         |

Size = 2 + 2 × n. Read n from every command: one code can take a different count in different commands.

### 2.5 Command Codes

Only the codes athc reads are listed. Skip any other command by its argument count (section 2.4).

| Code | Name            | Arguments | Description               |
| :--- | :-------------- | :-------- | :------------------------ |
| `02` | Move to         | x, y      | Move to the spot          |
| `06` | Timed pass      | tenths    | Throw after the delay     |
| `08` | Check receivers | count     | Check this many receivers |
| `0C` | Run             | direction | The ball carrier runs     |

### 2.6 Coordinates

(0, 0) is the ball on the line of scrimmage. The play is drawn with the ball in the middle of the field.

- x is sideways, positive to the offense's right. The sidelines are at -2400 and 2400.
- y is downfield, positive toward the defense. The offense lines up at negative y and the defense at positive y; both sides share the frame.
- 90 units = 1 yard: 4,800 units span the field's 53⅓-yard width.
- Example: the QB of `AF6AsprZ` lines up at (-11, -550), about 6 yards behind the ball, and moves to (281, -550), about 3 yards to the right, before checking receivers.

### 2.7 Example

`AT1BemTy`, the QB record at 0x0021:

```
0x0021  01                  rank       = 1 (QB1)
0x0022  02                  role       = 2 (takes the snap)
0x0023  20 00               position   = 0x0020 (QB)
0x0025  01 00               pre-snap   = 1 box
0x0027  F5 FF 2E FF 00 00   box          (-11, -210), 0 commands
0x002D  02 00               after snap = 2 boxes
0x002F  F5 FF 2E FF 01 00   box          (-11, -210), 1 command
0x0035  02 02 F5 FF 84 FE     Move to (-11, -380)
0x003B  F5 FF 84 FE 03 00   box          (-11, -380), 3 commands
0x0041  06 01 00 00           Timed pass, 0.0 s
0x0045  05 02 00 00 8E 03     code 05, 2 arguments: skipped
0x004B  07 01 01 00           code 07, 1 argument: skipped
```

The QB drops back from (-11, -210) to (-11, -380) and throws a timed pass. The tackles stand at x -322 and 311 at the snap, so the QB stays inside them. The next record (the C) starts at 0x004F.

---

## 3. Play Categories

Starts at 0x001E.

The three category bytes at 0x001E–0x0020 classify a play. The play category is the game's own classification of the play; the user category is the category the coach picks in the Save Play dialog. The two may hold different codes for one play (section 3.5).

| Offset | Size | Type | Name             | Description                                                                              |
| -----: | ---: | :--- | :--------------- | :--------------------------------------------------------------------------------------- |
| 0x001E |    1 | u8   | Play category    | Category code in bits 5–0 (sections 3.1, 3.2); bits 7–6 shared with 0x0020 (section 3.4) |
| 0x001F |    1 | u8   | Special category | Special code (section 3.3); bits 7–6 always `00`                                         |
| 0x0020 |    1 | u8   | User category    | Category code in bits 5–0 (sections 3.1, 3.2); bits 7–6 shared with 0x001E (section 3.4) |

Play category and user category bits:

| Bit(s) | Mask | Field     | Description                                            |
| -----: | ---: | :-------- | :----------------------------------------------------- |
|    7–6 | 0xC0 | —         | Not part of the category code (section 3.4)            |
|    5–4 | 0x30 | distance  | `00` Short, `01` Medium, `10` Long, `11` Goal Line     |
|    3–2 | 0x0C | direction | `00` Right, `01` Left, `10` Middle, `11` Razzle Dazzle |
|      1 | 0x02 | run/pass  | `0` Run, `1` Pass                                      |
|      0 | 0x01 | side      | `0` Defense, `1` Offense                               |

Bits 5–0 are the category code: mask with 0x3F before looking a byte up in section 3.1 or 3.2. Bit 0 is the side of ball in both bytes: odd = offense / kicking side, even = defense / receiving side, special plays included.

### 3.1 Offensive Categories (bit 0 = 1)

| Value  | Name               |
| :----- | :----------------- |
| `0x01` | Run Right          |
| `0x03` | Pass Short Right   |
| `0x05` | Run Left           |
| `0x07` | Pass Short Left    |
| `0x09` | Run Middle         |
| `0x0B` | Pass Short Middle  |
| `0x0D` | Razzle Dazzle Run  |
| `0x0F` | Razzle Dazzle Pass |
| `0x13` | Pass Medium Right  |
| `0x17` | Pass Medium Left   |
| `0x1B` | Pass Medium Middle |
| `0x23` | Pass Long Right    |
| `0x27` | Pass Long Left     |
| `0x2B` | Pass Long Middle   |
| `0x31` | Goal Line Run      |
| `0x33` | Goal Line Pass     |
| `0xFF` | User Specific      |

Not seen in the PNFL pool (2,579 offensive files): `0x0D` in either byte, `0x27` and `0x2B` as the user category, and `0xFF`.

### 3.2 Defensive Categories (bit 0 = 0)

| Value  | Name               |
| :----- | :----------------- |
| `0x00` | Run Right          |
| `0x02` | Pass Short         |
| `0x04` | Run Left           |
| `0x08` | Run Middle         |
| `0x0C` | Razzle Dazzle Run  |
| `0x0E` | Razzle Dazzle Pass |
| `0x12` | Pass Medium        |
| `0x22` | Pass Long          |
| `0x30` | Goal Line Run      |
| `0x32` | Goal Line Pass     |
| `0xFE` | User Specific      |

Not seen in the PNFL pool (2,267 defensive files): `0x0C`, `0x30` and `0x32` as the play category, and `0xFE`.

`0xFF` / `0xFE` (User Specific) is a play saved as Custom + Special; it is a full-byte value, not a bits 5–0 code.

### 3.3 Special Categories

Special category: `0x00` = normal play; otherwise:

| Value  | Offense Name   | Defense Name           |
| :----- | :------------- | :--------------------- |
| `0x01` | FG/PAT         | FG/PAT Defense         |
| `0x02` | Kickoff        | Kick Return            |
| `0x03` | Punt           | Punt Return            |
| `0x04` | Onside Kick    | Onside Return          |
| `0x05` | Fake FG Run    | Fake FG Run Defense    |
| `0x06` | Fake FG Pass   | Fake FG Pass Defense   |
| `0x07` | Fake Punt Run  | Fake Punt Run Defense  |
| `0x08` | Fake Punt Pass | Fake Punt Pass Defense |
| `0x09` | Free Kick      | Free Kick Return       |
| `0x0A` | Squib Kick     | Squib Return           |
| `0x0B` | Run Clock      | —                      |
| `0x0C` | Stop Clock     | —                      |

Both sides of the same special category share the same value. Defense has no clock plays.

In a special play the play category and user category are both `0x01` (offense) or `0x00` (defense), with bits 7–6 = `00`. `0x0B` and `0x0C` exist only as offensive stock records in `.pln` game plans ([pln.md section 2.3](../../fbpro98_gameplan/specs/pln.md#23-play-record-variable-size)); no `.ply` in the PNFL pool carries them (309 special files, all `0x01`–`0x0A`).

### 3.4 Bits 7–6

Bits 7–6 hold the same pair in the play category and user category bytes. They are not part of the category code. Game plans copy the pair unchanged (pln.md section 2.3).

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

## 4. Codes

### 4.1 Position

| Code     | Name | Group |
| :------- | :--- | :---- |
| `0x0010` | G    | OL    |
| `0x0011` | T    | OL    |
| `0x0012` | C    | OL    |
| `0x0020` | QB   | QB    |
| `0x0041` | FB   | RB    |
| `0x0042` | HB   | RB    |
| `0x0080` | WR   | WR/TE |
| `0x0081` | TE   | WR/TE |
| `0x0101` | DT   | DL    |
| `0x0102` | DE   | DL    |
| `0x0200` | LB   | LB    |
| `0x0400` | CB   | DB    |
| `0x0401` | S    | DB    |
| `0x0800` | K    | K     |
| `0x1000` | P    | P     |

Each code is one bit for the position group plus a number within the group. The nine groups are the depth chart's groups in the `.lge` roster ([lge.md](../../fbpro98_lge/specs/lge.md), section 6).

### 4.2 Role

| Bit(s) | Mask | Field         | Description                                                    |
| -----: | ---: | :------------ | :------------------------------------------------------------- |
|      0 | 0x01 | snapper       | Offense and kicking: snaps the ball. Defense: Preferred Player |
|      1 | 0x02 | snap receiver | The default snap receiver, slot 0                              |
|      2 | 0x04 | kicker        | Kicks                                                          |

Typical values: QB `2`, C `1`, kickoff kicker `4`, punter `6` (takes the snap and kicks). A defender marked Preferred Player has `1`: the play wants that depth chart player, not a backup.

---

## 5. Play Attributes

Play type and personnel are not stored as fields; they follow from the player records.

- Play type: the commands in the QB's logic boxes (position `0x0020`; section 2.5), such as a Timed pass, Check receivers or a Run, and the spots the QB moves to.
- Personnel: count the 11 position codes (section 4.1). Offense: RB (HB + FB), TE, WR. Defense: DL (DE + DT), LB, DB (CB + S).

How athc turns these into a timed pass, QB run, rollout or defensive front is a league rule, not part of the format: see the [playpool README](../../playpool/README.md#how-athc-reads-a-play).

---

## 6. Validity

A file is invalid when any of these holds:

- A block ID other than `"P95:"`
- A file length other than 8 + size
- A file too short for the offsets and category bytes
- A player record offset with no room for the record's first 4 bytes
- A player record too short for its box lists (section 2)
- Play category bytes that no category table recognizes (section 3)

---

## 7. Open Questions

None.
