# Console, run log and exit codes

Status: design for the 1.0.0 TODO task. It describes the target, not the code.
When the task is done the rules move into
[architecture.md](../architecture.md#cross-cutting-conventions) and this file
goes. Per command and per library: [logging-by-command.md](logging-by-command.md).

## In one breath

- Results on stdout, everything else on stderr, and every status line also in
  a run log the user never has to open.
- One console helper (Rich) prints every line, one logging setup in `main()`
  writes the file, one error base class, one place turns errors into the exit
  code.
- The same exit codes in every command: 0 done, 1 findings, 2 error.

## What is mainstream (research of 2026-10-08)

The reference is Tamarack Habilitations' `pdf-converter` ("TH"). The table
says what the mainstream does, who does it, and whether TH matches.

| Concern | Mainstream | Who | TH |
|---|---|---|---|
| Console color | Rich | pip vendors it; Hatch, pdm, Typer and Textual use it. Click alone ignores `NO_COLOR`. | Rich. Match. |
| What is colored | Only the label word | cargo, ruff, yt-dlp, pre-commit | Prefix only. Match. |
| Color switch | On for a terminal, off when piped; `NO_COLOR` off, `FORCE_COLOR` on | no-color.org, force-color.org; Rich does all three | Rich. Match. |
| Run-log library | stdlib `logging` + `RotatingFileHandler` | pip, mkdocs; loguru and structlog are popular but absent from the mainstream CLIs | Match. |
| A log every run | Both exist: always (winget, npm, Chocolatey) or opt-in (pip, git, cargo) | | Always. Match. |
| Log content | The console's lines plus detail: a start line, tracebacks | npm, pip `--log`, Chocolatey | Match. |
| Streams | Results on stdout; messages, warnings, errors and progress on stderr | clig.dev; git, cargo, ruff, pip, Black | Match. |
| Progress | stderr, shown by default, no animation off a terminal | git, curl, ffmpeg, tqdm, pip, cargo | TH has no long runs. |
| Per-item status | A status word per item, then a tally | pytest PASSED/FAILED, pre-commit Passed/Failed, Ansible ok/failed | OK/SKIP/WARN/FAIL. Match. |
| Label case | Lowercase `warning:` / `error:` | git, cargo, ruff, npm, gcc, mypy; uppercase is the pip / yt-dlp minority | Uppercase words: the one minority choice. Kept, so both projects read the same. |
| A crash | One human line, traceback to the log, a batch goes on | Black, npm ("see log"), clig.dev | Match. |
| Library warnings | Returned as values | Fowler's notification pattern; the Logging HOWTO says libraries configure no handlers | Match. |
| Library progress | A callback, or `logging` INFO the app routes | OR-Tools `log_callback`, yt-dlp `progress_hooks`; Logging HOWTO | Not needed in TH. |
| Exit codes | One error code in every subcommand; a findings code only where a command reports findings; usage 2; warnings never change it; a crash is an error; the worst outcome wins in a batch; no hit is 1 for a search | git (128 / 1 / 129), ruff (2 / 1), grep, ripgrep, diff; argparse, Click, clap; gcc, eslint; rsync | 0 / 1 / usage 2, one command. Match. |

Verdict: TH is the mainstream pattern; athc adopts it whole, with these
additions TH never needed: a findings code, progress lines, a per-item catch
that keeps a batch going, and a progress callback for libraries.

## Libraries

- **Rich** for the console: one `Console` for stdout, one for stderr
  (`stderr=True`), both `soft_wrap=True`, `highlight=False`.
- **stdlib `logging`** for the run log, file only; no console handler, ever.
- **Click** stays for parsing. `click.echo`, `print()` and
  `logging.basicConfig` disappear from commands.
- **platformdirs** for the log folder, as it already is for the config folder.

## Pieces

| Piece | Module | Job |
|---|---|---|
| Console | `athc/console.py` | Prints every line, colors the prefix word, writes the matching log line. One module-level instance, used by every command. |
| Run log | `athc/log.py` | `setup_logging()`, called once in `main()`; rotating `athc.log`. |
| Errors | `athc/errors.py` | `AthcError`, the base of every expected error; the shared `ConfigFileError`, `LeagueError`, `RulesFileError`. Library errors subclass it. |
| `main()` | `athc/cli/__init__.py` | Runs Click in non-standalone mode; the one place that turns every error into a line, a log entry and an exit code. |

Tool packages and libraries never import the console or configure logging.

## Message kinds

| Kind | Call | Console line | Stream | Log |
|---|---|---|---|---|
| Result: the command's product (report lines, lists, a diff) | `console.print(text)` | plain | stdout | no |
| One item done | `console.ok(msg)` | `OK   msg` | stdout | INFO |
| One item skipped on purpose | `console.skip(msg)` | `SKIP msg` | stdout | INFO |
| Tally, or one line per item that had findings | `console.result(msg)` | plain | stdout | INFO |
| Progress of a long run | `console.progress(msg)` | plain | stderr | INFO |
| Warning: noted, nothing failed | `console.warn(msg)` | `WARN msg` | stderr | WARNING |
| Failure: one item, or the run | `console.fail(msg)` | `FAIL msg` | stderr | ERROR |
| Bug | `console.unexpected(what)` | `FAIL what: unexpected error (see log: <path>)` | stderr | ERROR with traceback |

Rules:

- Only those four words are labels. No `athc <command>:` prefix, no
  timestamps, no `INFO:` on the console.
- A line about a file starts with its path: `OK   x.pln: updated (3 special
  plays)`, `FAIL x.pln: not a .pln file`.
- Findings (violations, play-pool issues, differences, a play not found) are
  results: a one-line headline per file through `result`, so the log holds
  one line per file, then the detail lines through `print`.
- A command that takes a directory ends with a tally through `result`; a
  single-file command does not.
- The console writes each log line itself, so nothing is written twice and no
  command touches `logging`.
- The log, not the console, gets a start line (`athc <version> <args>`) and an
  end line (`exit <code>`).

## Color

- Rich decides: color on a terminal, none when piped or redirected to a file.
- `NO_COLOR` set to anything non-empty turns color off; `FORCE_COLOR` turns it
  on. No athc option, no config key.
- Green `OK`, cyan `SKIP`, yellow `WARN`, red `FAIL`. Only the word.
- `soft_wrap=True` and `highlight=False`: a line is never wrapped, and numbers
  or paths are never restyled, so `2> err.log` holds whole plain lines.

## Run log

- `%LOCALAPPDATA%\athc\Logs\athc.log` (`platformdirs.user_log_dir("athc",
  appauthor=False)`), 1 MB x 5 files, UTF-8, `time LEVEL message`. The folder
  is created on first use.
- One file for every command.
- Every run writes: the start line, every OK / SKIP / result / progress / WARN
  / FAIL line, every traceback, the end line. Results are never logged.
- Set up once in `main()` before Click runs. The `athc` logger does not
  propagate, so nothing from `logging` reaches the console.
- No log option, no level option.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Done. Clean, or warnings only. |
| 1 | Findings: ran fine and reported problems in valid input (violations, play-pool issues, differences, play not found). Only the checker and finder commands ever use it. |
| 2 | Error: could not do the job. Usage, config, league, a missing or bad input, a file that failed inside a batch, a missing dependency, a bug. |
| 130 | Ctrl-C. |

Rules:

- The same numbers in every command, so a script treats 2 as "athc could not
  do it" everywhere.
- A batch processes every item, then exits with the worst outcome: error beats
  findings beats clean.
- Warnings never change the code.
- A bug is an error, not a special code; the log holds the traceback.
- Usage errors stay Click's: its `Usage: ... Error: ...` text on stderr, 2.
- `autocontinue` stops on Ctrl-C by design, so there it is 0.

## Situations

| Situation | Console | Log | Exit |
|---|---|---|---|
| Bad option or argument | Click's usage error, stderr | ERROR | 2 |
| Input file or path named on the command line does not exist | `FAIL <path>: not found` | ERROR | 2 |
| Named file is corrupt or not the expected type | `FAIL <path>: <reason>` | ERROR | 2 |
| No league selected, unknown league, bad `athc.ini` / `league.toml` / rules file | `FAIL <reason>` | ERROR | 2 |
| Missing dependency (ortools, pyautogui) | `FAIL missing <module> -- reinstall athc` | ERROR | 2 |
| Bug while processing a single named file | `FAIL <path>: unexpected error (see log: ...)` | ERROR + traceback | 2 |
| Bug on one file of a directory | same line; the batch goes on | same | 2 after the batch |
| One file of a directory cannot be read or updated, the rest are fine | `FAIL <path>: <reason>`; the batch goes on | ERROR | 2 after the batch |
| An output file cannot be written | `FAIL <path>: <reason>` | ERROR | 2 |
| Findings in valid input (violation, play-pool issue, difference, play not found) | headline per file, detail lines, tally; stdout | INFO, one line per file | 1 |
| A named game plan, profile or play file holds a category id the reader does not know | corrupt file: `FAIL` | ERROR | 2 |
| A rule or label names a category the league does not know | config: `FAIL` | ERROR | 2 |
| A `.ply` in the play pool that is misfiled, unreadable or invalid | play-pool finding | INFO | 1 from `playpool check`; `WARN` and 0 from any other command that loads the pool |
| Directory with no matching files | `WARN <dir>: no .pln files`; tally | WARNING | 0 (`find-play`: 1, nothing found) |
| `find-play`: no hit in any file | `not found` line per file, tally | INFO | 1 |
| `find-play`: a hit in at least one file | hit lines, tally | INFO | 0 |
| Warnings only (recoverable notices) | `WARN` lines, then the normal `OK` lines and tally | WARNING | 0 |
| A file skipped on purpose (wrong side, the source itself) | `SKIP <path>: <why>` | INFO | 0 |
| All clean, all updated | `OK` lines, tally | INFO | 0 |
| Findings in some files and a failure in another | all of the above | all of the above | 2: the worst outcome |
| Long run in progress | plain lines on stderr | INFO | - |
| Ctrl-C | `FAIL interrupted` | ERROR | 130 (`autocontinue`: 0) |
| Crash before any file is touched | `FAIL unexpected error (see log: ...)` | ERROR + traceback | 2 |

## Libraries and tool packages (the Click-free code)

- Never print, never import the console, never configure `logging`, never log.
- A failure raises an `AthcError` subclass. The message is the whole human
  text without the path; the command adds the path.
- Readers wrap every model `ValueError` in their own error, so a command never
  catches a bare `ValueError`.
- Warnings and findings come back as values with the result
  (`warnings: list[str]`, `issues`, `violations`).
- Live progress goes through an optional `progress: Callable[[str], None]`
  parameter; the command passes `console.progress`. A loop that cannot return
  its warnings (`autocontinue`) takes a `warn` callback the same way.

## Errors and the exit code, one place

`main()` calls `cli(standalone_mode=False)` and handles everything that comes
out:

| What came out | Console | Exit |
|---|---|---|
| A Click usage error | Click's own text (`e.show()`) | 2 |
| `Abort` (Ctrl-C) | `FAIL interrupted` | 130 |
| `AthcError` or `OSError` | `FAIL <message>` | 2 |
| Any other exception | `unexpected` line, traceback to the log | 2 |
| A normal return | nothing more | the command's code |

A command: lets a startup problem (config, league, rules, the one named file)
propagate; uses `ctx.exit(1)` for findings; inside a batch loop catches
`AthcError | OSError` per item (`FAIL`, count, continue) and `Exception` per
item (`unexpected`, count, continue); then exits
`2 if failed else 1 if findings else 0`.

`ATHC_DEBUG` goes: the traceback is always in the log.

## Unchanged

Click and `ctx.exit`, `--version`, `--league`, the config layout, no verbosity
or color options, packaging: decided on 2026-10-08 against pdf-converter and
not reopened here.

## Open

- `set-normals -q`: the only quiet option in athc. Keep it, drop it, or give
  every file-writing command one. pdf-converter has none.

## Sources

- clig.dev: <https://clig.dev/>
- no-color.org: <https://no-color.org/>; force-color.org: <https://force-color.org/>
- Rich console and logging docs: <https://rich.readthedocs.io/en/stable/console.html>, <https://rich.readthedocs.io/en/stable/logging.html>
- Python Logging HOWTO (library guidance, when to print vs log): <https://docs.python.org/3/howto/logging.html>
- Fowler, Replace Throw with Notification: <https://martinfowler.com/articles/replaceThrowWithNotification.html>
- pip vendors Rich: <https://raw.githubusercontent.com/pypa/pip/main/src/pip/_vendor/vendor.txt>; pip logging: <https://raw.githubusercontent.com/pypa/pip/main/src/pip/_internal/utils/logging.py>
- Hatch, pdm, Typer, Textual on Rich: their `pyproject.toml`; <https://typer.tiangolo.com/tutorial/printing/>
- Click 8.4.1 has no `NO_COLOR` handling: `.venv\Lib\site-packages\click\_compat.py`, `utils.py`; exit codes: `exceptions.py` (ClickException 1, UsageError 2), `core.py` (`main()`: Abort 1, `Exit`)
- git exit codes: <https://raw.githubusercontent.com/git/git/master/usage.c> (die 128, usage 129); <https://git-scm.com/docs/git-diff> (`--exit-code`); <https://git-scm.com/docs/git-grep>
- ruff: <https://docs.astral.sh/ruff/linter/> (0 / 1 / 2), <https://docs.astral.sh/ruff/formatter/>
- pytest: <https://docs.pytest.org/en/stable/reference/exit-codes.html>
- pip status codes: <https://raw.githubusercontent.com/pypa/pip/main/src/pip/_internal/cli/status_codes.py>
- grep, diff, find, ls man pages: <https://man7.org/linux/man-pages/man1/grep.1.html>, <https://man7.org/linux/man-pages/man1/diff.1.html>, <https://man7.org/linux/man-pages/man1/find.1.html>, <https://man7.org/linux/man-pages/man1/ls.1.html>; ripgrep: <https://manpages.debian.org/testing/ripgrep/rg.1.en.html>
- rsync (23 partial): <https://download.samba.org/pub/rsync/rsync.1>; 7-Zip: <https://7-zip.opensource.jp/chm/cmdline/exit_codes.htm>
- argparse (usage 2): <https://docs.python.org/3/library/argparse.html>; clap: <https://docs.rs/clap/latest/clap/error/struct.Error.html>
- bash exit status (130): <https://www.gnu.org/software/bash/manual/html_node/Exit-Status.html>; pre-commit: <https://pre-commit.com/>
- gcc warnings and `-Werror`: <https://gcc.gnu.org/onlinedocs/gcc/Warning-Options.html>; eslint: <https://eslint.org/docs/latest/use/command-line-interface>
- Black (per-file catch, batch continues): <https://raw.githubusercontent.com/psf/black/main/src/black/__init__.py>
- Run logs: winget <https://learn.microsoft.com/en-us/windows/package-manager/winget/troubleshooting>; npm <https://docs.npmjs.com/cli/v10/using-npm/logging>; Chocolatey <https://docs.chocolatey.org/en-us/troubleshooting/>; platformdirs <https://platformdirs.readthedocs.io/en/latest/platforms.html>
- Progress on stderr: <https://git-scm.com/docs/git-clone>, <https://ffmpeg.org/ffmpeg.html>, <https://tqdm.github.io/docs/tqdm/>
- Library progress callbacks: OR-Tools `log_callback` (`.venv\Lib\site-packages\ortools\sat\python\cp_model.py`); yt-dlp `progress_hooks`: <https://raw.githubusercontent.com/yt-dlp/yt-dlp/master/README.md>
- pdf-converter source: `C:\Users\Brian\Projects\Customer Projects\Tamarack Habilitations\pdf-converter\src\pdf_converter\{console,log,errors,cli}.py`
