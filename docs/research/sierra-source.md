# Sierra FbPro98 source: research notes

- Source: `E:\PNFL\__My Projects\Sierra Source Code`, read-only, read 2026-10-16.
- Citations are `FILE:line` in `FBPRO98\src` unless marked "Formats.txt" (`FBPRO98\doc\Fb98 File Formats.txt`) or "fbcodesml".
- "Inference" marks a point the code does not prove.
- Our docs named here are compared as they stood on 2026-10-16.
- The planned spec and doc changes are in sections 14 and 15, for the 2.0.0 TODOs.

## 1. What the source is

- The front end only: league, rosters, draft, training camp, aging, injury bookkeeping, trades, schedules, stats I/O, and the play, plan and profile editors.
- Missing:
  - the on-field simulation and the computer's play calling (`GAME.CPP` is absent);
  - the automatic play categorizer `D_PLAYCAT::Get` (called at `PLAY.CPP:2285`);
  - `GAMESAVE.CPP`, `MAGAZINE.CPP`, `PLYRRDWR.CPP`, the stock-play class, the `COM::` command code numbers;
  - `awardval.hxx`, so every award weight is unknown (`STATFILE.CPP:57`).
- An older file format than the installed game writes:

  | Item | Source | Installed game's files (our specs) |
  | :--- | :--- | :--- |
  | `.lge` chunk tags | `L02`, `C00`, `D00`, `T02`, `R01`, `SCD` (`LCDTGLOB.CPP:40-45`, dated 1995) | `L03`, `C03`, `D03`, `T03`, `R03`, `S03` ([lge.md](../formats/lge.md)) |
  | `.pyr` record | 51 bytes (`PLYRRDWR.H:42-53`) | 60 bytes ([pyr.md](../formats/pyr.md)) |
  | `.prf` audibles field | absent (`CPROFILE.CPP:344-374`) | present ([prf.md](../formats/prf.md)) |

  - So the shipped game's logic may differ from this code.
  - Sizes and field order still match for the C, D, T, R and S chunks.
- `Formats.txt` (dated 2-Apr-97) does describe the '98 files, with a few errors (section 9.9).
- `fbcodesml` holds copies or strict subsets of the `src` files; `fbcode.h` holds the league, team, roster and schedule disk structs.
- `PERCENT.H`, `NPO.H`, `EDITPLYR.H` and `PLYREDIT.H` have no `.CPP` and no callers.
- The `LCDT` build flag is defined nowhere in the tree; which shipped program uses which value is unknown.

## 2. Bonus ratings

### 2.1 No game-time boost in this code

- Nothing here lifts a player above his stored actual ratings: no hot, clutch, morale, chemistry, veteran, home-field or difficulty field, and no random rating noise.
- The team record has no advantage flag (`TEAM.CPP:77-109`); `ownerType` is stored but never read.
- `manage` (computer control) changes roster management only (section 5).
- `GAME.H` holds whole-game data only: ground rules, weather, quarter length, sim mode, profiles and plans (`GAME.H:65-129`).
- The simulation is absent, so a game-time effect cannot be ruled out.
- A load-time scaling of actuals by position sits inside `#if 0`, so it never ran (`ROSPLYR.CPP:1891-1921`): OL ST/AG ×1.07, DL ×0.96, QB AG/SP ×1.05 and DI ×0.95, DB HA ×1.04.

### 2.2 Hidden boosts when the game creates a player

`RosPlayer::Generate` (`ROSPLYR.CPP:994-1093`) rolls potential, then actual as a share of potential (1077, 1080), then the blessing and the superstar roll (1087-1090).

| Boost | Who | Effect | Source |
| :--- | :--- | :--- | :--- |
| Range boost | 5% of generated players | both ends of every potential range +25%, high end capped at 99; actual follows, since it is rolled from the boosted potential | `ROSPLYR.CPP:98-103, 2140-2165` |
| Blessed position | every player of one random position group, once per college class | +5 to +10 potential on 3 key ratings | `LEAGUE.CPP:5255-5257`; `ROSPLYR.CPP:1087-1088, 2298-2315` |
| Superstar | 1 in 1,024 generated players | blessed 3 times: +15 to +30 potential on the same 3 ratings | `ROSPLYR.CPP:97, 2092-2102` |

- The blessing and the superstar raise potential only; actual is already rolled.
- The blessed position is printed only to a debug monitor (`LEAGUE.CPP:5257`); no screen shows it.
- New-league free agents and emergency free agents are never blessed (`LEAGUE.CPP:5295-5304`; `FAPOOL.CPP:282`), but can still roll superstar.
- The comment says superstar is "1 in 1000"; the constant is 1024.
- A debug switch, off, would prefix boosted names with "SS " (`ROSPLYR.CPP:85, 1064-1075`).
- Inference: 5% assumes `getRandPercent` returns 1-100 (its definition is not in the tree).

Key ratings per position (`bonusPBR`, `ROSPLYR.CPP:358-375`):

| Position | Ratings |
| :--- | :--- |
| QB | IN, HA, DI |
| FB | ST, AC, AG |
| HB | HA, SP, AG |
| TE | ST, HA, AG |
| WR | SP, HA, AC |
| C | HA, ST, EN |
| G, T | ST, EN, AC |
| DE | AC, ST, SP |
| DT | ST, EN, AG |
| LB | SP, AG, IN |
| CB | ST, SP, AC |
| S | SP, HA, AG |
| K, P | ST, HA, AC |

Why these players end up better:

- Potential is hidden in the game but stored in the `.pyr` ([pyr.md](../formats/pyr.md)).
- Camp gains grow with the gap between actual and potential (section 3.3), so a boosted player grows faster and higher.
- Only players the game creates get boosts: the college class in continuing leagues, the free agents of a new league, and emergency free agents.

### 2.3 Rating cuts and limits

- Undrafted college players become free agents at 75% of potential and actual, for good (`LEAGUE.CPP:5334`, via 4741 and 5305).
- Emergency free agents get 60%, "the ability of a gomer" (`FAPOOL.CPP:284-286`).
- Every rating caps at 99; raising actual above potential raises potential to match (`ROSPLYR.CPP:89, 1379-1381, 1963-1971`).
- No code path creates actual above potential.

## 3. Player life cycle

### 3.1 Generation

- Potential = 10 + low + rand % (high − low), capped at 99 (`ROSPLYR.CPP:2136-2206`).
- Actual = potential × pct / 100.
- Ranges by group, before boosts (`ROSPLYR.CPP:260-325`); each cell is potential range / actual as % of potential:

| Group | AC | AG | DI | EN | HA | IN | SP | ST |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| QB | 65-89 / 50-89% | 65-89 / 50-89% | 70-99 / 50-89% | 40-89 / 40-79% | 65-99 / 50-89% | 70-99 / 60-89% | 60-89 / 50-89% | 75-99 / 60-89% |
| RB | 90-99 / 60-89% | 85-99 / 60-89% | 55-99 / 40-79% | 65-99 / 50-89% | 75-99 / 50-89% | 50-99 / 60-89% | 85-99 / 60-89% | 50-94 / 40-79% |
| REC | 90-99 / 60-89% | 90-99 / 50-89% | 50-89 / 40-79% | 75-99 / 50-89% | 85-99 / 60-89% | 50-89 / 60-89% | 90-99 / 60-79% | 50-94 / 40-79% |
| OL | 45-79 / 40-79% | 50-79 / 40-79% | 70-99 / 40-79% | 75-99 / 40-79% | 60-89 / 40-79% | 40-99 / 60-89% | 45-88 / 50-89% | 80-99 / 50-89% |
| DL | 55-89 / 50-89% | 55-89 / 40-79% | 70-99 / 40-79% | 75-99 / 40-79% | 55-89 / 40-79% | 50-89 / 60-89% | 70-94 / 50-89% | 75-99 / 50-89% |
| LB | 65-99 / 50-89% | 65-94 / 50-89% | 60-99 / 50-89% | 75-99 / 40-79% | 65-94 / 40-79% | 65-99 / 60-89% | 65-94 / 50-89% | 70-99 / 40-79% |
| DB | 90-99 / 60-89% | 80-99 / 60-89% | 50-89 / 40-79% | 75-99 / 50-89% | 80-99 / 50-89% | 55-99 / 60-89% | 85-99 / 60-79% | 50-99 / 40-79% |
| K/P | 50-84 / 40-79% | 40-69 / 40-79% | 65-99 / 50-89% | 30-69 / 40-79% | 55-99 / 40-79% | 50-84 / 60-89% | 30-69 / 40-79% | 85-99 / 50-89% |

- Specific position, from potential (`ROSPLYR.CPP:333-356, 2224-2282`):
  - FB if ST > 67, else HB.
  - TE if ST > 78, else WR.
  - C if HA > 74, else G; a G becomes T on a coin flip.
  - DE if SP > 72, else DT.
  - CB if ST > 72, else S.
- College class size per position = talent target minus healthy rostered players (`LEAGUE.CPP:289-307, 5260-5267`).

### 3.2 Positions repaired on load

- A bad specific position is rebuilt from the group: RB→HB, REC→WR, OL→G, DL→DE, DB→S; a bad group is rebuilt from the specific position (`ROSPLYR.CPP:1802-1928`).
- The fix is written back to the `.pyr`.

### 3.3 Training camp

`RosPlayer::Train` (`ROSPLYR.CPP:1273-1341`), once per camp, per rating:

- Ratio = actual × 1000 / potential.
- Gain per 5% of the rating's share of camp time, in thousandths of potential:

  | Ratio | Gain per 5% |
  | :--- | ---: |
  | below 660 | 20 |
  | 660-709 | 15 |
  | 710-759 | 13 |
  | 760-809 | 10 |
  | 810-859 | 8 |
  | 860-909 | 5 |
  | 910-959 | 3 |
  | 960 and up | 2 |

- 0% loses 150 thousandths (15% of potential); 1-4% neither gains nor loses (`pct / 5` is integer division).
- The result is capped at potential and floored at 0.
- Example: potential 80, actual 70 (ratio 875): 20% gives 71; 0% gives 58.
- Who trains:
  - Rostered players only; free agents are skipped (`LEAGUE.CPP:4853`).
  - IR players are skipped (`ROSTER.CPP:5713-5752`).
  - K and P share one row (`ROSTER.CPP:5748-5751`).
- Each row must total at least 100 (`ROSTER.CPP:3728-3751`); rows are zeroed after camp (`ROSTER.CPP:3801`).
- Computer teams use fixed rows (`ROSTER.CPP:7003-7083`; `TEAM.CPP:1556-1569`).
- The comment table at `ROSPLYR.CPP:1254-1262` is stale.

### 3.4 Aging

`RosPlayer::Age` and `ageBRs` (`ROSPLYR.CPP:1168-1178, 2346-2408`):

- Years go up by 1 at each rollover (`LEAGUE.CPP:5060-5106`); aging starts at year 7.
- Base = (years − 5) × factor × 6 / 8, with factor K 7, QB/OL/DL 8, P 10, RB/LB 11, REC/DB 12.
- AC, AG, EN, HA, SP and ST lose round(rand(1..5) × base / 100) potential each; DI and IN never age.
- Actual is rescaled to keep its share of potential.
- Examples: a QB at year 7 loses 0-1 per rating; a WR at year 15 loses 1-5.
- Everyone ages: rostered, IR and free agents (`ROSTER.CPP:2394-2407`; `FAPOOL.CPP:160-175`).

### 3.5 Retirement

Rostered players, `Roster::Retire` (`ROSTER.CPP:2448-2615`), every team, human or computer:

1. Each team retires 4-11 players a season (`ROSTER.CPP:123-125, 2451`).
2. Always retired, no cap: career-ending injuries and players at the mandatory age (`ROSTER.CPP:304-315, 2455-2475`): QB 16, RB 14, REC 13, OL 15, DL 14, LB 15, DB 13, K 16, P 12.
3. If short, 40%: one "surprise" retirement of a player with 5 years or fewer in an open, inactive or IR slot (`ROSTER.CPP:125, 2481-2527`).
4. If short, 40%: up to 2 players with 6+ years, walking back from the last IR slot (`ROSTER.CPP:126, 2537-2560`).
5. While short: the player closest to his mandatory age, if under 5 years away and not first at his position (`ROSTER.CPP:2579-2588`).
6. Then the depth chart is re-sorted by the computer, for human teams too (`ROSTER.CPP:2614`).

Free agents, `RosPlayer::Retire` (`ROSPLYR.CPP:1215-1244`, table 381-390):

- Chance by years: 1% at 1, 3% at 3, 11% at 5, 31% at 7, 67% at 10, 81% at 12, 99% at 15.
- Past 15 years the loop reads beyond its table (no bound check).

### 3.6 Season reset

- `SeasonReset` clears injuries only, despite its comment (`ROSPLYR.CPP:1140-1150`).
- A career-ending injury stays unless forced; single-season leagues force it (`LEAGUE.CPP:5027`).

## 4. Injuries

- Levels (`ROSPLYR.H:114-122`): P 1, Q 151, D 301, O 451, career-ending 9999.
- Points cap at 9999, so enough injuries add up to career-ending (`ROSPLYR.CPP:1681-1682`).
- Career-ending players never heal (`ROSPLYR.CPP:1503`) and always retire (`ROSTER.CPP:2462`).
- Weekly healing by EN (`ROSPLYR.CPP:1499-1531`), plus 15 on IR, no randomness:

  | EN | Healed |
  | :--- | ---: |
  | up to 30 | 30 |
  | 31-50 | 60 |
  | 51-70 | 90 |
  | 71-90 | 120 |
  | 91+ | 150 |

- Every team heals before each week's games, byes and IR included (`LEAGUE.CPP:3826-3891`).
- Weeks out = 1 + points / (EN × 3 / 2), with EN × 3 / 2 truncated first (`ROSPLYR.CPP:1441-1461`).
- IR needs 6 or more weeks out (`ROSPLYR.H:131-134`; `ROSPLYR.CPP:1476-1481`).
- A new injury rolls the body part, and the points at that moment pick the name, e.g. ankle: up to 75 bruised, 300 strained, 525 sprained, more broken (`ROSPLYR.CPP:1549-1686`).
- A second injury adds points to the existing level and keeps the first type and week (`ROSPLYR.CPP:1543-1545, 1680-1684`); whether the engine does this is unknown.
- An injured player released to free agency is healed on the spot (`LEAGUE.CPP:3135-3142`).
- Single-season leagues halve a career-ending injury (`LEAGUE.CPP:3933-3936`).
- A career-ending replacement is signed automatically for computer teams only (`ROSTER.CPP:2891-2911`; `TEAM.CPP:1641-1652`).
- In a 17-week season the two finalists heal twice before the final (`LEAGUE.CPP:3869-3890`).

Injury names, by type (`ROSPLYR.CPP:117-163`):

| # | Injury | # | Injury | # | Injury |
| ---: | :--- | ---: | :--- | ---: | :--- |
| 0 | bruised ankle | 11 | strained chest | 22 | knee cartilage |
| 1 | strained ankle | 12 | fractured rib | 23 | bruised calf |
| 2 | sprained ankle | 13 | dislocated rib | 24 | strained calf |
| 3 | broken ankle | 14 | bruised thigh | 25 | broken leg |
| 4 | bruised arm | 15 | strained hamstring | 26 | sore neck |
| 5 | strained wrist | 16 | fractured femur | 27 | neck strain |
| 6 | broken finger | 17 | strained hip | 28 | neck sprain |
| 7 | broken hand | 18 | hip fracture | 29 | dislocated disk |
| 8 | sore back | 19 | dislocated hip | 30 | bruised shoulder |
| 9 | strained back | 20 | sore knee | 31 | strained shoulder |
| 10 | ruptured disk | 21 | bruised knee | 32 | dislocated shoulder |

## 5. Computer teams

### 5.1 How they value players

- Weighted sum of actual ratings (`SumBrs`, `ROSPLYR.CPP:1991-2075`), with a fixed table (`LCDTGLOB.CPP:66-80`); each row sums to 20:

  | | AC | AG | DI | EN | HA | IN | SP | ST |
  | :--- | --: | --: | --: | --: | --: | --: | --: | --: |
  | QB | 1 | 1 | 2 | 2 | 3 | 5 | 2 | 4 |
  | FB | 3 | 2 | 1 | 2 | 2 | 1 | 4 | 5 |
  | HB | 3 | 2 | 1 | 2 | 4 | 1 | 5 | 2 |
  | TE | 3 | 2 | 1 | 2 | 4 | 1 | 2 | 5 |
  | WR | 3 | 2 | 1 | 3 | 5 | 1 | 4 | 1 |
  | C | 3 | 2 | 2 | 2 | 3 | 1 | 2 | 5 |
  | G | 2 | 3 | 2 | 2 | 2 | 1 | 3 | 5 |
  | T | 5 | 1 | 2 | 2 | 2 | 1 | 2 | 5 |
  | DE | 3 | 3 | 2 | 2 | 1 | 1 | 4 | 4 |
  | DT | 5 | 2 | 2 | 2 | 1 | 1 | 2 | 5 |
  | LB | 2 | 2 | 1 | 2 | 3 | 2 | 4 | 4 |
  | CB | 3 | 4 | 1 | 3 | 2 | 2 | 4 | 1 |
  | S | 2 | 2 | 1 | 3 | 4 | 2 | 4 | 2 |
  | K, P | 1 | 1 | 6 | 1 | 2 | 1 | 1 | 7 |

- Each team's stored copy is ignored on load and rewritten on save (`ROSTER.CPP:4086-4089, 4232-4236`).
- The weights only order players; they change no rating.
- Potential is never used: the only read sits inside `#if OBSOLETE` (`ROSTER.CPP:7134-7624`).
- Injured value is cut to 56/64 (1-151 points), 38/64 (152-301), 19/64 (302-451) or 0 (452+) (`ROSPLYR.CPP:944-972`).

### 5.2 Depth chart

- `ManageSlots` (`ROSTER.CPP:4472-4623`) fills each group's assigned slots with its best non-IR players: QB 2, RB 3, REC 5, OL 6, DL 4, LB 5, DB 7, K 1, P 1.
- The rest are pooled across positions: the top 12 are open active, everyone else inactive.
- It runs after roster moves for computer teams only (`TEAM.CPP:1618`), but after retirement for every team (`ROSTER.CPP:2614`).

### 5.3 Draft and signings

- College round (`ROSTER.CPP:5295-5341`):
  - Positions are tried by need; never K or P.
  - Then the best player overall, QB to DB only (`ROSTER.CPP:5503`).
- Position caps (`ROSTER.CPP:278-289`): QB 4, RB 8, REC 10, OL 11, DL 9, LB 9, DB 10, K 2, P 2.
- Unless forced, a draftee must match the specific position of the team's worst player in that group and be worth more (`ROSTER.CPP:5590-5609`).
- Weekly signing goes worst record first (`LEAGUE.CPP:3535-3598`); a pick is forced when injured starters lack healthy backups (`ROSTER.CPP:5845-5889`).
- Empty slots before a game get 60% emergency players when no free agent fits (`ROSTER.CPP:5408-5457`).
- A human team with empty assigned slots blocks the week (`LEAGUE.CPP:2319-2333`).

### 5.4 Trades

`Roster::TradeEval` (`ROSTER.CPP:3020-3112`) runs for computer teams only (`TEAM.CPP:1676-1679`).

- Trade-proof players, by raw rating sum (`ROSTER.CPP:291-302, 6951-6975`): top QB 1, RB 2, REC 4, OL 5, DL 3, LB 4, DB 6, K 1, P 1.
- Equal counts (1-for-1, 2-for-2, 3-for-3): accepted when no outgoing player is trade-proof and each incoming player beats at least one of the computer's players at his position, or it has none there.
  - Incoming and outgoing values are never compared.
- Uneven counts, a bug: every pass reads the first pair only (`ROSTER.CPP:3074-3075`).
  - Accepted when 90% of incoming #1 ≤ outgoing #1 < incoming #1.
  - Extra players are ignored, with no trade-proof check.
  - Inference: extra computer players come free.
- Injury check, a bug: the count loop stops at the first incoming player with 151+ points (`ROSTER.CPP:3028-3041`).
  - Listed first, both counts are 0 and the trade is accepted unchecked.
  - Listed later, only the pairs before him are checked.
- Computer-to-computer trades: 20% of weeks (`ROSTER.CPP:4893`), at most 1 per team per week, only in the first half of the regular season (`LEAGUE.CPP:117, 3603-3648`).
- A human's proposal to a computer team needs the same group, or an open or inactive human player; uneven trades need roster holes (`LEAGUE.CPP:2824-2951`).
- A player released to free agency drops out of every pending trade (`LEAGUE.CPP:3169-3183`).

### 5.5 Draft strategy ranks

- Each team has 10 ranks: run inside, run outside, pass long, pass short, defend run, defend pass, rush pass, kicking, punting, trade (`ROSTER.H:116-125`).
- They score which position to acquire (highest) and which to trade away (lowest) (`ROSTER.CPP:6810-6852, 6872-6935`).
- The OL score counts run inside twice and never run outside (`ROSTER.CPP:6898, 6901`); inference: a typo.
- Each new season, `GenerateStrategies` moves them by last season's league ranks (`ROSTER.CPP:3570-3613`; `LEAGUE.CPP:6357-6403`).
  - Inference: a team leans further into what it already does well.
- "Trade" (best overall) stays at rank 0 and never moves (`ROSTER.CPP:3604, 6784`).

### 5.6 IR and releases

- The computer puts a player on IR only if his weeks out cover the rest of the regular season, and never takes one off mid-season (`ROSTER.CPP:4749-4867`).
- Its "sickest first" sort is unreliable: it scales one side by 16 and not the other (`ROSTER.CPP:6379, 6386`).
- At preseason, an IR player returns if he beats the worst rostered player; the rest are released (`ROSTER.CPP:4645-4723`).
- A forced release drops the last healthy inactive player (`ROSTER.CPP:2802-2825`).
- No college class is made while any team, human included, still has IR players (`LEAGUE.CPP:5115-5120, 5148-5150`).

## 6. Plays (`.ply`)

- Old format: a first offset of 24 means an old stock play with no user-category byte; user category = play category (`PLAY.CPP:206-209`).
- Old play blocks are converted, auto-categorized and rewritten on disk (`PLAY.CPP:3184-3209`).
- Role flags (`PLAY.CPP:273-285, 639-649`):
  - The game finds the snap taker by role bit 1 on whatever slot holds it, not by slot 0.
  - Only one slot keeps each flag; on load the last flagged slot wins.
- Argument count: only the low 4 bits of its byte count (`PLAY.CPP:243-246`).
  - Load reads arguments only for counts 1 and 2 (`PLAY.CPP:248-265`); save recomputes the count (`PLAY.CPP:676-683`).
- Coordinates pass through the editor's pixel grid on every load and save (`PLAY.CPP:2616-2630`).
  - Inference: re-saving in the game snaps x to steps of about 7.8 units.
- The editor starts a new play as `Off_Wiz` or `Def_Wiz`, with both categories 0xFF (offense) or 0xFE (defense), shown as "USER SPECIFIC" (`PLAY.CPP:140-157, 2315-2319`).
- Coaches change only the user category; the play category changes only in Sierra's internal mode (`PLAY.CPP:2485-2496`).
- Side comes from bit 0 of the play category, not the user category (`PLAY.CPP:288`).
- The game names every 6-bit category value (`PLAY.CPP:2322-2382`):
  - Goal line overrides side; Razzle Dazzle overrides distance.
  - A run shows no distance; a defensive pass shows no side.
- Special codes 13-16 exist: run random and pass long, medium and short random (`PLAY.CPP:2460-2474`).
- Defensive fakes show the offense names, e.g. "FAKE FIELD GOAL RUN" (`PLAY.CPP:2420-2434`).
- Load fails only when the file will not open or has no play block (`PLAY.CPP:3245-3274`); nothing else is checked.

## 7. Game plans (`.pln`)

- A stock record's offset and size locate the play body in the stock data file (`PLAN.CPP:1132-1135`); the error text names `STOCK.DAT` (`PLAY.CPP:3222`).
  - Inference: the `.MAP` is the name index (`GetStockOffset`, `PLAN.CPP:123`).
- Stock records in regular slots are used as stored; the name is not looked up again (`PLAN.CPP:181-186`).
- Custom records take their category bytes from the `.ply` on every load (`PLAN.CPP:189-196`).
  - So re-categorizing a play changes every plan that uses it.
- Stock specials (entries 65, 67 … 83) are rebuilt from fixed names on load (`PLAN.CPP:102-125`); the file's copies have no effect.
  - Offense: FGPAT, KICKOFF, PUNT, ONSDKICK, FKFGRUN, FKFGPASS, FKPNTRUN, FKPNTPAS, FREEKICK, SQUIB.
  - Defense: FGPATD, KICKRET, PUNTRET, ONSIDRET, FKFGRUND, FKFGPASD, FKPNTRND, FKPNTPSD, FREERET, SQUIBRET.
- Clock entries 84-85 are never read; RUNCLOCK and STOPCLOK are rebuilt for offense (`PLAN.CPP:127-135, 166, 230`).
- A custom path without a drive gets the plays folder in front (`PLAN.CPP:172-180`).
- Load always succeeds (`PLAN.CPP:141-286`).
  - A custom play that fails to open, lacks a play block, or has the wrong side or special type empties its slot.
  - A custom special must match the record's stored special byte, not the slot (`PLAN.CPP:255`).
  - Side comes from where the editor is, not the info block (`PLAN.CPP:158`).
- J95 counts feed only the file dialog; load recounts (`PLAN.CPP:148-151, 477-483`).
- The 4 audible bytes default to 0, 1, 2, 3; the setter is compiled out, "dropped from the game" (`PLAN.CPP:90-91`; `PLAN.H:82-94`).
- An older 32-slot plan format is still read (`PLAN.CPP:289-395`).
- New teams default to OFF1.PRF + OFF.PLN, DEF1.PRF + DEF.PLN, OFF2.PRF + OFF.PLN, DEF2.PRF + DEF.PLN (`TEAM.CPP:2148-2187`).

## 8. Profiles (`.prf`) and play calling

- Play codes 128 and up call one plan slot: code − 128 (`CPROFILE.CPP:218-234, 1390-1399`).
  - Slots are numbers, not names, so moving plays in the plan breaks them.
  - Codes 27-127 are undefined.
- Weights keep 4 bits, 0-15 (`CPROFILE.CPP:764, 811, 833`); Stop Clock is bit 7 of pick 1's weight (`CPROFILE.CPP:767-768`).
- A pick's chance is its weight over the situation's total, rounded to sum to 100 (`CPROFILE.CPP:1345-1370`).
  - Inference: a weighted random pick; the engine is absent.
- PAT weights tolerate the Stop Clock bit and mask it off (`CPROFILE.CPP:788-789, 833`).
- The FG range relabels the field buckets "DEF 5-<FG>" and "DEF <FG>-OFF 35" (`CPROFILE.CPP:1074-1082`).
  - Inference: the bucket edge is the FG range yard line, not a fixed DEF 35.
- FG range prints as "N yard line" (`CPROFILE.CPP:1175-1177`).
- Situation index = time × 560 + down × 140 + to-go × 35 + field × 7 + score, minus the excluded combinations (`CPROFILE.CPP:53-68, 118-144`).
- Codes 23-26 are the "random direction" member of the run and pass long, medium and short groups (`Cycle`, `CPROFILE.CPP:691-702`).
- A plan play maps to a profile code by its user category, or its play category for 0xFF/0xFE (`GetGeneralType`, `CPROFILE.CPP:240-293, 489-492`).
- Fallbacks:
  - When a plan's custom play will not load, profile entries pointing at it become the play's general code (`PLAN.CPP:203-218`).
  - An entry pointing at an empty slot becomes code 0, goal line run (`CPROFILE.CPP:496-497`).
- Profiles cannot call kickoff, onside, squib or free kick; inference: the engine picks those.
- Defaults (`CPROFILE.CPP:435-463`):
  - every situation calls goal line run, weight 1;
  - every PAT calls FG/PAT;
  - FG range 35;
  - substitutions 70 out, 85 in.
- I95 block (`CPROFILE.CPP:380-428`): side (1), specific-play count (u16), FG range (1), plan flag (u16), then an optional 33-byte password.
  - Password byte i: XOR 0x69 × i, then swap nibbles with the high one inverted.
- F95 data is subs (32) + situations (15,120) + FG range (1) + PAT (360) = 15,513 bytes, with no audibles (`CPROFILE.CPP:344-374`).
- Load checks nothing (`CPROFILE.CPP:344-358`).

## 9. League files

### 9.1 `.lge` league chunk

From `LeagueDiskDataF` (`LEAGUE.CPP:155-171`), `fbcode.h:25-41` and Formats.txt:26-46:

| Byte | Field |
| :--- | :--- |
| 0x00 | size: 0 = 8, 1 = 10, 2 = 12, 3 = 18, 4 = 28, 5 = 30 teams, 6 = Pro Bowl (`LEAGUE.H:143-153`) |
| 0x01 | conference count |
| 0x02 | type: 0 continuing, 1 single season, 2 Pro Bowl |
| 0x03 | stage, 0-15 (section 12) |
| 0x04 | file type: 0 master, 1 original, 2 copy |
| 0x05 | NFL logos valid |
| 0x06 | u16 unique id, unused |
| 0x0C | seasons played (1 byte) |
| 0x0D | quarter length: 0 = 5, 1 = 10, 2 = 15 minutes |
| 0x0E | rule bits: fatigue, fumbles, injuries, interceptions, penalties, 45-second clock, fast sim |
| 0x41 | commissioner phone, 17 bytes, unused |
| after conference ids | auto retirement, salary caps, trades disabled (1 byte each), then u32 flags |

- Inference: rule bits run low bit first; the defaults give 0x3F (`LEAGUE.CPP:6585-6596`).
- Bit 7 of the rule byte is never set, so it holds leftover memory; that explains 0x3F vs 0xBF (`LEAGUE.CPP:4521-4524`).
- Inference from sizes: PNFL's tail `00 00 01` means auto retirement off, no salary cap, trades disabled.
- No difficulty setting exists.

### 9.2 Conference and team chunks

- C03 byte 3: a real conference vs an internal-only unit, as in the 8-team league (`CONFER.H:17-20`).
- T03 (`TEAM.CPP:77-109`):
  - coach is 25 bytes;
  - a 9-byte password follows, plain text inside the mask;
  - then the NFL team id and 16 unused bytes, then the draft profile.
- Team name 16 characters (`TEAM.CPP:821-825`); league, trophy, conference and division names 23 (`LEAGUE.CPP:1373-1398`).

### 9.3 Roster chunk

325 bytes (Formats.txt:48-55; `fbcode.h:143-184`):

| Part | Bytes |
| :--- | ---: |
| team id | 2 |
| player ids, 63 × u16 | 126 |
| jerseys | 63 |
| draft strategy ranks (section 5.5) | 10 |
| training rows, 8 groups × 8 ratings | 64 |
| rating weights, 15 positions × 8 four-bit values, low nibble first | 60 |

- The weights equal the fixed table in section 5.1, rewritten on every save.
- Jersey ranges for new numbers (`ROSTER.CPP:2171-2234`): QB/K/P 1-19, RB and DB 20-49, OL 50-69, DL 60-79 or 90-99, LB 50-59 or 70-79, REC 80-89.
- A team needs all 46 game slots filled to play (`ROSTER.CPP:3489-3510`).

### 9.4 Schedule chunk

- Game status: −2 play paused, −1 sim paused, 0 done, 1 sim, 2 play, 3 paused; new games are 2 (`SCHTEMP.H:83-91`; `SCHTEMP.CPP:282, 332`).
- Weeks played = 255 before the season and after the last playoff game (`SCHEDULE.CPP:657, 926-930`).
- Scores and team ids are signed bytes; −1 = unplayed (`SCHTEMP.H:45-49`).

### 9.5 `.pyr`

- Coding table from the 2-byte header key (`ENCRYPT.CPP:141-206`):
  - s = key byte 0, i = key byte 1.
  - Fill 256 slots with s − 1.
  - For k = 0..255, store s + k at the pointer, move it on by i (wrapping at 256), and step past filled slots.
  - Encode = table applied 3 times; decode = the inverse 3 times (`ENCRYPT.CPP:208-231`).
  - A new key is random: s 0-255, i 1-255 (`ENCRYPT.CPP:113-118`).
- Record index = id − 99, so the header is record 0 (`PLYRRDWR.H:109-110`).
- Players start at id 100 (`PLYRRDWR.H:108`).
- Bytes 0x33-0x3B, per Formats.txt:131-140 only (no code reads them): height, weight, skin color, original NFL team, original jersey, then B&W picture, color picture, player card and audio play-by-play flags, 1 byte each.
- No age, draft or status field exists.
- `status`, `modified` and `proBowlValue` live in memory only (`ROSPLYR.CPP:184-187`).
- The free-agent pool holds at most 3,000 players (`FAPOOL.CPP:40-42`).

### 9.6 `.lg2`

- Record at 4193 × (team id − 1) (`TEAM.CPP:2252, 2324`); entries are profile then plan, offense then defense, half 1 then half 2 (`TEAM.CPP:2262-2276`).
- Number color 1 = jersey; defaults: dark home jersey, numbers in the pants color (code 3) (`TEAM.H:100-108`; `TEAM.CPP:2190-2192`).
- A missing or short file silently gives every team the default profiles and plans (`TEAM.CPP:2245-2303`).
- It is rewritten on every league save (`TEAM.CPP:581-582`).

### 9.7 Cities, calendar and schedule templates

- `CITIES.DAT` (`CITY.H:27-80`; `CITY.CPP:35-39, 537-608`):
  - 0x11 is base wind in mph; each game rolls ±8, minimum 0 (`CITY.CPP:319-329`).
  - Weather table byte 8 is the temperature level 'A'-'G'; byte 9 is base humidity: 100 in rain, otherwise ±10 or ±20 (`CITY.CPP:246-305`).
  - Rain beyond the first three ranges; snow is never returned here (`CITY.CPP:215-232`).
  - The heat-index and wind-chill tables are disabled (`CITY.CPP:338-339, 386-387`).
  - Stadium type: 0 outdoor grass, 1 outdoor turf, 2 indoor turf (`TEAM.H:78-81`).
  - This code reads nothing from 0x44 on.
- `calender.dat` (`CALENDER.CPP:40-174`):
  - SPC block: first year, last year, preseason weeks, weeks, calendar count, then a calendar number per year.
  - One SWC block per calendar: (month, day) per week.
  - Years past the last wrap around.
- `stpl.dat` (`SCHTEMP.CPP:172-377, 847-884`):
  - SCT block per league size: weeks, playoff weeks, games per week, then u16 games (high byte home slot, low byte visitor slot, 0 = bye).
  - SPT block: playoff count, division winners and wild cards per conference, then (home, visitor) code pairs.
  - Slots map to teams by a random shuffle inside fixed division sizes: 8 = 4,4; 10 = 3,4,3; 12 = 4,4,4; 18 = 4,5,4,5; 28 = 5,4,5,5,5,4; 30 = 5×6 (`SCHTEMP.CPP:196-241`).
  - The built-in schedule ignores last season's finish (`SCHEDULE.CPP:139-155`).

### 9.8 Other files

| File | Holds | Source |
| :--- | :--- | :--- |
| `.tmn` | team news: career-ending injuries as (team, player id), a `-1,-1` marker, then retirements | `TEAMNEWS.CPP:19-21, 265-318, 620-677` |
| `.trn` | trade news, block `TRN:`, u16 count, trade records | `TRADNEWS.CPP:48-49, 309-332` |
| `.pyc` | college draft pool | `CDPOOL.CPP:54` |
| `.rst` | last week's rosters, for box scores | `LEAGUE.CPP:2455-2523` |
| `.xxx` | temporary file for a safe save | `LEAGUE.CPP:1504-1518` |
| `.dft` | draft order: `DOD:`, u8 team count, u8 current pick, u8 round, then (team, enabled) pairs | `DRAFT.CPP:326-342` |
| `.DP` | draft profile: `DP0:`, 53 × (position, rating 1, rating 2), u8 rounds used | `DRAFTPRO.CPP:80, 330-341`; `DRAFTPRO.H:62-77` |
| `.lgc` | champions: winner name, score, loser name, score; the year is not stored | `LCHAMPS.CPP:38-121` |
| `ltplNN.lgt` | new-league templates | `LEAGUE.CPP:309-321, 1955-1996` |
| `ASGnnnn.LGE` | Pro Bowl leagues | `LEAGUE.CPP:5630-5645` |
| `tradelog.out` | optional trade log | `LEAGUE.CPP:4242-4249` |

- `.tmn` and `.trn` are wiped at the start of each week (`LEAGUE.CPP:3836-3841`; `TRADNEWS.CPP:114-118`).
- Accepting a trade rejects every other pending trade sharing a player (`TRADNEWS.CPP:206-291`).

### 9.9 Errors in Sierra's `Formats.txt`

- S03 "0 = unplayed": the code has 0 = done.
- `.lg2` number colors "light, then dark": the code writes dark first (`TEAM.CPP:2286-2293`).
- L03 numSeasons "SHORT": it is 1 byte (`LEAGUE.CPP:166`).
- `.pyr` positions "LONG": they are 1 byte on disk (`PLYRRDWR.H:49-50`).
- `.lg2` second-half defense pair labeled "profileOff/planOff" (lines 155-162).

## 10. Stats (`.dat`, `.idx`) and awards

### 10.1 File

- A FairCom c-tree ISAM pair (`STATFILE.CPP:15, 64-73, 128-159`): 20-byte records, 4,096-byte growth, 512-byte index nodes, a 4-byte big-endian key (type, id), no duplicates.
- First byte 0xFF marks a deleted record (`STATFILE.CPP:126`).
- If the files will not open, the game deletes both and starts empty; the backup copy is never made (`STATFILE.CPP:1073-1105, 1517-1538`).

### 10.2 Categories

Type = block base (0, 32, 64, 96, 130, 164, 198) + category (`STATDRVD.H:101-247`).

| Cat | Name | Values |
| ---: | :--- | :--- |
| 0 | PAT | attempts, made |
| 1 | FG | long, then 10/20/30/40/50 ranges (high byte attempts, low byte made) |
| 2 | Rushing | number, yards, long, TDs |
| 3 | Passing | as rushing + completions, INTs, sacks, sack yards |
| 4 | Receiving | as rushing |
| 5 | Interceptions | as rushing |
| 6 | Punting | punts, yards, long, 0, blocked, returns, return yards, touchbacks |
| 7 | Punt returns | as rushing + fair catches |
| 8 | Kick returns | as rushing |
| 9 | Fumbles | count |
| 10 | Fumble recoveries | as rushing |
| 11 | Sacks | count |
| 12 | Safeties | count |
| 13 | Tackles | count |
| 17 | Two-point conversions | attempts, made |

Categories 14-16 differ by block (`STATDRVD.H:122-184`):

| Cat | Player game | Player season | Player career | Team and opponent |
| ---: | :--- | :--- | :--- | :--- |
| 14 | Hall of Fame points | Hall of Fame points | Hall of Fame points | first downs: total, rush, pass, penalty |
| 15 | Player of the Game | All-Pro team | awards | first-down total, 3rd att, 3rd made, 4th att, 4th made |
| 16 | penalties | unused | Hall of Fame nominee | opponent, penalties, penalty yards, possession time, score (own × 256 + opp), fumbles lost |

- Hall of Fame points: v0 count, v1 conference, v2 points (`STATDRVD.H:796-800`).
- Player of the Game: id = game number + 1, 99 = Player of the Week; v0 points, v1 player, v2 team, v3 opponent (`STATFILE.CPP:1639, 1717-1724`).
- All-Pro: id = (position + 1) + conference × 16 + pick × 256; pick 0 consensus, 1 first team, 2-4 second team; id 4096 = Coach of the Year (`STATFILE.CPP:1935-1975, 2239-2249`).
- Awards: id = code + (year mod 100) × 256; codes 90 MVP, 91/93 offensive and 92/94 defensive player of the year per conference, 99 rookie of the year (`STATFILE.CPP:1774-1775, 1983-2025`).
- Hall of Fame nominee: v1 points, v2 year retired, v3 year elected, 0 = not yet (`STATDRVD.H:833-838`).
- Unused values are leftover memory, never cleared (`STATFILE.CPP:778-785`).

### 10.3 Rules

- Playoff games feed last-game records only, never season, career or awards (`STATFILE.CPP:479-480, 714, 732-733`).
- Weekly flush deletes all game records; season flush keeps All-Pro (`STATFILE.CPP:984-1022`).
- Team points = 6 × TDs + XPs + 3 × FGs + 2 × two-point conversions + 2 × safeties.
- Each game score is the sum of 5 quarter bytes, capped at 127 (`STATFILE.CPP:75-76, 499-503`).
- Averages are stored as value × 16 + tenths, truncated, sign in bit 15 (`STATFILE.CPP:267-303`).
- QB rating is the NFL formula, truncated to tenths, max 158.3 (`STATFILE.CPP:405-436`).
  - 32,768+ passing yards read as negative and zero the yards part.
- Leaders sort by yards, then TDs, then attempts; the passing completions step compares a player with himself (`STATFILE.CPP:1426-1473`).

### 10.4 Awards

- Player of the Game after each regular-season game: top game points; ties go to the first found, home team first (`STATFILE.CPP:1577-1621`).
- Season awards, All-Pro and the Hall of Fame vote run in the last regular-season week (`STATFILE.CPP:1765-1769`).
- Defensive = LB, DB, DL; everyone else, kickers and linemen included, counts as offense (`STATFILE.CPP:1542, 1822-1849`).
- Rookie of the year: top season points among 0-year players (`STATFILE.CPP:1855-1873`).
- All-Pro counts (`APTCOUNT.H:16-30`): QB 2, FB 2, HB 1, TE 2, WR 3, C 2, G 3, T 1, DE 4, DT 0, LB 5, CB 4, S 3, K 1, P 1.
  - No DT is ever named.
- The Pro Bowl uses the same counts (`LEAGUE.CPP:5708-5864`).
- Hall of Fame (`STATFILE.CPP:3342-3503`):
  - nominated at retirement, eligible 5 years later;
  - points scaled when a career outlasts the league's history;
  - inductees capped by league size and by a share of the top nominee's points.
- Bugs that change results:
  - the passing-yards award subtracts the completion threshold (`STATFILE.CPP:2357-2358`);
  - the longest-run award goes to the top scorer (`STATFILE.CPP:3322`);
  - the OL yards-per-carry award uses the passing average (`STATFILE.CPP:3156-3161`);
  - `=` instead of `+=` drops earlier points (`STATFILE.CPP:2505, 2581`).
- No award changes ratings; stats code only reads players (`STATFILE.CPP`, `TEAMNEWS.CPP`).

## 11. Standings, playoffs and draft order

- Win % = (4 × wins + ties) × 100 / games, so a tie is a quarter win; 1 before any game (`TEAM.CPP:1063-1082`).
  - Example: 6-5-5 ranks below 8-8-0.
- Regular season: win %, points for, fewer points against, team name (`LEAGUE.CPP:6083-6089, 6161-6185`).
- From the playoffs on, pairwise (`LEAGUE.CPP:6212-6282`):
  1. Win %.
  2. Head-to-head net wins.
  3. Same division: division net wins, conference net wins, common opponents, division net points, all net points.
  4. Different divisions: conference net wins, common opponents, conference net points, all net points.
  5. Team name, alphabetically.
- Quirks:
  - "Common opponents" always returns 0 (`SCHEDULE.CPP:1211-1218`).
  - "Division net points" checks the division index, not the conference (`SCHEDULE.CPP:1287-1289`).
  - Inference: net points wrap past ±127 (signed byte returns).
  - Multi-team ties use a pairwise sort, not the NFL group steps (`LEAGUE.CPP:952-968`).
- Division winner = first in its division; wild cards = next best from divisions already won (`SCHTEMP.CPP:537-587`).
- Seeds list conference 1's division winners, then conference 2's, then wild cards; the lower seed hosts (`SCHTEMP.CPP:411-417, 638-663`).
- A tied playoff game, or final, goes to the visitor (`SCHTEMP.CPP:493-497`; `LEAGUE.CPP:5000-5013`).
- Draft order: by record, champion last, runner-up second to last (`SCHEDULE.CPP:418-452`; `LEAGUE.CPP:4628-4636`).
  - Every round uses the same order, no snake (`DRAFT.CPP:376-384`); a random order is the other option (`DRAFT.CPP:435-457`).

## 12. Season flow

Stage is byte 0x03 of the league chunk (`LEAGUE.H:108-123`).

| Stage | Name | What happens |
| ---: | :--- | :--- |
| 13 | playoffs end | champion to `.lgc`; seasons +1; continuing leagues age and retire players (`LEAGUE.CPP:4982-5106`) |
| 14 | transition | every team must empty IR; computer teams do it, humans by hand (`LEAGUE.CPP:5128-5190`) |
| 15 | no bye info | 28-team leagues choose byes |
| 0 | start | continuing leagues: free agents wiped, new college class; draft order, schedule, records reset, draft strategies (`LEAGUE.CPP:4597-4677, 5167-5176`) |
| 1-3 | college draft | undrafted players become 75% free agents at the end (`LEAGUE.CPP:4735-4745`) |
| 4-6 | supplemental draft | (`LEAGUE.CPP:4760-4803`) |
| 7 | training start | needs every team's rows to pass (`LEAGUE.CPP:4819-4845`) |
| 8 | training end | season stats wiped; rostered players train (`LEAGUE.CPP:4861-4887`) |
| 9 | season start | |
| 10 | season running | set at the first game; weekly heal, games, injuries, roster moves (`LEAGUE.CPP:3518-3991`) |
| 12 | playoffs start | bracket set when the regular season ends (`LEAGUE.CPP:4962-4967`) |
| 11 | season end | never set by the game-complete path |

- Single-season leagues skip aging, retirement, the college class, the draft and strategies, and fully heal at season end (`LEAGUE.CPP:5026-5027, 5167-5181`).

## 13. From the manual and the user

Manual: `E:\Docs and Hints\Games\Front Page Sports Football Pro '98\Official Contents\Manual.pdf`, printed page numbers.

- **Tie value:**
  - The manual never says what a tie is worth; it ranks by "won-lost-tied percentage" (page 129).
  - athc counts a tie as half a win; the source counts it as a quarter win (section 11).
  - No PNFL season in the test files has a team with two or more ties, so the files cannot tell which one the shipped game uses.
- **Tie-breakers:** athc's game method follows the manual's 8 steps (page 129); the source's list differs (section 11).
- **Substitution %:**
  - The manual says the default is OUT 70%, IN 85% (pages 59 and 112), as does the source's blank profile.
  - The game's one default profile holds 75/85 (user).
  - In real profiles the other side's unused group bytes hold 80/90.
  - Every group the game shows can be edited (user); prf.md's "non-editable groups" is wrong.
  - New profiles are copies of an existing one, so no default is documented (user).
- **Field goal range:**
  - 5-50 yards (page 114).
  - A yard line on the defense's side: the field-position bands run "DEF 5 - your field goal range" and "your field goal range - OFF 35" (page 114), and the source prints "N yard line".
- **Weights:** the game's screen limits them to 0-10 (user); the source keeps 4 bits.
- **Profiles with plays:**
  - Using specific plays puts their game plan into the profile (manual, Generalize).
  - The PNFL does not support such profiles (user).
- **PAT Stop Clock bit:** no real profile has it. athc's reader rejects a profile with it; the source ignores it.

## 14. Planned spec changes

Each spec's ImHex pattern (`.hexpat`) changes to match. The Hex Workshop patterns `pln.hsl` and `prf.hsl` would need the same renames.

### pyr.md

- Answer the open question of how the header key builds the coding table (section 9.5; it rebuilds PNFL's table exactly).
- Record index = player id − 99; the header is record 0, and players start at id 100.
- Bytes 0x33-0x3B: height, weight, skin color, original NFL team, original jersey, then B&W picture, color picture, player card and audio flags (Formats.txt). Check `PNFL.pyr` weights first: any weight over 255 keeps the u16 weight.
- Injury type names, 0-32 (section 4).
- On load the game rebuilds a bad position from its group, or a bad group from its position, and writes it back.
- Ratings cap at 99; actual never exceeds potential.

### lge.md

- League chunk (section 9.1):
  - 0x00 league size code;
  - 0x02 league type;
  - 0x03 stage, 0-15 with names;
  - 0x04 file type;
  - 0x05 NFL logos valid;
  - 0x06 unused id;
  - 0x0C seasons played;
  - 0x0D quarter length;
  - 0x0E rule bits (bit 7 never set, which explains BF and 3F);
  - commissioner phone, unused;
  - the 7-byte tail: auto retirement, salary caps, trades disabled, flags.
- C03 byte 0x03: a real conference, or an internal-only unit.
- T03 0x6E-0xA0: head coach 25 bytes, password 9 bytes (never write a value), NFL team id, then unused.
- R03 0xBD: the 10 draft strategy ranks, in order run inside … trade; "trade" is fixed at 0; rebuilt each season.
- R03 0x107: rating weights, 15 positions × 8 four-bit values, the computer's player-value table, rewritten on every save.
- Training rows: a finished row totals 100; rows are cleared after camp; K and P share one.
- S03: game status values (−2, −1, 0, 1, 2, 3); weeks played = 255 before the season and after the last playoff game; scores are signed bytes.
- Open questions updated.

### lg2.md

- Number color code 1 = jersey (the spec says 1 is never used).
- A missing or short file gives every team OFF1.PRF / OFF.PLN / DEF1.PRF / DEF.PLN / OFF2.PRF / DEF2.PRF.
- New-team uniform: dark home jersey, numbers in the pants color.
- Team record at 4193 × (team number − 1); the file is created when team 1 is written and rewritten on every league save.

### ply.md

- Fix: the snap-taker flag can sit on any slot, not slot 0; only one slot keeps each role flag.
- Fix: on defense the game shows the fakes with the offense names; only FG/PAT, kick, punt, onside, free and squib have return labels.
- Argument count: only the low 4 bits count; the game reads arguments only for counts 1 and 2 and recomputes the count on save.
- New plays start as Off_Wiz / Def_Wiz with 0xFF / 0xFE, shown as User Specific.
- Old format: first offset 24 means no user-category byte; the game converts such plays and rewrites them.
- The game names every category value: goal line beats side, Razzle Dazzle beats distance. Special codes 13-16 are the random run and pass plays.
- Side comes from the play category's bit 0; coaches change only the user category.

### prf.md

- Info block +1 is the count of specific-play picks, 0 in profiles without plays.
- Pick codes 128 and up mean the play in game-plan slot (code − 128); codes 27-127 are unused.
- Codes 23-26 are the random-direction member of the run and pass long, medium and short groups.
- Field goal range is a yard line on the defense's side, 5-50; it moves the edge between the "DEF 5" and "DEF 35" field-position bands (manual page 114).
- Drop the "non-editable groups" and "game's default 80/90" sentence; the other side's groups are unused.

### pln.md

- 0x0C and 0x10 are the stock play's offset and size inside the stock play data file (check one record against `STOCK98.DAT` before naming it), not "unknown file".
- The game rebuilds the stock special plays and the clock plays from fixed names on every load, so the file's copies have no effect; list the names (section 7).
- A custom play's category bytes are re-read from its `.ply` on every load.
- A custom path without a drive gets the plays folder in front.
- The J95 counts only feed the file dialog; the game recounts on load.
- The 4 audible bytes (Up, Down, Left, Right) were dropped from the game.
- An older 32-slot plan format exists; profiles can address slots 0-73.

### stats.md

- The file pair is a c-tree database: names header 0x2E (4096 growth) and 0x30; 512-byte index nodes; a 4-byte big-endian key.
- Punting: value 4 is blocked punts, value 5 returns.
- Punt returns: value 4 is fair catches.
- Category 12 is safeties.
- Player categories 14-16 (section 10.2):
  - Hall of Fame points;
  - Player of the Game / Player of the Week, All-Pro team and awards, with their id encodings;
  - penalties, and Hall of Fame nominee.
- Team categories:
  - 14: first downs (total, rush, pass, penalty);
  - 15: third and fourth downs (attempts, made);
  - 16: opponent, penalties, penalty yards, time of possession, final score, fumbles lost.
- Team points include 2 × safeties.
- Playoff games feed last-game records only.
- The weekly and season clean-ups; the file pair is wiped if it fails to open.
- Field goal range counts wrap at 256.
- Open questions updated.

### cities.md

- 0x11: base wind in mph, rolled ±8 each game.
- Weather byte 8: temperature level A-G. Byte 9: base humidity (100 in rain).
- The header tables: temperature odds, degree ranges, heat index and wind chill (the last two unused).
- Rain beyond the first three odds; snow never.
- Stadium type 0 outdoor grass, 1 outdoor turf, 2 indoor turf.
- The city picker skips id 1.
- Open questions updated.

### formats/README.md

- `.tmn` is team news.
- `.pln` stock offsets point into the stock data file.
- Add `.trn`, `.pyc`, `.rst`, `.xxx`, the `.dft` header, `.DP`, `calender.dat`, `stpl.dat`, `.lgt`, the Pro Bowl `.LGE` and `tradelog.out` (section 9.8).

### No change

`pdb.md` and `schedule-import.md`: the source has nothing on them.

## 15. Other planned changes

- **[fbpro98-game-behavior.md](../fbpro98-game-behavior.md):**
  - add sections 2-5, 10.4, 11 and 12: potential boosts and key ratings; creation, camp, aging, retirement; injuries; computer teams; standings; draft order; season stages; awards; weather rolls;
  - healing by EN fills the rows the doc has not seen yet;
  - weeks out truncates 1.5 × EN first;
  - an existing injury level can grow in the source (engine use unknown);
  - the standings note: the source's quarter-win tie and tie-breaker list, against athc's half win and the manual's list.
- **Code comments:**
  - `fbpro98_profile/model.py`: drop "non-editable groups" and "the game's 80/90 default" (also in `profile/rules.py` and [fbpro98_profile.md](../fbpro98_profile.md)).
  - `fbpro98_gameplan/model.py`: the stock offset and size point into the stock play data file, not `STOCK98.MAP`.
- **Decoder `research/pnfl_decode.py`:**
  - T03: the head coach is 25 bytes, not "owner" (17 read).
  - T03: stop printing the password bytes (they sit inside `unknown_128_145`).
  - T03: name the NFL team id; 0xA1 is the draft profile, not "uniform".
  - R03: name `perm9` and `const60` (strategy ranks, rating weights).
  - Stats: name categories 12 and 14-16.
  - `.tmn`: team news.
  - Weight: read as the real data shows.
- **Other docs:**
  - [pnfl-formats.md](pnfl-formats.md): the `.dft` header is u8 count, u8 current pick, u8 round; `.tmn` is team news; the R03 and T03 unknowns are named.
  - The standings docs ([fbpro98_lge.md](../fbpro98_lge.md), [fbpro98_standings.md](../fbpro98_standings.md), [standings-tie-breakers.md](standings-tie-breakers.md)): revisit with ties and tie-breakers.
- **athc code differences to weigh** (none breaks the PNFL today):
  - Tie value: half a win, against the source's quarter.
  - Tie-breakers: the manual's list, against the source's.
  - The profile reader rejects specific-play codes (128+) and their count; the PNFL doesn't support profiles with plays.
  - The profile reader rejects weights 11-15; the game's screen limits weights to 0-10.
  - The profile reader rejects the PAT Stop Clock bit; no real profile has it.
  - The play and game plan readers reject category values not on athc's list; the game names any value.

## 16. Open questions

- Does the shipped game keep this logic (trade bugs, quarter-win ties, tie-breakers, awards)?
- How does the absent engine use ratings, fatigue, weather and home field?
- Are `.pyr` bytes 0x33-0x3B laid out as Formats.txt says?
- PNFL's `.tmn` entries read as retirements, yet most are still rostered; check against last off-season.
- Who hosts the final in real seasons? The source says conference 1's division winner; game-behavior says the higher seed, from 2043-2048.
- Award weights (`awardval.hxx` is missing).
- Is `getRandPercent` 1-100 (5% range boost) or 0-100?
