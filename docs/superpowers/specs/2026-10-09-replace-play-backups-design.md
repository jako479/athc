# replace-play backup replacements — design

Status: talked through on 2026-10-08; built unattended on 2026-10-09 from that
discussion; on 2026-10-11 the user ruled that a replacement is used only if
the plan then passes `check`.

## Goal

`replace-play` takes a list of replacement plays. In each game plan it uses
the first one that is not already in the plan and with which the plan passes
`check`.

## Command line

`athc gameplan replace-play [-h] [-r] [--league name] play replacement... [path]`

- The first name is the play to replace (one play, as today).
- Then one or more replacements, tried in the order given.
- The last argument is the path when it is an existing file or folder,
  contains `\` or `/`, ends in `.pln`, or is a wildcard; otherwise it is a
  replacement and the path is the current folder.
- Fewer than two names (the play and one replacement) is a usage error, 2.
- Every replacement must be in the play pool, checked up front:
  `FAIL replacement play 'X' not found in the play pool`, 2 (as today).

## Per game plan

1. The plan without the play: unchanged and, in a folder, silent (as today).
2. Each replacement, in order:
   - Already in the plan (a normal or custom special slot, other than the
     play's own): `SKIP <file>: 'NEW' already in the gameplan`.
   - Swapped in memory. The model refusing it (wrong side, wrong special
     category) fails the file as today: `FAIL <file>: <why>`, 2.
   - Checked. When the plan would fail `check`: `SKIP <file>: 'NEW' fails
     check: [cat] message` (the `check` text), one line per violation; the
     next replacement is tried.
   - Otherwise the file is written and the `OK` line is printed as today.
3. None fits: `<file>: 'OLD' not replaced, no valid replacement`, a finding;
   the file is left untouched.

A swap that fixes what made the plan fail is used. A play in several slots
becomes a duplicate, which fails `check`, so it is never replaced.

## Rules and pool

- Rules: the league's game plan rules, as `check` reads them. With none
  configured, no league rule is checked; "already in the gameplan" and
  `check`'s built-in checks (duplicates, plays not in the pool) still apply.
- Pool: built with the league's `playpool.toml`, as `check` does, so the
  rollout, QB draw, timed and 2-DL attributes the rules cap are known. Its
  `WARN` lines show as in `check`.

## Output and exit codes

- Every existing message stays as it is.
- Folder tally: `'OLD' -> 'NEW1', 'NEW2': replaced <n> instance(s) in <m>
  gameplan(s), <f> failed, <k> not replaced`.
- Exit 2 when any file failed; else 1 when nothing was replaced anywhere or
  any plan had no valid replacement; else 0.

## Out of scope

- The message rewording talked about (one line per file, short reasons, no
  category in parentheses).
- A list of play/replacement pairs (the TODO item).

## Testing

- Argument split: one name (usage error), two names, the last argument as a
  folder, a file, a `\` / `/` name, a `.pln` name, a wildcard, a plain name;
  a folder named like a play counts as the folder.
- Picking: first replacement already in the plan, first breaking a rule,
  all skipped, a plan still failing after the swap, a swap that fixes the
  plan, the play replaced by itself.
- Command: path left out (current folder), backups across a folder, the
  not-replaced line and tally, exit codes. Existing tests stay as they are,
  except the three that pin the old command line (the path required, a
  single replacement, the `play replacement path` usage text), which now test
  the new one.
