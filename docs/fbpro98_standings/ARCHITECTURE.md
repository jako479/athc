# fbpro98-standings — Architecture

Library that ranks a league's teams from its `.lge` files by one of three tie-break methods.

## Module layout

```
src/athc/fbpro98_standings/
├── __init__.py    # public API: Standings, Method, StandingsError
├── standings.py   # Standings; _Ranker, the one ranking engine
├── methods.py     # each method's steps for division, conference and league standings
├── steps.py       # one function per tie-break step
├── moves.py       # match the previous season's teams to the current season's
├── season.py      # one LgeFile as numbered teams, games and playoff rounds
└── errors.py      # StandingsError
```

## What this package does

- Ranks from the games in the file (regular season for records, playoffs for the playoff round), never from the records the file stores. Exact arithmetic (`Fraction`).
- One engine for every method: sort by the method's first steps, then break each level group with its tie-breakers; teams level after every step get a coin toss.
- Game: the manual's list (head-to-head, division record, conference record, net points in division games, net points in all games, strength of schedule with each opponent once); conference standings put division winners first; league standings are the draft order reversed (champion, Super Bowl loser, then record and strength of schedule).
- Scheduler: division standings by the game's list; league standings by playoff round, record, strength of schedule (every game), division finish, point differential; conference standings in league order.
- NFL: the NFL's division, wild-card and draft-order steps; one team advances at a time, and teams of different divisions go on only as each division's best.
- With the previous season's file: ranks last season as played, under its own divisions, and answers with the current file's teams; teams match by name plus the team moves.

## What this package does NOT do

- Read files; the caller passes `LgeFile` objects from `fbpro98_lge`.
- Net touchdowns: not in the file, so that step is skipped.
- Know a league's team moves; the caller passes them.

## Testing

- `tests/unit/fbpro98_standings/`: each step on built leagues, each method on built leagues and the PNFL's real files, two seasons, every error. Matrix: [tests/unit/fbpro98_standings/README.md](../../tests/unit/fbpro98_standings/README.md).
