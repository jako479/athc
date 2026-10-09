# Console, run log and exit codes by command and library

Status: companion to [logging.md](logging.md), same TODO task. When the task
is done each tool's README carries its own lines and codes and this file goes.
The release docs' per-command "Messages" part (`COMMANDS.txt`) is written from
this file.

Every command follows the rules in logging.md; this file says what each one
prints, what counts as a finding, and what each library raises and returns.

## Shared code

### `main()`: the one place

```python
def main() -> None:
    log_path = setup_logging()
    logger.info("athc %s %s", version("athc"), " ".join(sys.argv[1:]))
    try:
        code = cli(standalone_mode=False) or 0
    except click.ClickException as error:      # usage: Click's own text, 2
        error.show()
        logger.error("%s", error.format_message())
        code = error.exit_code
    except click.Abort:                        # Ctrl-C
        console.fail("interrupted")
        code = 130
    except (AthcError, OSError) as error:      # an expected failure
        console.fail(str(error))
        code = 2
    except Exception:                          # a bug
        console.unexpected()
        code = 2
    logger.info("exit %d", code)
    sys.exit(code)
```

`__main__.py` calls `main()`, so `python -m athc` gets the same backstop.

### A single-file command

Nothing is caught; a failure propagates to `main()`.

```python
@click.pass_context
def list_normals(ctx, gameplan, output_file, sort, league):
    cfg = load(league)                 # LeagueError / ConfigFileError -> FAIL, 2
    plan = read_gameplan(gameplan)     # OSError / InvalidGamePlanError -> FAIL, 2
    lines = normals(plan, sort, cfg.categories)
    if output_file == "-":
        for line in lines:
            console.print(line)        # the result, stdout, not logged
    else:
        write_lines(output_file, lines)
        console.ok(f"{output_file}: {len(lines)} normal play(s)")
```

### A batch command

Startup problems propagate; each item is caught; the worst outcome wins.

```python
@click.pass_context
def check(ctx, paths, recursive, league):
    cfg = load(league)
    rules = load_rules(cfg)                        # propagates: FAIL, 2
    files = collect_files(paths, ".pln", recursive)  # none: WARN, falls through
    findings = failed = 0
    for file in files:
        try:
            plan = read_gameplan(file)
        except (AthcError, OSError) as error:
            console.fail(f"{file}: {error}")
            failed += 1
            continue
        except Exception:
            console.unexpected(str(file))
            failed += 1
            continue
        violations = validate_gameplan(plan, rules)
        if violations:
            findings += 1
            console.result(f"{file}: {len(violations)} violation(s)")
            for v in violations:
                console.print(f"  [{v.category}] {v.message}")
        else:
            console.ok(f"{file}: {plan.side}, {len(plan.normals)} normal")
    console.result(f"{len(files)} file(s) checked, {findings} with violations, {failed} failed")
    ctx.exit(2 if failed else 1 if findings else 0)
```

### A library

```python
class InvalidGamePlanError(AthcError):
    """The bytes are not a game plan."""

def read_play_pool(root, labels) -> PlayPool:
    """pool.issues holds every problem found; nothing is logged."""

def generate(config, *, progress: Callable[[str], None] | None = None) -> SchedulerResult:
    say = progress or (lambda _: None)
    say("Phase 1: selecting matchups")
```

## Commands

Each block: input, the lines it prints, what counts as a finding, the exit
code. "Batch" means the batch loop above. Failures and warnings inside a batch
are the standard `FAIL <path>: ...` and `WARN ...` lines and are not repeated.

### gameplan

**check** `[path]...` (file, directory or glob; `-r`). Batch.
- `OK   <file>: <side>, <n> normal` per clean file; a headline plus
  `  [Category] message` lines per file with violations; tally.
- `WARN` per play-pool issue and rules-file notice, before the files.
- Findings: violations. Exit 2 / 1 / 0.

**find-play** `play... [path]` (file or directory; `-r`). Batch, no league.
- A result line per file and play: `<file>: 'play' found in slot(s) ...` or
  `<file>: 'play' not found`; a tally per play.
- Findings: a play found nowhere. Exit 2 if any file failed, else 1 if no
  play was found anywhere, else 0.

**list-normals** `gameplan [output_file]` (`-` for stdout). Single.
- The play names through `print` when the output is `-`; else
  `OK   <output_file>: <n> normal play(s)`.
- No findings. Exit 2 / 0.

**list-specials**: as list-normals, without a league.

**replace-play** `play replacement path` (file or directory; `-r`). Batch.
- `OK   <file>: 'old' replaced with 'new' [1-3][4-2]` per updated file; a
  file without the play prints nothing in a directory and
  `<file>: 'play' not found` (result) for a single file; tally.
- Replacement play not in the pool: propagates, `FAIL`, 2.
- Findings: nothing replaced anywhere. Exit 2 / 1 / 0.

**set-normals** `gameplan input_file` (`-` for stdin). Single.
- `OK   <gameplan>: <n> normal play(s)`.
- A bad input list is an error: `FAIL <input_file> line <i>: <why>` per bad
  line, the game plan untouched, 2.
- `-q`: open (logging.md).

**set-specials** `path input_file` (file or directory; `-r`). Batch.
- `OK   <file>: updated (<n> special play(s))`; `SKIP <file>: <other side>`
  for a file of the wrong side (silent today); tally.
- A file the input does not fit: `FAIL`, counted, the batch goes on.
- No findings. Exit 2 / 0.

### profile

**check** `[path]...` (`-r`). Batch. As gameplan check with `.prf` files,
`  [situation n] message` detail lines, no play pool.

**copy** `source target` (file or directory; `-r`; copy flags). Batch.
- `OK   <file>: updated (stop-clock, ...)`; `SKIP <file>: <why>` for the
  wrong side and for the source itself (silent today); tally.
- No copy flag: a usage error, 2. Source unreadable: propagates, 2.
- No findings. Exit 2 / 0.

**diff** `a b` (`-o file.txt|csv`). Single pair.
- The report through `print`; with `-o`, `OK   <file>: written`.
- Findings: any difference. Exit 2 / 1 / 0.
- A bad `-o` extension is a usage error (`BadParameter`), 2.

### playpool

**check** `[play_dir]` (default: the league's `play_path`). The library reads
the whole tree.
- The issues through `print`, one per line, then the tally
  `<n> play(s) checked in '<dir>', <i> issue(s)`.
- Findings: `pool.issues`, including an unreadable or invalid `.ply` (the
  point of the command). Exit 2 / 1 / 0.
- No `play_dir` and no league `play_path`: propagates, 2.

### check-ppp

`first [second]` (a `.prf` and a `.pln`, or a directory; `-r`). Batch over
the league file's profile/game-plan pairs.
- Per pair the `profile check` and `gameplan check` lines; tally.
- A side mismatch is `FAIL <pair>: profile is X but gameplan is Y`; in pair
  mode that is the run's failure, 2.
- No pairs in the directory: `WARN`, tally, 0.
- Findings: violations and compatibility issues. Exit 2 / 1 / 0.

### convert-pdb

`pdb_file output_file` (`-o`, `-o2`, `-d`, `-d2` game plans; `--skip-calcs`).
Single.
- Progress lines from the library (`Creating '<workbook>'`) through the
  callback, stderr.
- `WARN` per returned warning (play file not found, stale deleted play,
  invalid tendency data, play-pool issue, playpool.toml notice).
- `OK   <output_file>: <n> play(s)` at the end (today nothing reaches
  stdout).
- No findings. Exit 2 / 0; warnings keep 0.

### generate-schedule

League only; `--season`, `--seed`, `--time-limit`. Single run.
- Progress lines from the scheduler through the callback (`Generating the
  2026 schedule`, `Phase 1: ...`, `Phase 2: ... can take 30 minutes`).
- `OK   <file>` per file written (`.txt`, `.html`, `_report.html`), then
  `result`: `Generated <n> games (seed <s>)` (today nothing reaches stdout,
  and the seed is only in a log line).
- Missing ortools: `FAIL missing ortools -- reinstall athc`, 2.
- No findings. Exit 2 / 0.

### autocontinue

No input; `--hot-corner`. A loop.
- Its status through the `progress` callback (`AutoContinue is RUNNING...`,
  `MouseMoveDuration set to ...`); retries and a failed config reload through
  the `warn` callback.
- Ctrl-C is the normal stop: `Shutting down AutoContinue` through `result`,
  0.
- Missing pyautogui, bad config: `FAIL`, 2.

### config

- **path**: the path through `print`. 0.
- **edit**, **reveal**: open the file or folder; a failure propagates, 2.
- **set** `key value`: `result`: `Set <key> = <value>`. Unknown key or bad
  league: a usage error, 2. Unreadable `athc.ini`: propagates (no longer
  rewrapped as a usage error), 2.

## Tool packages (Click-free logic)

| Package | Raises (all `AthcError`) | Returns | Progress |
|---|---|---|---|
| `gameplan` | `RulesFileError` (shared), `InvalidPlayInputError` with `.violations`; `ConfigFileError` for a missing `play_path` | `validate_gameplan() -> tuple[Violation, ...]` | - |
| `profile` | `RulesFileError` (shared), `ProfileTypeMismatchError`; `diff_profiles` raises `ProfileTypeMismatchError`, never bare `ValueError` | violations, `CompatIssue`s, `ProfileDiff` | - |
| `scheduler` | `ConfigFileError` in place of its own `ConfigError`; `SchedulerError` for a solve that fails | `SchedulerResult`, with the seed and the file paths | `progress` callback replaces its four `logger.info` lines |
| `pdbtoexcel` | `InvalidPDBError`; `ConfigFileError` from `config.py` | a result carrying `warnings: list[str]` in place of its six `logger.warning` / `info` lines | `progress` callback for `Creating '<workbook>'` |
| `autocontinue` | `ConfigFileError` in place of its own `ConfigError` | - | `progress` and `warn` callbacks replace its seven logging calls |

## Libraries

| Library | Raises (all `AthcError`) | Returns |
|---|---|---|
| `athc.config` | `LeagueError`, `ConfigFileError`; `load_config` wraps `configparser.Error` itself, so no caller sees it | - |
| `fbpro98_gameplan` | `InvalidGamePlanError`; the reader wraps the model's `ValueError`s (today they escape) | - |
| `fbpro98_profile` | `InvalidProfileError`, `UnsupportedProfileError` | - |
| `fbpro98_play` | `InvalidPlayFileError`; `CategoryLabels` raises `ConfigFileError`, not `ValueError` | - |
| `fbpro98_lg2` | `InvalidLg2Error`, `UnsupportedLg2Error` | - |
| `playpool` | `RulesFileError` (shared) | `PlayPool.issues`, `rule_warnings()`, `folder_warnings()`; its two logging calls go |

`RulesFileError` is defined once, in `athc/errors.py`, and used by the
gameplan, profile and playpool rule readers (three copies today). The two
`ConfigError` classes (scheduler, autocontinue) become `ConfigFileError`.

## athc-admin

Plugs into athc and still calls `basicConfig` in three commands. It keeps
working through the change and moves onto `athc.console` and the run log as
a follow-on in its own TODO.
