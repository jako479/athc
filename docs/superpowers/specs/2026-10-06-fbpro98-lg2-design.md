# fbpro98_lg2: read each team's profile and game plan files from a league's .lg2 — design

Date: 2026-10-06. Status: approved by the user; implemented.

## Goal

A read-only library that returns, for every team in a custom league's `.lg2`,
the eight profile and game plan files the team uses. Stock leagues are
recognized and rejected. The format is in
[docs/fbpro98_lg2/specs/lg2.md](../../fbpro98_lg2/specs/lg2.md).

## Current state (branch `worktree-fbpro98-lg2`, on main 1cdc2bd)

- Three Front Page Sports Football Pro '98 libraries exist: `fbpro98_play`,
  `fbpro98_gameplan`, `fbpro98_profile`. Each has `model.py`, `schema.py`,
  `reader.py` (plus `writer.py` for gameplan and profile), exports
  `read_x(path)` / `parse_x(buffer, path)`, raises `Invalid…Error`
  (profile also `UnsupportedProfileError`), never logs, and doesn't know its
  file extension.
- The `.lg2` format spec is committed (4890607). No code exists.

## Decisions (the user's)

- Name: `fbpro98_lg2`, after the extension, since a league spans several files.
- Reading only; no writer.
- No game folder setting in `athc.ini` yet; it comes with the first command
  that needs it.
- Model is nested pairs, so each profile stays with its game plan.
- A file's location is one string, `folder\filename`, like the gameplan
  library's play filenames; callers split it with `PureWindowsPath`.
- Stock leagues raise `UnsupportedLg2Error`, judged by the first entry only:
  - modern stock: the folder field starts with exactly
    `STOCK\0A\FBPRO97\STOCK\0` (true of every entry in all four modern samples);
  - old stock: the folder field starts with a NUL (empty folder).
- Fixtures: `PNFL.lg2` (custom), `NFLPI97.LG2` (modern stock), `08_TEAMS.LG2`
  (old stock), copied from `E:\SIERRA\FbPro98\`.

## API and model

```python
from athc.fbpro98_lg2 import read_lg2

lg2 = read_lg2(r"E:\SIERRA\FbPro98\PNFL.lg2")
lg2.teams                          # tuple of TeamFiles, in file order
team.first_half.offense.profile    # "PNFL\\2049\\Plans\\Denver (Brian)\\DEN-OFF1.prf"
team.second_half.defense.gameplan
```

- `Lg2File(teams: tuple[TeamFiles, ...])`
- `TeamFiles(first_half: HalfFiles, second_half: HalfFiles)`
- `HalfFiles(offense: FilePair, defense: FilePair)`
- `FilePair(profile: str, gameplan: str)`
- `read_lg2(path)` reads from disk; `parse_lg2(buffer, path="<buffer>")`
  parses bytes, `path` used only in error messages.
- All model classes are frozen, slotted dataclasses.
- Strings are decoded as ASCII with `errors="replace"`, like the gameplan
  reader. A location is `folder\filename`, or just `filename` when the folder
  is empty.

## Modules

```
src/athc/fbpro98_lg2/
├── __init__.py    # public API re-exports
├── model.py       # Lg2File, TeamFiles, HalfFiles, FilePair
├── schema.py      # record sizes, field offsets, stock signatures
└── reader.py      # read_lg2 / parse_lg2; InvalidLg2Error, UnsupportedLg2Error
```

## Checks

In this order:

1. `InvalidLg2Error` if the size is zero or not a whole number of 4,193-byte
   team records.
2. `UnsupportedLg2Error` if the first entry's folder field matches a stock
   signature (above).
3. `InvalidLg2Error` if any folder or filename field has no NUL, or any
   filename is empty.

Ignored: text after each NUL, and the 9 unknown bytes that end each team
record. Messages end with `in {path}`, like the other libraries. No logging.

## Tests

`tests/unit/fbpro98_lg2/`, fixtures in `data/`:

- `PNFL.lg2` reads 18 teams; locations spot-checked, including one whose
  folder has leftover text after its NUL.
- `NFLPI97.LG2` and `08_TEAMS.LG2` raise `UnsupportedLg2Error`.
- A stock signature on a later entry is read, not rejected.
- A first-entry folder of `STOCK` with other leftover text is read as custom.
- Model: building each class and nesting.
- Limits, on built bytes:
  - size: 0, 4,192 and 4,194 bytes rejected; 4,193 accepted;
  - folder: 260 characters plus NUL accepted; 261 with no NUL rejected;
  - filename: 261 characters plus NUL accepted; 262 with no NUL rejected;
  - filename length: 1 accepted; 0 (empty) rejected.

## Docs

- New `docs/fbpro98_lg2/README.md` and `ARCHITECTURE.md`, modeled on
  `fbpro98_profile`.
- `lg2.md`: add a reader contract and a validation and test vectors section,
  like `ply.md`.
- New `tests/unit/fbpro98_lg2/README.md`, like the other library test folders.
- Update `docs/design/overview.md`, `STATUS.md`, `CHANGELOG.md`.

## Out of scope

- Writing `.lg2` files.
- Reading stock leagues.
- A game folder setting, or any command that uses this library.
- The 9 unknown bytes per team, and team order.
