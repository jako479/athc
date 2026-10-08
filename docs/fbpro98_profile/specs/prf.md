# .prf - Front Page Sports Football Pro '98 Coaching Profile File Format

- **Owner:** FBPro98 Profile Library
- **Encoding:** Integers little-endian; strings ASCII unless noted.

---

## 1. Container Overview

```
F95  coaching profile data
  substitution settings
  category weights
  field goal range
  PAT category weights
  use audibles
I95  profile metadata
trailer
```

| Offset |   Size | Name    | Description                                          | Section |
| -----: | -----: | :------ | :--------------------------------------------------- | :------ |
| 0x0000 | 0x3CA5 | F95     | Coaching profile data: 8-byte header + 0x3C9D bytes  | 2       |
| 0x3CA5 |   0x12 | I95     | Profile metadata: 8-byte header + 10 bytes           | 3       |
| 0x3CB7 | 1 or 2 | Trailer | 1 byte for offense, 2 bytes for defense              | 5       |

Each block: ID (4 bytes) + size (4 bytes) + data, where size excludes the 8-byte header.

Profiles can also be saved with embedded game plans (G95/J95/S98 trios after I95); see section 4.

---

## 2. Block: F95 — Coaching Profile Data

Starts at 0x0000; the data offsets in 2.2-2.6 count from the first data byte at 0x0008.

### 2.1 Header (8 bytes)

| Offset | Size | Type    | Name | Description                                       |
| -----: | ---: | :------ | :--- | :------------------------------------------------ |
| 0x0000 |    4 | char[4] | ID   | `"F95:"`                                          |
| 0x0004 |    4 | u32     | Size | Data size in bytes (always `0x3C9D` = 15517 dec.) |

Data layout: substitutions → category weights → FG range → PAT category weights → use audibles.

### 2.2 Substitution Settings (32 bytes, data offset 0x00)

8 position groups × paired out percent / in percent. All 32 bytes physically present in both offense and defense profiles. Within a group: 0 ≤ out ≤ in ≤ 100.

| Offset | Size | Type | Name                    | Description        | Editable in |
| -----: | ---: | :--- | :---------------------- | :----------------- | :---------- |
|   0x00 |    2 | u16  | Offensive linemen out % | Fatigue threshold  | Offense     |
|   0x02 |    2 | u16  | Offensive linemen in %  | Recovery threshold | Offense     |
|   0x04 |    2 | u16  | Quarterbacks out %      | Fatigue threshold  | Offense     |
|   0x06 |    2 | u16  | Quarterbacks in %       | Recovery threshold | Offense     |
|   0x08 |    2 | u16  | Running backs out %     | Fatigue threshold  | Offense     |
|   0x0A |    2 | u16  | Running backs in %      | Recovery threshold | Offense     |
|   0x0C |    2 | u16  | Receivers out %         | Fatigue threshold  | Offense     |
|   0x0E |    2 | u16  | Receivers in %          | Recovery threshold | Offense     |
|   0x10 |    2 | u16  | Defensive linemen out % | Fatigue threshold  | Defense     |
|   0x12 |    2 | u16  | Defensive linemen in %  | Recovery threshold | Defense     |
|   0x14 |    2 | u16  | Linebackers out %       | Fatigue threshold  | Defense     |
|   0x16 |    2 | u16  | Linebackers in %        | Recovery threshold | Defense     |
|   0x18 |    2 | u16  | Defensive backs out %   | Fatigue threshold  | Defense     |
|   0x1A |    2 | u16  | Defensive backs in %    | Recovery threshold | Defense     |
|   0x1C |    2 | u16  | Kickers out %           | Fatigue threshold  | Offense     |
|   0x1E |    2 | u16  | Kickers in %            | Recovery threshold | Offense     |

The UI exposes only the offense groups (OL, QB, RB, WR, K) when editing an offense profile and only the defense groups (DL, LB, DB) for defense. Non-editable groups hold the game's default 80/90 (`0x50` / `0x5A`).

### 2.3 Category Weights (15120 bytes, data offset 0x20)

2520 records × 6 bytes. Indexed by the game's internal situation number; each record holds the play-calling rule for that situation.

#### 2.3.1 Category Weights Record (6 bytes)

| Offset | Size | Type | Name            | Description                                          |
| -----: | ---: | :--- | :-------------- | :--------------------------------------------------- |
|   0x00 |    1 | u8   | Play category 1 | First play category — see section 2.3.2              |
|   0x01 |    1 | u8   | Weight 1        | Weight `0`–`10` plus Stop Clock bit — see section 2.3.3 |
|   0x02 |    1 | u8   | Play category 2 | Second play category                                 |
|   0x03 |    1 | u8   | Weight 2        | Weight `0`–`10`                                      |
|   0x04 |    1 | u8   | Play category 3 | Third play category                                  |
|   0x05 |    1 | u8   | Weight 3        | Weight `0`–`10`                                      |

Three weighted play-category picks for the situation at this position. The AI selects one category (weighted by its weight) then chooses a play of that category from the game plan. The codes here are the profile's own table (section 2.3.2), not the category bytes of a play file or game plan ([ply.md section 3](../../fbpro98_play/specs/ply.md#3-play-categories)): one side uses both odd and even values.

#### 2.3.2 Play Category Codes

Offense uses all 27 codes (`0x00`–`0x1A`). Defense uses 22 (`0x00`–`0x15`); `0x16`–`0x1A` are unused on defense. Defense doesn't distinguish pass direction, so `0x07`–`0x0F` collapse to three labels.

| Value  | Offense Name         | Defense Name         |
| :----- | :------------------- | :------------------- |
| `0x00` | Goal Line Run        | Goal Line Run        |
| `0x01` | Razzle Dazzle Run    | Razzle Dazzle Run    |
| `0x02` | Run Left             | Run Left             |
| `0x03` | Run Middle           | Run Middle           |
| `0x04` | Run Right            | Run Right            |
| `0x05` | Goal Line Pass       | Goal Line Pass       |
| `0x06` | Razzle Dazzle Pass   | Razzle Dazzle Pass   |
| `0x07` | Pass Long Left       | Pass Long            |
| `0x08` | Pass Long Middle     | Pass Long            |
| `0x09` | Pass Long Right      | Pass Long            |
| `0x0A` | Pass Medium Left     | Pass Medium          |
| `0x0B` | Pass Medium Middle   | Pass Medium          |
| `0x0C` | Pass Medium Right    | Pass Medium          |
| `0x0D` | Pass Short Left      | Pass Short           |
| `0x0E` | Pass Short Middle    | Pass Short           |
| `0x0F` | Pass Short Right     | Pass Short           |
| `0x10` | Field Goal / PAT     | Field Goal / PAT     |
| `0x11` | Fake Field Goal Run  | Fake Field Goal Run  |
| `0x12` | Fake Field Goal Pass | Fake Field Goal Pass |
| `0x13` | Punt                 | Punt                 |
| `0x14` | Fake Punt Run        | Fake Punt Run        |
| `0x15` | Fake Punt Pass       | Fake Punt Pass       |
| `0x16` | Run Clock            | _(unused)_           |
| `0x17` | Run Random           | _(unused)_           |
| `0x18` | Pass Long Random     | _(unused)_           |
| `0x19` | Pass Medium Random   | _(unused)_           |
| `0x1A` | Pass Short Random    | _(unused)_           |

#### 2.3.3 Weight Encoding

Weight 1 packs the weight and the Stop Clock bit:

| Bit(s) | Mask | Field      | Description                                  |
| -----: | ---: | :--------- | :------------------------------------------- |
|    6–0 | 0x7F | weight     | Selection weight, range `0`–`10` (`0x00`–`0x0A`) |
|      7 | 0x80 | stop clock | Stop Clock setting for this situation        |

Weight 2 and weight 3 are plain weights with no Stop Clock bit; range `0`–`10`.

#### 2.3.4 Situation Number Layout

The 2520-entry array is ordered by the cross-product of five game-state buckets, with one structural exclusion. Fastest-changing bucket is last:

| Bucket            | Cardinality | Values (ordered)                                                      |
| :---------------- | ----------: | :-------------------------------------------------------------------- |
| Minutes remaining |           5 | >5, >2-5, >1-2, >:15-1, 0-:15                                         |
| Down              |           4 | 1, 2, 3, 4                                                            |
| Yards to go       |           4 | 0-1, 2-5, 6-10, >10                                                   |
| Field position    |           5 | <DEF 5, DEF 5 - DEF 35, DEF 35 - OFF 35, OFF 35 - OFF 5, <OFF 5       |
| Point spread      |           7 | Ahead by 8+, 4-7, 1-3; Tied; Behind by 1-3, 4-7, 8+                   |

Dense product is 5 × 4 × 4 × 5 × 7 = 2800. The 280 missing entries are the structurally-invalid combinations where the field position is <DEF 5 and yards to go is 6-10 or >10 (you can't have 6+ yards to a first down when the goal line is within 5 yards). Per (minutes, down) block, the layout is:

| Yards bucket | Cells per block | Field positions present |
| :----------- | --------------: | :---------------------- |
| 0-1          |              35 | all 5                   |
| 2-5          |              35 | all 5                   |
| 6-10         |              28 | 4 (excludes <DEF 5)     |
| >10          |              28 | 4 (excludes <DEF 5)     |

Per (minutes, down) pair: 35 + 35 + 28 + 28 = 126 records. Total: 5 × 4 × 126 = 2520.

Records are laid out by minutes remaining (slowest-changing), then down, then yards to go, then field position, then point spread (fastest-changing). Within each (minutes, down) pair the four yards-to-go groups appear in order; the two upper yards-to-go groups omit the <DEF 5 field-position row, which is what creates the 280-cell shortfall.

Stop Clock is bit 7 of weight 1 on disk (section 2.3.3).

### 2.4 Field Goal Range (1 byte, data offset 0x3B30)

| Offset | Size | Type | Name             | Description                                 |
| -----: | ---: | :--- | :--------------- | :------------------------------------------ |
| 0x3B30 |    1 | u8   | Field goal range | Maximum FG attempt distance, yards `5`–`50` |

### 2.5 PAT Category Weights (360 bytes, data offset 0x3B31)

60 records using the section 2.3.1 layout. Indexed by the game's internal PAT situation number.

PAT records do **not** carry a Stop Clock bit — weight 1 is a plain weight in `0`–`10`, identical in semantics to weight 2 and weight 3. A PAT record whose weight 1 falls outside `0`–`10` is invalid (no bit-7 masking).

#### 2.5.1 PAT Situation Number Layout

PAT situations vary along only two game-state buckets (no down, yards to go, or field position):

| Bucket            | Cardinality | Values (ordered)                                                                    |
| :---------------- | ----------: | :---------------------------------------------------------------------------------- |
| Minutes remaining |           4 | >5, >2-5, >1-2, 0-1                                                                 |
| Point spread      |          15 | Ahead by 12+, 9-11, 8, 6-7, 5, 2-4, 1; Tied; Behind by 1, 2, 3-4, 5, 6-8, 9-12, 13+ |

Dense product: 4 × 15 = 60. No exclusions. PAT minutes collapses the regular-situation >:15-1 and 0-:15 buckets into a single 0-1 bucket; PAT point spread uses finer-grained buckets than regular situations (every 1-point difference up to ±8 is distinguished).

Records are laid out by minutes remaining (slowest-changing), then point spread (fastest-changing). A straight linear cross-product, with no exclusions.

### 2.6 Use Audibles (4 bytes, data offset 0x3C99)

| Offset | Size | Type | Name         | Description                            |
| -----: | ---: | :--- | :----------- | :------------------------------------- |
| 0x3C99 |    4 | u32  | Use audibles | `0` = audibles disabled, `1` = enabled |

End of F95 data at offset 0x3C9D (file offset 0x3CA5).

---

## 3. Block: I95 — Profile Metadata

Starts at 0x3CA5; its data at 0x3CAD.

### 3.1 Header (8 bytes)

| Offset | Size | Type    | Name | Description                        |
| -----: | ---: | :------ | :--- | :--------------------------------- |
| 0x0000 |    4 | char[4] | ID   | `"I95:"`                           |
| 0x0004 |    4 | u32     | Size | Data size in bytes (always `0x0A`) |

### 3.2 Data (10 bytes)

| Offset | Size | Type | Name             | Description                                                    |
| -----: | ---: | :--- | :--------------- | :------------------------------------------------------------- |
|     +0 |    1 | u8   | Profile type     | `0` = defense, `1` = offense                                   |
|     +1 |    2 | u16  | Reserved         | Always `0x0000`                                                |
|     +3 |    1 | u8   | Field goal range | Yards `5`–`50`; mirrors the F95 field goal range               |
|     +4 |    2 | u16  | Game plan blocks | Count of embedded game plans; supported profiles have `0` here |
|     +6 |    4 | u32  | Use audibles     | `0` or `1`; mirrors the F95 use audibles                       |

Field goal range and use audibles are stored redundantly in F95 and I95; a mismatch is invalid. A game plan block count other than `0` signals the embedded-game-plans variant (section 4).

---

## 4. Embedded Game Plans

When present, the extra blocks start at 0x3CB7, where the trailer would be.

Profiles saved with embedded game plans append one G95/J95/S98 trio per plan after I95. The variant shows as an I95 game plan block count other than `0`, bytes other than the trailer after I95, or a `G95:` / `J95:` / `S98:` ID after I95.

---

## 5. Trailer

Starts at 0x3CB7.

Every profile ends with **1 byte (offense)** or **2 bytes (defense)** so the total file size has the parity FbPro98's file-open dialog uses to filter by profile type:

| Profile type | Trailer length | Total file size |
| :----------- | -------------: | :-------------- |
| Offense      |         1 byte | even            |
| Defense      |        2 bytes | odd             |

(Bare blocks total 0x3CB7 = odd, so offense pads +1, defense pads +2.)

Trailer bytes must be `0x00` (NUL). Stock/factory profiles use `0x69` (a single byte for offense, `0x69 0x69` for defense), but they are the older stock layout, whose F95 size is `0x3F69` or `0x4509` rather than `0x3C9D`.

---

## 6. Validity

A file is invalid when any of these holds:

- A bad block ID or size
- An F95 size other than `0x3C9D`; an I95 size other than `0x0A`
- A profile type other than `0` or `1`; an I95 reserved field other than `0`
- A field goal range outside `5`–`50` in F95 or I95
- F95 and I95 disagreeing on the field goal range or use audibles
- Use audibles other than `0` or `1` in either block
- A substitution pair violating `0 ≤ out ≤ in ≤ 100`
- A category-weights play category outside `0x00`–`0x1A` (no side-specific subset)
- A category-weights weight outside `0`–`10` (after masking the Stop Clock bit on weight 1)
- A trailer length other than 1 (offense) or 2 (defense)
- A trailer byte other than `0x00`
- File-size parity wrong for the profile type

A profile with embedded game plans (section 4) is a valid file in a different variant, not an invalid one.
