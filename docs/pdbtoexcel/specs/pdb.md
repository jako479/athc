# WinLogStats `.pdb` File Format (Little-Endian)

- **Status:** Draft (reverse-engineered)
- **Owner:** PDB-to-Excel Library
- **Encoding:** Integers little-endian; strings ASCII (NUL-padded fixed buffers).

---

## 1. Container Overview

A `.pdb` is a flat stream of records. Each record is a 1-byte tag followed by a fixed-size body. No file header, no overall length field; EOF terminates the stream.

| Tag    | Record Type | Body Size  |
| -----: | :---------- | ---------: |
| `0x00` | PLAY_DATA   | 256 bytes  |
| `0x01` | TENDENCY    | 192 bytes  |

Any other tag byte is invalid.

PLAY and TENDENCY records may appear in any order. Duplicate `(team, play)` keys within PLAY records are summed by the reader.

---

## 2. Record: PLAY_DATA (256 bytes)

| Offset | Type      | Name                | Description                                              |
| -----: | :-------- | :------------------ | :------------------------------------------------------- |
| 0x0000 | u32       | play_type           | `0` Run, `1` Pass, `2` Special, `3` Defense, `5` Onside  |
| 0x0004 | char[64]  | team_name           | NUL-padded                                               |
| 0x0044 | char[128] | play_name           | NUL-padded                                               |
| 0x00C4 | i32       | total_yards         | Offense yards gained (signed; negative on loss)          |
| 0x00C8 | u32       | play_count          | Plays this record covers (see notes)                     |
| 0x00CC | u32       | completions         | Offense pass completions                                 |
| 0x00D0 | u32       | sacks               | Offense sacks taken / defense sacks recorded             |
| 0x00D4 | u32       | fumbles             | Fumbles                                                  |
| 0x00D8 | u32       | interceptions       | Interceptions                                            |
| 0x00DC | u32       | touchdowns_offense  | TDs scored by the offense                                |
| 0x00E0 | u32       | touchdowns_defense  | TDs scored by the defense                                |
| 0x00E4 | i32       | unknown1            | Always observed `0`                                      |
| 0x00E8 | i32       | unknown2            | Always observed `0`                                      |
| 0x00EC | u32       | points_scored       | Offense or defense points; ignored by readers            |
| 0x00F0 | u32       | run_plays_against   | Defense: rush plays faced                                |
| 0x00F4 | u32       | pass_plays_against  | Defense: pass plays faced (includes sacks)               |
| 0x00F8 | i32       | rush_yards_allowed  | Defense: rush yards given up                             |
| 0x00FC | i32       | pass_yards_allowed  | Defense: pass yards given up                             |

A record is valid when `play_type ∈ {0, 1, 2, 3, 5}` and both `team_name` and `play_name` are non-empty.

Records with `play_name == "RUNCLOCK"` or `play_name == "STOPCLOK"` are filtered by the reader (they are clock-management markers, not real plays).

---

## 3. Record: TENDENCY_DATA (192 bytes)

Run/pass call counts split by down (1st–4th) and yards-to-go bucket (`0-1`, `2-5`, `6-10`, `>10`).

| Offset | Type      | Name                  |
| -----: | :-------- | :-------------------- |
| 0x0000 | char[64]  | team_name             |
| 0x0040 | SITUATION | run_zero_to_one       |
| 0x0050 | SITUATION | pass_zero_to_one      |
| 0x0060 | SITUATION | run_two_to_five       |
| 0x0070 | SITUATION | pass_two_to_five      |
| 0x0080 | SITUATION | run_six_to_ten        |
| 0x0090 | SITUATION | pass_six_to_ten       |
| 0x00A0 | SITUATION | run_ten_plus          |
| 0x00B0 | SITUATION | pass_ten_plus         |

### 3.1 SITUATION (16 bytes)

| Offset | Type | Name        |
| -----: | :--- | :---------- |
|   0x00 | u32  | first_down  |
|   0x04 | u32  | second_down |
|   0x08 | u32  | third_down  |
|   0x0C | u32  | fourth_down |

A TENDENCY record is valid when `team_name` is non-empty.

---

## 4. Notes

- **`play_count` is inaccurate for defensive plays.** For defense it exceeds `run_plays_against + pass_plays_against`, appearing to also count snaps the defensive play was on the field for during special-teams plays. Treat `run_plays_against + pass_plays_against` as the authoritative defensive snap count.
- **QB scrambles are indistinguishable from incomplete passes.** A scramble appears in the PDB as a pass play with `0` yards and no completion — identical to a thrown incompletion.
- **Sacks on timed pass plays are logged as runs.** When a sack occurs on a "timed" pass play, the engine attributes the play (and its lost yards) to the run bucket rather than the pass bucket. The reader's `convert_invalid_play_data` rebalances these by detecting offensive plays whose recorded `play_type` disagrees with the play pool, and moves stats back to the correct side.

---

## 5. Reader Contract

- API: `PDB(filename)` parses the file synchronously.
- Exposes `plays` (dict keyed by `PLAY_TYPE` → dict keyed by `(team, play)` → `PLAY_DATA`) and `tendencies` (list of `TENDENCY_DATA`, sorted by team).
- Duplicate `(team, play)` records within a single `PLAY_TYPE` are summed via `PLAY_DATA.__iadd__`.
- Names listed in `RENAMED_PLAYS` are rewritten on load (e.g. `WR47PT01` → `WR27PT01`).
- Raises `InvalidPDBError` on a bad record-type byte.
- `convert_invalid_play_data(play_pool)` reclassifies misattributed run/pass records (see section 4).
