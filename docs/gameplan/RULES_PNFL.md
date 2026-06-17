# PNFL Gameplan Rules

The PNFL rules `validate_gameplan` enforces. Sources: the league's [offensive](https://pnfl.biz/messageboard/viewtopic.php?f=16&t=14) and [defensive](https://pnfl.biz/messageboard/viewtopic.php?f=16&t=15) rules threads. The machine-readable form is [release/rules/PNFL.gameplan.toml](../../release/rules/PNFL.gameplan.toml); this doc is the human reference for it.

Sections are keyed by **short category label** — offense codes (`PSL`), defense words (`RunDazzle`). All per-section keys are optional (set at least one): `required` (default false), `min_count` (default 0), and `max_count`. Caps read playpool attributes: QB draws, rollouts, timed passes, and 2-DL (Run-and-Shoot front).

## Universal (both sides)

- **No duplicate plays** across the 64 normal slots.
- **Plays must resolve** in the bound play pool; an unknown play name is a violation.
- **Required special categories** must each have a custom or stock play: Field Goal/PAT, Kickoff, Punt, Onside Kick, Free Kick, Squib Kick. (The fake-kick categories are not required.)
- **Disallowed categories** must not appear: offense — Pass Long Left, Pass Long Middle, Razzle Dazzle Run, User Specific; defense — User Specific. A play in one is a violation.

## Offense

Pass categories cap **rollouts at 2** and **timed passes at 50%** (≤ 1/2 of the category's plays).

| Category | Required | Min plays | Extra |
|---|---|---|---|
| Run Middle | yes | 10 | ≤ 2 QB draws |
| Run Left | if used | 4 | ≤ 2 QB draws |
| Run Right | if used | 4 | ≤ 2 QB draws |
| Goal Line Run | if used | 3 | — |
| Pass Short Left / Middle / Right | yes | 5 | rollout + timed caps |
| Pass Medium Left / Middle / Right | yes | 5 | rollout + timed caps |
| Pass Long Right | yes | 4 | rollout + timed caps |
| Razzle Dazzle Pass | yes | 4 | rollout + timed caps |
| Goal Line Pass | if used | 3 | rollout + timed caps |

## Defense

| Category | Required | Min plays | 2-DL cap |
|---|---|---|---|
| Run Left / Middle / Right | yes | 6 | — |
| Pass Short | yes | 6 | ≤ 1/3 |
| Pass Medium | yes | 6 | ≤ 1/3 |
| Pass Long | yes | 6 | ≤ 1/2 |
| Goal Line Run | if used | 3 | — |
| Goal Line Pass | if used | 3 | — |
| Run Dazzle | if used | 4 | — |
| Pass Dazzle | if used | 4 | ≤ 1/2 |

## Not enforced

- **Per-play personnel** (e.g. "Pass Short: min two DLs and three LBs") — these constrain how a play is built, not how many a gameplan needs. gameplan assumes plays are valid for their category.
- **Situational eligibility** (e.g. "Pass Long callable on 1st/2nd and >10") — an in-game decision, not a construction rule.
