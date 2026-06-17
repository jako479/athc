# .prf - Front Page Sports Football Pro '98 Coaching Profile File Format

- **Status:** Complete
- **Owner:** FBPro98 Profile Library
- **Encoding:** Integers little-endian; strings ASCII unless noted.

---

## 1. Container Overview

```
F95 (8 + 0x3C9D = 0x3CA5 bytes)
I95 (8 + 0x0A   = 0x0012 bytes)
trailer (1 byte for offense, 2 bytes for defense)
EOF
```

Each block: `ID (4 bytes)` + `size (4 bytes)` + data, where `size` excludes the 8-byte header.

Profiles can also be saved with embedded game plans (G95/J95/S98 trios after I95). This library rejects that variant — see section 4.

---

## 2. Block: F95 — Coaching Profile Data

### 2.1 Header (8 bytes)

| Offset | Type    | Name | Description                                       |
| -----: | :------ | :--- | :------------------------------------------------ |
| 0x0000 | char[4] | ID   | `"F95:"`                                          |
| 0x0004 | u32     | size | Data size in bytes (always `0x3C9D` = 15517 dec.) |

Data layout: substitutions → category weights → FG range → PAT category weights → `use_audibles`.

### 2.2 Substitution Settings (32 bytes, data offset `0x00`)

8 position groups × paired `out_percent` / `in_percent`. All 32 bytes physically present in both offense and defense profiles. Within a group: `0 ≤ out_percent ≤ in_percent ≤ 100`.

| Offset | Type | Name           | Description               | Editable in |
| -----: | :--- | :------------- | :------------------------ | :---------- |
|   0x00 | u16  | ol_out_percent | Offensive linemen `out` % | OFFENSE     |
|   0x02 | u16  | ol_in_percent  | Offensive linemen `in` %  | OFFENSE     |
|   0x04 | u16  | qb_out_percent | Quarterbacks `out` %      | OFFENSE     |
|   0x06 | u16  | qb_in_percent  | Quarterbacks `in` %       | OFFENSE     |
|   0x08 | u16  | rb_out_percent | Running backs `out` %     | OFFENSE     |
|   0x0A | u16  | rb_in_percent  | Running backs `in` %      | OFFENSE     |
|   0x0C | u16  | wr_out_percent | Receivers `out` %         | OFFENSE     |
|   0x0E | u16  | wr_in_percent  | Receivers `in` %          | OFFENSE     |
|   0x10 | u16  | dl_out_percent | Defensive linemen `out` % | DEFENSE     |
|   0x12 | u16  | dl_in_percent  | Defensive linemen `in` %  | DEFENSE     |
|   0x14 | u16  | lb_out_percent | Linebackers `out` %       | DEFENSE     |
|   0x16 | u16  | lb_in_percent  | Linebackers `in` %        | DEFENSE     |
|   0x18 | u16  | db_out_percent | Defensive backs `out` %   | DEFENSE     |
|   0x1A | u16  | db_in_percent  | Defensive backs `in` %    | DEFENSE     |
|   0x1C | u16  | k_out_percent  | Kickers `out` %           | OFFENSE     |
|   0x1E | u16  | k_in_percent   | Kickers `in` %            | OFFENSE     |

The UI exposes only the offense groups (OL, QB, RB, WR, K) when editing an offense profile and only the defense groups (DL, LB, DB) for defense. Non-editable groups hold the game's default `80/90` (`0x50 / 0x5A`). Readers expose all eight; writers preserve disk bytes for non-editable groups (initialize to `80/90` for new profiles).

### 2.3 Category Weights (15120 bytes, data offset `0x20`)

2520 records × 6 bytes. Indexed by the game's internal situation number; each record holds the play-calling rule for that situation.

#### 2.3.1 Category Weights Record (6 bytes)

| Offset | Type | Name           | Description                                           |
| -----: | :--- | :------------- | :---------------------------------------------------- |
|   0x00 | u8   | play_category1 | First play category — see section 2.3.2               |
|   0x01 | u8   | weight1        | Weight `0–10` plus Stop-Clock bit — see section 2.3.3 |
|   0x02 | u8   | play_category2 | Second play category                                  |
|   0x03 | u8   | weight2        | Weight `0–10`                                         |
|   0x04 | u8   | play_category3 | Third play category                                   |
|   0x05 | u8   | weight3        | Weight `0–10`                                         |

Three weighted play-category picks for the situation at this position. The AI selects one category (weighted by `weightN`) then chooses a play whose `play_category` matches — same enum as `PlayInPlan.play_category` in [pln.md section 2.3](../../fbpro98_gameplan/specs/pln.md#23-play-record-variable-size).

#### 2.3.2 Play Category Codes

Offense uses all 27 codes (`0x00`–`0x1A`). Defense uses 22 (`0x00`–`0x15`); `0x16`–`0x1A` are unused on defense. Defense doesn't distinguish pass direction, so `0x07`–`0x0F` collapse to three labels.

| Value | Offense Name         | Defense Name         |
| ----: | :------------------- | :------------------- |
|  0x00 | GOAL_LINE_RUN        | GOAL_LINE_RUN        |
|  0x01 | RAZZLE_DAZZLE_RUN    | RAZZLE_DAZZLE_RUN    |
|  0x02 | RUN_LEFT             | RUN_LEFT             |
|  0x03 | RUN_MIDDLE           | RUN_MIDDLE           |
|  0x04 | RUN_RIGHT            | RUN_RIGHT            |
|  0x05 | GOAL_LINE_PASS       | GOAL_LINE_PASS       |
|  0x06 | RAZZLE_DAZZLE_PASS   | RAZZLE_DAZZLE_PASS   |
|  0x07 | PASS_LONG_LEFT       | PASS_LONG            |
|  0x08 | PASS_LONG_MIDDLE     | PASS_LONG            |
|  0x09 | PASS_LONG_RIGHT      | PASS_LONG            |
|  0x0A | PASS_MEDIUM_LEFT     | PASS_MEDIUM          |
|  0x0B | PASS_MEDIUM_MIDDLE   | PASS_MEDIUM          |
|  0x0C | PASS_MEDIUM_RIGHT    | PASS_MEDIUM          |
|  0x0D | PASS_SHORT_LEFT      | PASS_SHORT           |
|  0x0E | PASS_SHORT_MIDDLE    | PASS_SHORT           |
|  0x0F | PASS_SHORT_RIGHT     | PASS_SHORT           |
|  0x10 | FIELD_GOAL_PAT       | FIELD_GOAL_PAT       |
|  0x11 | FAKE_FIELD_GOAL_RUN  | FAKE_FIELD_GOAL_RUN  |
|  0x12 | FAKE_FIELD_GOAL_PASS | FAKE_FIELD_GOAL_PASS |
|  0x13 | PUNT                 | PUNT                 |
|  0x14 | FAKE_PUNT_RUN        | FAKE_PUNT_RUN        |
|  0x15 | FAKE_PUNT_PASS       | FAKE_PUNT_PASS       |
|  0x16 | RUN_CLOCK            | _(unused)_           |
|  0x17 | RUN_RANDOM           | _(unused)_           |
|  0x18 | PASS_LONG_RANDOM     | _(unused)_           |
|  0x19 | PASS_MEDIUM_RANDOM   | _(unused)_           |
|  0x1A | PASS_SHORT_RANDOM    | _(unused)_           |

The reader does not enforce side-specific code restrictions — it accepts `0x00`–`0x1A` on both sides for permissive inspection.

#### 2.3.3 Weight Encoding

`weight1` packs weight + Stop-Clock bit:

| Bit(s) | Mask | Field      | Description                                  |
| -----: | ---: | :--------- | :------------------------------------------- |
|    6–0 | 0x7F | weight     | Selection weight, range `0–10` (`0x00–0x0A`) |
|      7 | 0x80 | stop_clock | Stop-Clock setting for this situation        |

`weight2` and `weight3` are plain weights with no Stop-Clock bit; range `0–10`.

#### 2.3.4 Situation Number Layout

The 2520-entry array is ordered by the cross-product of five game-state buckets, with one structural exclusion. Fastest-changing bucket is last:

| Bucket            | Cardinality | Values (ordered)                                                          |
| :---------------- | ----------: | :------------------------------------------------------------------------ |
| minutes_remaining |           5 | `>5`, `>2-5`, `>1-2`, `>:15-1`, `0-:15`                                   |
| down              |           4 | 1, 2, 3, 4                                                                |
| yards_to_go       |           4 | `0-1`, `2-5`, `6-10`, `>10`                                               |
| field_position    |           5 | `<DEF 5`, `DEF 5 - DEF 35`, `DEF 35 - OFF 35`, `OFF 35 - OFF 5`, `<OFF 5` |
| point_spread      |           7 | Ahead by 8+, 4-7, 1-3; Tied; Behind by 1-3, 4-7, 8+                       |

Dense product is `5 × 4 × 4 × 5 × 7 = 2800`. The 280 missing entries are the structurally-invalid combinations where `field_position == INSIDE_DEF_5 ∧ yards_to_go ∈ {6-10, >10}` (you can't have 6+ yards to a first down when the goal line is within 5 yards). Per `(minutes, down)` block, the layout is:

| Yards bucket | Cells per block | Field positions present     |
| :----------- | --------------: | :-------------------------- |
| `0-1`        |              35 | all 5                       |
| `2-5`        |              35 | all 5                       |
| `6-10`       |              28 | 4 (excludes `INSIDE_DEF_5`) |
| `>10`        |              28 | 4 (excludes `INSIDE_DEF_5`) |

Per `(minutes, down)` pair: 35 + 35 + 28 + 28 = 126 records. Total: 5 × 4 × 126 = 2520.

Records are laid out by minutes-remaining (slowest-changing), then down, then yards-to-go, then field-position, then point-spread (fastest-changing). Within each `(minutes, down)` pair the four yards-to-go groups appear in order; the two upper yards-to-go groups omit the `INSIDE_DEF_5` field-position row, which is what creates the 280-cell shortfall.

`stop_clock` is bit 7 of `weight1` on disk (see section 2.3.3); the parsed model carries it as a situation-level flag rather than a property of the weighted picks.

### 2.4 Field Goal Range (1 byte, data offset `0x3B30`)

| Offset | Type | Name             | Description                               |
| -----: | :--- | :--------------- | :---------------------------------------- |
| 0x3B30 | u8   | field_goal_range | Maximum FG attempt distance, yards `5–50` |

### 2.5 PAT Category Weights (360 bytes, data offset `0x3B31`)

60 records using the section 2.3.1 layout. Indexed by the game's internal PAT situation number.

PAT records do **not** carry a Stop-Clock bit — `weight1` is a plain weight in `[0, 10]`, identical in semantics to `weight2` and `weight3`. The reader rejects PAT records whose `weight1` falls outside `[0, 10]` (no bit-7 masking).

#### 2.5.1 PAT Situation Number Layout

PAT situations vary along only two game-state buckets (no down, yards-to-go, or field position):

| Bucket            | Cardinality | Values (ordered)                                                                    |
| :---------------- | ----------: | :---------------------------------------------------------------------------------- |
| minutes_remaining |           4 | `>5`, `>2-5`, `>1-2`, `0-1`                                                         |
| point_spread      |          15 | Ahead by 12+, 9-11, 8, 6-7, 5, 2-4, 1; Tied; Behind by 1, 2, 3-4, 5, 6-8, 9-12, 13+ |

Dense product: 4 × 15 = 60. No exclusions. PAT minutes collapses the regular-situation `>:15-1` and `0-:15` buckets into a single `0-1` bucket; PAT point-spread uses finer-grained buckets than regular situations (every 1-point difference up to ±8 is distinguished).

Records are laid out by minutes-remaining (slowest-changing), then point-spread (fastest-changing). A straight linear cross-product, with no exclusions.

### 2.6 Use Audibles (4 bytes, data offset `0x3C99`)

| Offset | Type | Name         | Description                            |
| -----: | :--- | :----------- | :------------------------------------- |
| 0x3C99 | u32  | use_audibles | `0` = audibles disabled, `1` = enabled |

End of F95 data at offset `0x3C9D` (file offset `0x3CA5`).

---

## 3. Block: I95 — Profile Metadata

### 3.1 Header (8 bytes)

| Offset | Type    | Name | Description                        |
| -----: | :------ | :--- | :--------------------------------- |
| 0x0000 | char[4] | ID   | `"I95:"`                           |
| 0x0004 | u32     | size | Data size in bytes (always `0x0A`) |

### 3.2 Data (10 bytes)

| Offset | Type | Name                 | Description                                                    |
| -----: | :--- | :------------------- | :------------------------------------------------------------- |
|     +0 | u8   | profile_type         | `0` = DEFENSE, `1` = OFFENSE                                   |
|     +1 | u16  | reserved             | Always `0x0000`                                                |
|     +3 | u8   | field_goal_range     | Yards `5–50`; mirrors F95's `field_goal_range`                 |
|     +4 | u16  | num_game_plan_blocks | Count of embedded game plans; supported profiles have `0` here |
|     +6 | u32  | use_audibles         | `0` or `1`; mirrors F95's `use_audibles`                       |

`field_goal_range` and `use_audibles` are stored redundantly in F95 and I95; readers reject mismatches. `num_game_plan_blocks ≠ 0` signals the embedded-game-plans variant (section 4).

---

## 4. Embedded Game Plans (Detected and Rejected)

Profiles saved with embedded game plans append one G95/J95/S98 trio per plan after I95. This library rejects that variant.

- **Detect:** `I95.num_game_plan_blocks ≠ 0`, or any non-trailer bytes after I95, or a `G95:` / `J95:` / `S98:` magic.
- **Reader:** raises `UnsupportedProfileError` (distinct from `InvalidProfileError`).
- **Writer:** never emits this variant.

---

## 5. Trailer

Every profile ends with **1 byte (offense)** or **2 bytes (defense)** so the total file size has the parity FbPro98's file-open dialog uses to filter by profile type:

| Profile type | Trailer length | Total file size |
| :----------- | -------------: | :-------------- |
| OFFENSE      |         1 byte | even            |
| DEFENSE      |        2 bytes | odd             |

(Bare blocks total `0x3CB7` = odd, so offense pads `+1`, defense pads `+2`.)

Trailer bytes must be `0x00` (NUL). Stock/factory profiles use `0x69` (a single byte for offense, `0x69 0x69` for defense), but those profiles are independently rejected at the F95 size check (section 4); the trailer code path never reaches them. The reader rejects `0x69` trailers; the writer always emits NULs.

---

## 6. Reader Validation

Reader raises `InvalidProfileError` for:

- Bad block ID or size
- F95 `size ≠ 0x3C9D`; I95 `size ≠ 0x0A`
- `profile_type ∉ {0, 1}`; I95 `reserved ≠ 0`
- `field_goal_range ∉ [5, 50]` in F95 or I95
- F95/I95 mismatch on `field_goal_range` or `use_audibles`
- `use_audibles ∉ {0, 1}` in either block
- Substitution pair violating `0 ≤ out ≤ in ≤ 100`
- Category-weights `play_category ∉ [0x00, 0x1A]` (no side-specific subset enforced)
- Category-weights `weight ∉ [0, 10]` (after masking the Stop-Clock bit on `weight1`)
- Trailer length ≠ 1 (offense) or 2 (defense)
- Trailer byte ≠ `0x00`
- File-size parity wrong for profile type

Profiles with embedded game plans (section 4) raise `UnsupportedProfileError` instead.

---

## 7. Writer Contract

- F95: fixed `0x3C9D` data size; recompute all sub-section bytes from the model.
- I95: fixed `0x0A` data size; mirror `field_goal_range` and `use_audibles` from F95; `reserved = 0`; `num_game_plan_blocks = 0`.
- Regular-situation `weight1`: pack the Stop-Clock flag into bit 7; clear bit 7 on `weight2` / `weight3`. PAT-situation weights carry no Stop-Clock bit.
- Trailer: 1 NUL (offense) or 2 NULs (defense).

Never emits embedded game plan blocks (section 4) or the stock layout (section 4 / F95 size variants).
