# FbPro98 game behavior

How the game behaves, learned from league files and play. Source: PNFL 2049,
weeks 1-7, unless noted.

## Injuries

Each injured player has an injury level; 0 is healthy. The game heals every
injured player once a week, when the week's games start. A game never changes
an existing injury level; it only adds new injuries.

### Weekly healing

The amount is fixed per player and the same every week; it is not random.

| Roster slot              | EN 84-90 | EN 91 |
| :----------------------- | -------: | ----: |
| Active, Open or Inactive |      120 |   150 |
| IR/PS (shown as IF)      |      135 |   165 |

- IR/PS heals 15 points a week more than any other slot.
- Inactive heals the same as Active and Open; sitting a player out does not
  speed healing.
- Playing while injured does not slow healing further: players who played
  healed the full amount. The manual's "heals about half as fast" did not
  happen.

### Endurance

EN sets the weekly healing amount: 120 at EN 84-90, 150 at EN 91. Other EN
values not seen yet.

### Injury status

The injury screens show a letter and a number, such as Q-3.

The letter comes from the injury level alone:

| Letter | Injury level | Lowest seen | Highest seen |
| :----- | :----------- | ----------: | -----------: |
| OK     | 0            |           0 |            0 |
| P      | 1-150        |          10 |          150 |
| Q      | 151-300      |         164 |          297 |
| D      | 301-450      |         302 |          437 |
| O      | 451 and up   |         458 |         9360 |

The number is the weeks out the game displays. It is not stored; the game
calculates it from the injury level and EN:

Weeks displayed = injury level ÷ (1.5 × EN), drop the decimals, then add 1.

- Corum, EN 86: 525 ÷ 129 = 4.07 → 4, plus 1 = O-5.
- Fields, EN 88: 389 ÷ 132 = 2.95 → 2, plus 1 = D-3.

This fits all 50 statuses checked (PNFL 2047-2049). One player showed 20 where
the calculation gives 72.

### P-1 that stays injured

The displayed weeks assume the player heals 1.5 × EN a week, but he really
heals 120. A player showing P-1 is still injured for the next game when his
injury level is above 120 and below 1.5 × EN:

| EN  | Injury levels that stay P-1 | Left after healing |
| :-- | :-------------------------- | :----------------- |
| 81  | 121                         | 1                  |
| 82  | 121-122                     | 1-2                |
| 83  | 121-124                     | 1-4                |
| 84  | 121-125                     | 1-5                |
| 85  | 121-127                     | 1-7                |
| 86  | 121-128                     | 1-8                |
| 87  | 121-130                     | 1-10               |
| 88  | 121-131                     | 1-11               |
| 89  | 121-133                     | 1-13               |
| 90  | 121-134                     | 1-14               |

- EN 81-83 assume 120 a week; not seen yet.
- Never on IR/PS (135 a week) or at EN 91 (150 a week): they heal more than
  1.5 × EN.

### Ratings while injured

The substitution screen shows an injured player's ratings cut by his status:
P by 10%, Q by 40%, D by 70%, O by 100% (manual; P and D checked). SP, AC,
AG, ST, HA and EN are cut, rounded down; IN and DI are not.

| Player         | Status | Ratings | SP | AC | AG | ST | HA | EN | IN | DI |
| :------------- | :----- | :------ | -: | -: | -: | -: | -: | -: | -: | -: |
| Morgan (T)     | P      | Normal  | 69 | 71 | 69 | 98 | 62 | 86 | 94 | 95 |
|                |        | Shown   | 62 | 63 | 62 | 88 | 55 | 77 | 94 | 95 |
| Tuipulotu (DT) | D      | Normal  | 59 | 54 | 63 | 97 | 55 | 88 | 86 | 88 |
|                |        | Shown   | 17 | 16 | 18 | 29 | 16 | 26 | 86 | 88 |

## Positions

Notes specific to each position.

### All positions

#### EN

Weekly injury healing: 120 points at EN 84-90, 150 at EN 91; 15 more on
IR/PS.

## Play editor

Which options the game's play editor offers each player, checked in the editor.

### Normal plays

| Position       | Before snap         | After snap                                                                                                     |
| :------------- | :------------------ | :------------------------------------------------------------------------------------------------------------- |
| QB             | Random snap count   | Move to, Block, Stop and wait, Pass, Look for pass, Stop looking for pass, Throw a fake, Handoff/Pitch, Run    |
| HB, FB, WR, TE | Shift, Go in motion | Same as QB                                                                                                     |
| C              | Snap to             | Move to, Block, Stop and wait                                                                                  |
| G, T           |                     | Move to, Block, Stop and wait                                                                                  |
| DT, DE         |                     | Move to, Stop and wait, Read, Pass rush, Run rush, Pursuit is                                                  |
| LB, CB, S      | Line up on man      | Move to, Stop and wait, Read, Key on, Pass defense, Run defense, Blitz, If run pursuit is, If pass coverage is |

### Special teams

| Team         | Before snap             | After snap                                                                                                            |
| :----------- | :---------------------- | :-------------------------------------------------------------------------------------------------------------------- |
| Kicking team | Shift, Snap to          | Move to, Block, Stop and wait, Handoff/Pitch, Pass, Look for pass, Run, Pursuit is, Down ball, Spike ball             |
| Return team  | Line up on man, Snap to | Move to, Block, Stop and wait, Catch kickoff, Read, Key on, Blitz, Pass rush, Run rush, Pass defense, Run, Pursuit is |

Who gets the before-snap options:

- Kicking team on kickoffs, onside kicks, field goals, PATs and punts: every
  player, except that K and P get no Snap to, and G and T get neither on
  kickoffs and punts (C does).
- Return team on kickoff and onside returns: every player except C, G and T, by
  position, not by where they line up.
- Return team on punt, field goal and PAT returns: every player.

### Notes

- Snap to goes to the player in the snapper spot, whatever the position: a T
  substituted for the C gets it.
- Pass is Timed pass, Check receivers or Fake pass; Handoff/Pitch and Blitz are
  real or fake; Go in motion continues to the snap, stops and gets set, or
  reverses.
- Every return-team position gets the same after-snap options; once Pass rush,
  Run rush or Block is in a logic box, only Pursuit is can still be added to
  it.
- The kicks (Kick, Punt, Onside kick, Squib kick) are not in the kicking team's
  list.
