# Error wording — design

Date: 2026-10-09. Follows the console, run log and exit-codes work (`7b5bdab`).

## Goal

Every `FAIL` and `WARN` line reads the way Windows command-line tools word their
errors, names the file to blame once, and fits on one line.

Out of scope: findings and other result lines, `OK` / `SKIP` lines, tallies,
the labels, exit codes, Click's own usage text, run-log-only lines.

## Research

- Windows tools (`type`, `copy`, `cd`, `robocopy`, `certutil`, PowerShell),
  captured on this machine: full sentences, capital first letter, trailing
  period. Missing file: `The system cannot find the file specified.` Missing
  folder: `The system cannot find the path specified.` Folder given for a file:
  `Access is denied.` File given for a folder: `The directory name is invalid.`
- End-user Python tools (yt-dlp, gallery-dl, streamlink, OCRmyPDF, beets,
  internetarchive, instaloader, calibre): capital first letter; lists joined
  with `, `, no Python brackets.
- Python on Windows gives one problem two texts depending on the call
  (`open` → `No such file or directory`, `os.stat` → `The system cannot find
  the file specified`), and opening a folder raises `Permission denied`.

## Rules

1. **Shape.** `<path>: <Sentence.>`; a line in a file is
   `<path>: line N: <Sentence.>`; no path when no single file is to blame.
   Location prefixes (`<path>:`, `line N:`, `[section] key:`, `[table]:`) come
   first; the sentence after the last one starts with a capital.
2. **Style.** Capital first letter, exactly one trailing period. A hint is a
   second sentence on the same line. Text embedded from elsewhere (a parser, a
   model `ValueError`, an inner error) loses its own trailing period; the line
   gets one. Names, keys, quotes and command names keep their own case, so a
   key never starts the sentence; it joins the location instead
   (`[x].mandatory: Must be a list.`).
3. **File-system phrases.** Windows' own words, fixed English text:

   | Problem | Phrase |
   |---|---|
   | Missing file | `The system cannot find the file specified.` |
   | Missing folder, or a folder on the way | `The system cannot find the path specified.` |
   | No access, or a folder given for a file | `Access is denied.` |
   | A file given for a folder | `The directory name is invalid.` |
   | Name already taken | `Cannot create a file when that file already exists.` |
   | An error with no text | `Unspecified error.` |
   | Anything else | Windows' own text (`strerror`), styled by rule 2 |

4. **One line per problem.** Nothing prints across lines; several problems are
   several labeled lines.
5. **Plain values.** Lists read `A, B, C`; bytes read as hex (`0x07`); no
   Python `['…']`, `b'…'`, dict or dataclass reprs; no Markdown backticks.
6. **Same problem, same words.** TOML parse errors:
   `Not valid TOML: <parser text>.` INI parse errors:
   `Not valid INI: <reason> (at line N).` A table that is not one:
   `<where>: Must be a table.` Unknown keys, one line per table:
   `<where>: Unknown key(s): a, b. Valid: x, y.` (`(top)` for top-level
   keys).
7. **Click usage errors.** Click's frame stays. Inside its `Invalid value
   for` sentence athc's part continues it, so it starts lowercase
   (`Error: Invalid value for 'pdb_file': must have a .pdb extension.`); a
   bare usage error is its own sentence and starts with a capital
   (`Error: Path must be a .pln file or a directory; …`).

## File-system errors (item 1, item 4b)

One helper module, `athc/errors.py`:

- `reason_of(error)` returns the rule-3 phrase for an `OSError`:

  | Error | Phrase |
  |---|---|
  | Windows code 2 | missing file |
  | Windows code 3 | missing folder |
  | Windows code 5 | access denied |
  | Windows code 267 | directory name invalid |
  | Windows code 183 | name taken |
  | No Windows code, `ENOENT` | missing folder when the parent folder is missing, else missing file |
  | `EACCES`, `EISDIR` | access denied |
  | `ENOTDIR` | directory name invalid |
  | `EEXIST` | name taken |
  | Anything else | `strerror` (or `str(error)`), styled by rule 2 |

- `missing_reason(path)`: the missing-folder phrase when the parent folder is
  missing, else the missing-file phrase. For athc's own checks.
- `error_line(error)`: an `AthcError` gives `str(error)`; an `OSError` gives
  `<filename>: <reason_of>`, or the phrase alone when it has no file name.

Used by:

- The one place (`cli/__init__.py`), the log-folder check, every batch loop
  (`find-play`, `replace-play`, `set-specials`, `gameplan check`,
  `profile check`, `profile copy`, check-ppp's pair loop and its per-file read
  lines), the play pool's unreadable-file warning, autocontinue's reload
  warning.
- autocontinue's screen-grab warning names its likely causes instead
  (`The screen is locked, a screensaver is on, or Remote Desktop is
  disconnected. Retrying in 60 seconds.`); the button image loads once at
  start, and a missing or unreadable one is `FAIL <image>: <why> Reinstall
  athc.`, exit 2.
- athc's own path checks, so a problem reads the same whether athc finds it
  first or Windows reports it:
  - `named_file`: missing → `missing_reason`; a folder → `Access is denied.`
    (this is convert-pdb's 4b fix, and every other one-file command's).
  - `collect_files`: missing → `missing_reason`.
  - Folder checks (`playpool check`, check-ppp's directory argument): missing →
    missing-folder phrase; a file → `The directory name is invalid.`
  - Play path (`gameplan` `build_pool` and convert-pdb's twin, now one
    wording): `<play path>: <missing-folder or directory-invalid phrase> Set
    play_path in <league.toml path>.`

## Multi-line errors (item 2)

- `console.fail` and `console.warn` print each line of a message as its own
  labeled line and its own run-log entry. The one place and every loop print
  through them, so nothing is ever unlabeled.
- `RulesFileError` with several problems: one `FAIL <rules file>: <problem>`
  per problem (gameplan, profile, play-pool rules).
- Missing standings file, one line: `<path>: The system cannot find the file
  specified. Add the <league> season <n> standings file.`
- autocontinue with no section, one line: `<athc.ini>: No [autocontinue]
  section. Add one, or set ATHC_CONFIG_DIR.`
- `InvalidPlayListError` text becomes one line (`<n> invalid play(s).`);
  its `violations` are printed one per line as now.

## Wordings (item 3)

- Play lists (`set-normals`, `set-specials`): `<list file>: line N: <Sentence.>`;
  from the console, `line N: <Sentence.>`. N is the line in the file, counting
  blank and `::` lines (today it counts plays only).
- `set-specials` per-gameplan problems name the gameplan and put the list line
  last: `<x.pln>: <Sentence> (<list file> line N).`; from the console,
  `(play list line N)`.
- `input has N play(s), max is M` → `<list file>: Too many plays (N). The most
  is M.`
- athc.ini value errors name athc.ini: autocontinue's
  (`<athc.ini>: [autocontinue] <key>: Must be true or false, got 'x'.`,
  `… Must be a number, got 'x'.`, `<athc.ini>: Missing required setting
  '<key>' in [autocontinue].`) and convert-pdb's booleans
  (`<athc.ini>: [convert-pdb] <key>: Must be true or false (yes/no, on/off and
  1/0 also work), got 'x'.`).

## The sweep

Everything else that breaks a rule, by group. Mechanical changes (capital,
period, plain lists) apply to every message in the group; the rest is listed.

| Group | Changes |
|---|---|
| Console | `interrupted` → `Interrupted.`; `<what>: unexpected error (see log: <path>)` → `<what>: Unexpected error. See <log path> for details.` |
| File collector | `No .pln files match.`, `No .pln files.`, `Not a .pln file.` (capital, period) |
| check-ppp | `Second .prf file. Pass one profile and one gameplan.`; `Not a .prf or .pln file.`; `Profile is offense but gameplan is defense.`; the no-pairs warning gets capital and period |
| Missing league settings (check-ppp, playpool check, gameplan, convert-pdb) | `<league.toml>: No play_path for the league. Set play_path in this file.` (and `path` the same way) |
| Dependencies | `missing ortools -- reinstall athc` → `Missing ortools. Reinstall athc.` (and pyautogui) |
| Click usage errors (`convert-pdb`, `config set`, `profile diff`, `profile copy`, `find-play`) | period added; `config set`'s league error starts lowercase inside Click's frame; `known keys:` becomes a second sentence |
| League selection | `League 'x' not found. No folder <path>. Available: a, b.`; `No league selected. Run 'athc config set league NAME' or pass --league.` |
| No rules | `No rules configured. Add profile.toml to the league folder.` (and gameplan.toml) |
| Type mismatch (`profile copy`, `profile diff`) | names both profiles: `<target>: Cannot copy from <source> (offense) to a defense profile.`; `Cannot compare <a> (offense) with <b> (defense).` |
| `replace-play` | `Replacement play 'x' not found in the play pool.` |
| Config readers (athc.ini, league.toml, labels) | capital after the location, period; parse errors by rule 6 |
| Rules files (gameplan, profile, play pool) | capital after the location, period; `Valid:` lists plain; backticks dropped; `must be a table` and unknown keys by rule 6; `(expected [...])` → ` Valid: a, b.` |
| Play pool warnings | path first: `<path>: Offensive play in the defense tree.`, `<path>: <Category> play in a <category> folder.`, `<path>: <reason> Skipped.` (invalid or unreadable file); rule warnings name the rules file by full path and become two sentences (`… exclude. Exclude wins.`, `… play. It has no effect.`) |
| Binary readers (`.ply`, `.pln`, `.prf`, `.lg2`, gameplan and profile models) | period added; bytes reprs → hex |
| convert-pdb | pdbtoexcel.toml errors by the rules above; `<pdb>: Invalid play data at 0x…. Skipped.` (and tendency data) names the PDB; `<pdbtoexcel.toml>: 'x' is listed in [deleted_plays] but is in the play pool. Its stats are skipped.`; `Play 'x' has no play file in the play pool.`; workbook write errors through `reason_of` |
| Scheduler | scheduler.toml and standings errors by the rules above; cross-checks name scheduler.toml; domain and solver texts: capital, period, plain lists |

## Tests

- Tests are changed first: each changed message's pinned text is updated to the
  approved wording and seen to fail, then the code changes. The conftest helpers
  (`no_league_selected`, `league_not_found`, `no_rules_configured`,
  `toml_error`, `os_error`) carry the shared lines.
- `reason_of`: one test per row of its table, missing file vs missing folder,
  an unknown error keeping Windows' text plus a period, `error_line` with and
  without a file name.
- `named_file`, `collect_files`, folder checks, play path: missing file,
  missing folder on the way, folder for a file, file for a folder.
- Multi-line: a rules file with several problems gives several `FAIL` lines
  and several log entries; a stray line break gets its own label.
- Play lists: blank and `::` lines before a bad play give the right line
  number, from a file and from the console.

## Docs

- `docs/design/architecture.md`, "Console, run log and errors": the rules and
  the helper.
- Each tool's README: its new lines.
- Release docs: any message they quote.
- CHANGELOG, STATUS, WORKLOG.
