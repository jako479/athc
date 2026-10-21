# Proposal — stat corrections

Status: idea for later; nothing implemented.

## Why

The game engine records some stats wrong. athc should fix them in the league's stats file, `<league>.dat` (spec: [formats/stats.md](../formats/stats.md)).

## How

- No game history: the file keeps only running totals (last game, season, career), so a fix adds or subtracts an amount from each total; nothing can be recalculated from the games.
- Steps: back up the `.dat` and `.idx`, describe the fix (game, player or team, stat, change), apply the same change to every record that counted it, then write the changed records in place.
- Fixes update existing records; none are deleted.
- A fix that gives a player or a team a stat with no record yet (nothing in that category) needs a record inserted in the `.dat` and a matching entry added to the `.idx`. Teams too have no record for a zero stat: after week 16 of 2047 only 4 of the 18 teams have a season safeties record.
- The reader, `fbpro98_stats`, gives a missing record as `None`, so a fix can tell an insert from a change.
- Player vs team: a player fix also changes the team's totals and the other team's opponents' totals; a team-only stat (first downs, third and fourth downs, penalties, time of possession) touches only the team and opponents' records.
- Game vs season vs career: last-game records are deleted each week, so they matter only before the next week is played; season records last until the next season; career records are permanent. A regular-season fix touches all three; a playoff fix touches last game only.
- Special values: "long" is the longest play, so it can't simply be adjusted; field goal ranges pack made and attempts into one value.
- Applying the same fix twice doubles the change, so record which fixes were applied.

## Open questions

- Whether the game recalculates Hall of Fame points or awards from the stats.
- What the game does with an out-of-date `.idx` (an open question in the spec).
