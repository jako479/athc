# WinLogStats `.pdb` File Format (Little-Endian)

- **Owner:** PDB-to-Excel Library
- **Encoding:** Integers little-endian; strings ASCII (NUL-padded fixed buffers).

---

## 1. Container Overview

A `.pdb` is a flat stream of records. Each record is a 1-byte tag followed by a fixed-size body. No file header, no overall length field; EOF terminates the stream.

| Tag    | Record Type | Body Size |
| -----: | :---------- | --------: |
| `0x00` | Play        | 256 bytes |
| `0x01` | Tendency    | 192 bytes |

Any other tag byte is invalid.

Play and tendency records may appear in any order, and the same team + play name key may appear in more than one play record.

---

## 2. Record: Play (256 bytes)

| Offset | Type      | Name                | Description                                             |
| -----: | :-------- | :------------------ | :------------------------------------------------------ |
| 0x0000 | u32       | Play type           | `0` Run, `1` Pass, `2` Special, `3` Defense, `5` Onside |
| 0x0004 | char[64]  | Team name           | NUL-padded                                              |
| 0x0044 | char[128] | Play name           | NUL-padded                                              |
| 0x00C4 | i32       | Total yards         | Offense yards gained (signed; negative on loss)         |
| 0x00C8 | u32       | Play count          | Plays this record covers (see notes)                    |
| 0x00CC | u32       | Completions         | Offense pass completions                                |
| 0x00D0 | u32       | Sacks               | Offense sacks taken / defense sacks recorded            |
| 0x00D4 | u32       | Fumbles             | Fumbles                                                 |
| 0x00D8 | u32       | Interceptions       | Interceptions                                           |
| 0x00DC | u32       | Touchdowns, offense | TDs scored by the offense                               |
| 0x00E0 | u32       | Touchdowns, defense | TDs scored by the defense                               |
| 0x00E4 | i32       | Unknown 1           | Always observed `0`                                     |
| 0x00E8 | i32       | Unknown 2           | Always observed `0`                                     |
| 0x00EC | u32       | Points scored       | Offense or defense points                               |
| 0x00F0 | u32       | Run plays against   | Defense: rush plays faced                               |
| 0x00F4 | u32       | Pass plays against  | Defense: pass plays faced (includes sacks)              |
| 0x00F8 | i32       | Rush yards allowed  | Defense: rush yards given up                            |
| 0x00FC | i32       | Pass yards allowed  | Defense: pass yards given up                            |

A record is valid when the play type is `0`, `1`, `2`, `3` or `5` and both the team name and the play name are non-empty.

Records whose play name is `"RUNCLOCK"` or `"STOPCLOK"` are clock-management markers, not real plays.

---

## 3. Record: Tendency (192 bytes)

Run/pass call counts split by down (1st–4th) and yards-to-go bucket (0-1, 2-5, 6-10, >10).

| Offset | Type            | Name             |
| -----: | :-------------- | :--------------- |
| 0x0000 | char[64]        | Team name        |
| 0x0040 | situation (3.1) | Run, 0-1 yards   |
| 0x0050 | situation (3.1) | Pass, 0-1 yards  |
| 0x0060 | situation (3.1) | Run, 2-5 yards   |
| 0x0070 | situation (3.1) | Pass, 2-5 yards  |
| 0x0080 | situation (3.1) | Run, 6-10 yards  |
| 0x0090 | situation (3.1) | Pass, 6-10 yards |
| 0x00A0 | situation (3.1) | Run, >10 yards   |
| 0x00B0 | situation (3.1) | Pass, >10 yards  |

### 3.1 Situation (16 bytes)

| Offset | Type | Name        |
| -----: | :--- | :---------- |
|   0x00 | u32  | First down  |
|   0x04 | u32  | Second down |
|   0x08 | u32  | Third down  |
|   0x0C | u32  | Fourth down |

A tendency record is valid when the team name is non-empty.

---

## 4. Notes

- **Play count is inaccurate for defensive plays.** For defense it exceeds run plays against + pass plays against, appearing to also count snaps the defensive play was on the field for during special-teams plays. Treat run plays against + pass plays against as the authoritative defensive snap count.
- **QB scrambles are indistinguishable from incomplete passes.** A scramble appears in the PDB as a pass play with `0` yards and no completion — identical to a thrown incompletion.
- **Sacks on timed pass plays are logged as runs.** When a sack occurs on a "timed" pass play, the engine attributes the play (and its lost yards) to the run bucket rather than the pass bucket.
