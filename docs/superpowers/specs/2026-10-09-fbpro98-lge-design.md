# fbpro98_lge: read conference, division and team names from a league's .lge — design

Date: 2026-10-09. Status: written unattended on the user's go-ahead; awaiting review.

## Goal

A read-only library that returns a league's conference names, each
conference's division names, and each division's team names: team name
("Denver"), nickname ("Broncos") and official name ("Denver Broncos"). The
format is in [docs/fbpro98_lge/specs/lge.md](../../fbpro98_lge/specs/lge.md).

## Current state (branch `worktree-fbpro98-lge`, on main 7b5bdab)

- `fbpro98_lg2` is the model: `model.py`, `schema.py`, `reader.py`,
  `read_lg2(league, league_dir)` / `parse_lg2(buffer, path)`, an
  `InvalidLg2Error(AthcError)`, frozen slotted dataclasses, ASCII decoding with
  `errors="replace"`, no logging.
- The `.lge` spec is committed. `research/pnfl_decode.py` walks the chunks and
  unmasks team chunks. No library exists.
- Every sample in `E:\SIERRA\FbPro98` has the spec's layout: 8, 10 and 12
  teams (one conference), 18 (stock and PNFL), 28 (NFLPA92-94) and 30
  (NFLPI95-97). Fourteen nest the chunks; five (`_default`, `Sierra`,
  `NFLPA93E`, `NFLPA94E`, `NFLPI95E`) group them by kind (found in review).

## Decisions

From the request:

- Name `fbpro98_lge`; reading only; conferences, divisions and teams only.
- Every league size; PNFL.lge is the 18-team fixture.
- Team chunks are unmasked while reading.

Taken unattended, each the obvious default:

- Same shape as `fbpro98_lg2`: `read_lge(league, league_dir)` reads
  `<league_dir>/<league>.lge`; `parse_lge(buffer, path="<buffer>")`.
- Nested model in file order, the way the game writes the tree.
- Team field names follow the game's Team Settings labels: `name` ("Team
  Name"), `nickname`; `official_name` is a property, the two joined by a space
  (just the one present when the other is empty).
- A name is the text up to its NUL, or the whole field when it has none (the
  spec notes a 17-character stadium name with no NUL).
- Empty names are returned as `""` (PNFL's conference names are empty).
- Stock leagues are read; no unsupported-league error.

## API and model

```python
from athc.fbpro98_lge import read_lge

lge = read_lge("PNFL", r"E:\SIERRA\FbPro98")
lge.conferences[0].name                          # ""
lge.conferences[0].divisions[1].name             # "West"
team = lge.conferences[0].divisions[1].teams[0]
team.name, team.nickname, team.official_name     # "Denver", "Broncos", "Denver Broncos"
```

- `LgeFile(conferences: tuple[Conference, ...])`
- `Conference(name: str, divisions: tuple[Division, ...])`
- `Division(name: str, teams: tuple[Team, ...])`
- `Team(name: str, nickname: str)`, property `official_name`

## Modules

```
src/athc/fbpro98_lge/
├── __init__.py    # public API re-exports
├── model.py       # LgeFile, Conference, Division, Team
├── schema.py      # chunk tags, sizes, field offsets, mask factor
└── reader.py      # read_lge / parse_lge; InvalidLgeError
```

## Checks

The reader walks the chunks in file order and raises `InvalidLgeError` at the
first problem:

- empty file;
- a chunk header cut short, or a chunk running past the end of the file;
- a chunk other than the one the tree expects next: L03, then per conference
  C03, per division D03, per team T03 then R03, then S03; or, when the first
  T03 is followed by another T03, every C03, D03, T03 and R03 in turn;
- a chunk of the wrong size: L03 89 + conferences, C03 29 + divisions,
  D03 29 + teams, T03 171, R03 325;
- data after the S03 chunk.

Not read: L03 fields other than the conference count, the conference, division
and team ids, rosters and the schedule. No logging.

## Tests

`tests/unit/fbpro98_lge/`, fixtures in `data/` copied from `E:\SIERRA\FbPro98`:
`PNFL.lge` (18), `08_TEAMS.lge`, `10_TEAMS.LGE`, `12_TEAMS.LGE`, `NFLPA94.lge`
(28), `NFLPI97R.LGE` (30); grouped: `NFLPA93E.LGE` (28), `_default.lge` (30).

- Each fixture: conference, division and team counts; names spot-checked,
  including leftover text after a NUL.
- Model: nesting, `official_name` with either part empty, frozen.
- Built bytes for every check above, each size at the limit and one past it.

## Docs

- New `docs/fbpro98_lge/README.md` and `ARCHITECTURE.md`, like `fbpro98_lg2`.
- New `tests/unit/fbpro98_lge/README.md` test matrix.
- `lge.md` owner line; `docs/design/architecture.md` and `fbpro98-files.md`
  library lists; `STATUS.md`, `CHANGELOG.md`.

## Out of scope

- Writing `.lge` files; every other field; rosters; the schedule.
- Any command that uses the library.
