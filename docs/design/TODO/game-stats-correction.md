# Proposal — game stats correction

Status: proposal; nothing implemented.

## Why

The game records some stats wrong, and athc should fix them in `<league>.dat`. [stat-corrections.md](stat-corrections.md) says what to fix; [stats-library.md](stats-library.md) adds the writer. This doc lays out the library so the fixes have a home.

## Layout

- One package, `fbpro98_stats`, never two installable ones.
- Two subpackages inside it, side by side: `ctree/`, the database layer, and `stats/`, the football layer.
- `fbpro98_stats/__init__.py` exposes the football functions; subcommands never see `ctree`.

## The database layer, `ctree/`

- Knows bytes, offsets, record sizes and slots, and the `.dat` and `.idx` headers.
- Reads a record, writes one in place, inserts, deletes and grows the files, when told to.
- Knows nothing of players, teams or what a value means, and decides nothing.
- Changing a value in an existing record is a seek and an overwrite; the headers and the index stay as they are.

## The football layer, `stats/`

- Turns a record (id, stat type, eight 2-byte values) into named stats and back.
- Holds the game's rules: a player record carries only a player id and a team record only a team id, so the file never links a player to a team; and no all-zero record exists, a rule of the game, not of the database.
- Decides from those rules whether a change is an update, an insert or a delete, and tells `ctree` which.

## Two ways in

- Reading: the file is small, so a caller reads it all into memory and takes what it needs. For net touchdowns, `athc standings` builds a record per team (team id, touchdowns scored, touchdowns allowed) and passes the list to `fbpro98_standings`, which never sees the rest.
- Correcting: a function reads one player's or team's block, changes it and writes just that back; never read everything and write everything, which risks the whole file on a crash and writes back stale data.

## Corrections

- One function per game bug, named for it: `convert_run_to_sack(player_id, team_id, yards)`. The caller passes both ids because the file doesn't link them.
- A function that changes a player stat changes the team's matching stat in the same call, so the two never drift.
- A sack counted as a quarterback run: the quarterback's rushing record loses one attempt and gains the sack yards; the team's sacked record gains one sack and the same yards. A rushing record that goes all-zero is deleted; a missing sacked record is inserted; an existing one is updated.
