# fbpro98_lg2: read stock leagues — design

Date: 2026-10-09. Status: requested by the user ("support stock leagues at
the library level, no questions tonight"); choices below were made unattended,
then reviewed by the user on 2026-10-11: keep `league_type`, `check-ppp` fails
on stock leagues, the trailer stays unread.

## Goal

`fbpro98_lg2` reads all three `.lg2` layouts in
[lg2.md](../../fbpro98_lg2/specs/lg2.md): custom, modern stock, old stock.

## Decisions

- Stock leagues are read, not rejected; `UnsupportedLg2Error` is removed.
- One parser for all three; the layouts differ only in the folder field.
  - modern stock: `STOCK\BILLSO1.PRF`;
  - old stock: empty folder, so just `OFF1.PRF`.
- The model says which layout it read: new `LeagueType` enum (`CUSTOM`,
  `MODERN_STOCK`, `OLD_STOCK`) and `Lg2File.league_type`, like
  `Profile.profile_type`.
- Same rule as before, now a label instead of an error: the first entry's
  folder field decides (modern: starts with `STOCK\0A\FBPRO97\STOCK\0`; old:
  starts with NUL; anything else custom).
- Checks: size, then fields; stock leagues get the same field checks.
- `check-ppp` still fails on a stock league, now by checking `league_type`
  itself: one message for every kind, `stock league not supported`, exit 2.
- The 9-byte team trailer stays ignored (not part of this request).

## Tests

- Unit: both stock fixtures read (type, team count, files); first-entry rule
  on built bytes; stock leagues still get size and field errors.
- Integration: `check-ppp` fails on a modern and an old stock `.lg2`.

## Docs

Library README and ARCHITECTURE, test READMEs, STATUS, CHANGELOG, WORKLOG.
