# Standings tie-breakers

How each set of rules orders teams that finish level: what each source says, side by side. The Scheduler column is how generate-schedule ranks the season just finished, to build the next season's schedule. What the standings library implements for each method: [fbpro98_standings/ARCHITECTURE.md](../../fbpro98_standings/ARCHITECTURE.md).

## Sources

- **Game**: the FbPro98 manual, "Post-Season Play" tie-breakers (page 129) and the draft (page 136); see [fbpro98-game-behavior.md](../fbpro98-game-behavior.md#tie-breakers).
- **NFL**: [NFL Tiebreaking Procedures](https://www.nfl.com/standings/tie-breaking-procedures) (division, wild card, draft order).
- **PNFL.biz**: the header comments of the release `config/release/leagues/PNFL/standings/<season>.league.ini` files (2045-2049, removed in `dade898`). pnfl.biz has no final 1-18 list; each file's overall standings were derived from the next season's draft order. The 2048 file was built by the user, 2045-2047 by an earlier session.
- **Scheduler**: `scheduler/league_files.py`, `scheduler/domain/league.py`, `fbpro98_lge/standings.py`.

W-L-T % counts a tie as half a win in every column.

## Overall standings

The 1-18 finish, best first. The game and the NFL publish no such list; their draft order, reversed, is the nearest.

| Step | Game | NFL | PNFL.biz | Scheduler |
| ---: | :--- | :--- | :--- | :--- |
| 1 | Champion first, Super Bowl loser second; other playoff rounds ignored | Playoff round reached: Super Bowl winner, Super Bowl loser, conference final losers, divisional losers, wild-card losers, then the rest | Playoff round reached: Super Bowl winner, Super Bowl loser, conference final losers, wild-card losers, then the rest | Playoff round reached: champion, then the round each team went out in, then the rest |
| 2 | Regular-season W-L-T % | W-L-T % | Regular-season W-L-T % | Regular-season W-L-T % |
| 3 | Strength of schedule (division opponents counted once) | Strength of schedule, tougher ranks higher | Strength of schedule (opponents' records that season), tougher ranks higher | Strength of schedule (opponents' records, a team met twice counted twice), tougher ranks higher |
| 4 | Not stated | Division, conference or interconference tie-breakers, ending in a coin toss | Division finish | Point differential |
| 5 | | | | League-file order |

## Conference standings

| Step | Game | NFL | PNFL.biz | Scheduler |
| ---: | :--- | :--- | :--- | :--- |
| Basis | Playoff seeds and wild cards; one list for every tie | Seeds and wild cards; same-division ties use the division steps; with 3+ clubs, only each division's top club goes on | The conference's teams, in the order the [overall standings](#overall-standings) steps rank them | The conference's teams, in the order the [overall standings](#overall-standings) steps rank them |
| 1 | W-L-T % | W-L-T % | | |
| 2 | Head-to-head | Head-to-head (3+ clubs: only a clean sweep) | | |
| 3 | Division W-L-T % | Conference record | | |
| 4 | Conference W-L-T % | Common games (at least four) | | |
| 5 | Net points in division games | Strength of victory | | |
| 6 | Net points in all games | Strength of schedule | | |
| 7 | Strength of schedule (division opponents counted once) | Combined conference ranking, points scored and allowed | | |
| 8 | Net touchdowns | Combined league ranking, points scored and allowed | | |
| 9 | Coin toss | Net points in conference games | | |
| 10 | | Net points in all games | | |
| 11 | | Net touchdowns | | |
| 12 | | Coin toss | | |

## Divisional standings

| Step | Game | NFL | PNFL.biz | Scheduler |
| ---: | :--- | :--- | :--- | :--- |
| Basis | Season-end standings (in season the standings screen sorts ties by points for) | Division standings | Regular-season division finish from pnfl.biz's standings; no rule stated | Regular-season division standings of the season just finished |
| 1 | W-L-T % | W-L-T % | | W-L-T % |
| 2 | Head-to-head | Head-to-head | | Head-to-head |
| 3 | Division W-L-T % | Division record | | Division W-L-T % |
| 4 | Conference W-L-T % | Common games | | Conference W-L-T % |
| 5 | Net points in division games | Conference record | | Net points in division games |
| 6 | Net points in all games | Strength of victory | | Net points in all games |
| 7 | Strength of schedule (division opponents counted once) | Strength of schedule | | Strength of schedule (each opponent once) |
| 8 | Net touchdowns | Combined conference ranking, points scored and allowed | | League-file order (net touchdowns are not in the league file) |
| 9 | Coin toss | Combined league ranking, points scored and allowed | | |
| 10 | | Net points in common games | | |
| 11 | | Net points in all games | | |
| 12 | | Net touchdowns | | |
| 13 | | Coin toss | | |

When a step splits a level group: the NFL advances one club and starts the rest over; the scheduler ranks each part again from step 2; the manual does not say.

## Teams that moved to another division

How a division whose teams changed gets its order from the season just finished.

| Game | NFL | PNFL.biz | Scheduler |
| :--- | :--- | :--- | :--- |
| Not covered | Not covered | Division finish of the season just finished, mapped to the new divisions; no rule stated | The teams now in the division, ranked by the divisional steps on the season just finished; division and conference records come from the divisions those games were played in |

Example (scheduler, 2047 AFC East): Miami (as Houston) and Jacksonville came over from the West; their division records are their games against their old West rivals.
