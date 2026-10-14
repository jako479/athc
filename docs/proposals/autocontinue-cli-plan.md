# autocontinue CLI plan

Gives `athc autocontinue` a `--delay` option, cli-help.md's help form and new status lines; the functional changes are in [autocontinue-behavior-plan.md](autocontinue-behavior-plan.md).

Depends on cli-help, which landed first (b0d8316).

## Decisions

- One command, no arguments, no league: no PATH, no `.`, no team, no `--league`, no `-r`; nothing under `[league]` is read.
- An extra argument is Click's own line with athc's period, `Error: Got unexpected extra argument (x).`, exit 2; the period is added once where usage errors are rendered in `src/athc/cli/__init__.py` (mechanism in [architecture.md](../architecture.md#console-run-log-and-errors)).
- The timing keys stay in `athc.ini`; `--delay SECONDS` overrides `delay_before_continue` for one run; `mouse_move_duration` has no option.
- `--delay`'s help names the key it overrides.
- The `--delay` override holds across live reloads: a reload that changes `delay_before_continue` neither applies nor prints while `--delay` is set.
- `--delay` is a plain `float` with a callback for the bound, not a `FloatRange`; `metavar="SECONDS"` is set explicitly.
- `--delay` is 0 or more (0 means instant), no upper limit; a non-number is Click's `'fast' is not a valid float.`; below 0 is the callback's `must be 0 or more, got -1.0.`, lowercase, ending in a period, inside Click's frame.
- The delay in force: `--delay` when given, else `delay_before_continue` from `athc.ini`, else `1.0`.
- The hot corner stays the library's: pyautogui checks it inside its own mouse calls, as today; the loop adds no check of its own.
- `--hot-corner/--no-hot-corner` overrides `hot_corner`, on by default, pinned to the top-left point, with cli-help.md's help text; the pair is declared without a default, so "(on by default)" stays in words.
- The hot corner in force: `--hot-corner`/`--no-hot-corner` when given, else `hot_corner`, else on.
- It stops by Ctrl+C or the hot corner, exit 0, as today; no timed stop and no stop when the game closes.
- After the game ends it keeps scanning, every second while the game window is active and every 2 s otherwise, and clicks nothing unless the button appears, until the coach stops it.
- On a match it moves the mouse to the button over `mouse_move_duration` s, waits the delay and clicks; 1 s between scans, 4 s after a click.
- The status lines name what the coach sees, never the tool: the Continue button, `Ctrl+C` and the `athc.ini` key names (`delay_before_continue = 1.0`).
- No `athc <command>:` prefix on a line; the `AutoContinue` and `DelayBeforeContinue` names go.
- One verb, "stop", in every line and in the help.
- No single-instance guard; the docs say to run one copy at a time.
- Setup order: the options, the import, the settings, the button image, then the screen; nothing is clicked before every start line has printed.
- Help follows cli-help.md's style: `[OPTIONS]`, a new summary (at most 55 characters), `--delay SECONDS`, cli-help.md's `--hot-corner` text, an Examples epilog.
- `config set` keeps to `league`; the three keys are edited by hand in `athc.ini`; `athc config edit` and `athc config path` reach the file.
- The installer item ("install: exclude autocontinue", TODO 1.0.0) is out of scope; nothing changes in `docs/design/installer.md`.
- Halftime (TODO 2.0.0) is out of scope; the shipped `halftime*.png` images stay unused.
- Codes stay 0 stopped and 2 error; never 1 and never 130.
- The start, settings, hot-corner and window lines go through `console.progress` (stderr and the run log); the stop line through `console.result` (stdout and the run log).
- The `athc.ini` sample and its comments are in [autocontinue-behavior-plan.md](autocontinue-behavior-plan.md).

## Help

### athc autocontinue --help

```
Usage: athc autocontinue [OPTIONS]

  Click the game's Continue button between plays.

  Watches the primary monitor while the game is the active window and clicks
  Continue each time it appears, after a short delay. Runs until you press
  Ctrl+C or move the mouse to the top-left corner of the screen.

Options:
  --delay SECONDS                 Seconds to wait before each click. Overrides
                                  delay_before_continue in athc.ini (1.0 by
                                  default).
  --hot-corner / --no-hot-corner  Stop when the mouse hits the top-left
                                  corner. Overrides hot_corner in athc.ini (on
                                  by default).
  -h, --help                      Show this message and exit.

  Examples:

    athc autocontinue
    athc autocontinue --delay 3
```

No `[x>=0]`, no `[default: ...]`.

## Lines and exit codes

| When | Line | Code |
|---|---|---|
| an argument | `Error: Got unexpected extra argument (x).` | 2 |
| `--delay` not a number | `Error: Invalid value for '--delay': 'fast' is not a valid float.` (Click's own) | 2 |
| `--delay` below 0 | `Error: Invalid value for '--delay': must be 0 or more, got -1.0.` | 2 |
| a module missing | `FAIL Missing pyautogui. Reinstall athc.` (or `cv2`), as today, before any `athc.ini` error | 2 |
| no `athc.ini`, no section, a key missing, at start or mid-run | nothing; the defaults apply (mid-run, the settings lines say what changed) | |
| a timing key not a number, or below 0 | `FAIL <athc.ini>: [autocontinue] delay_before_continue: Must be a number, 0 or more, got '-1.0'.` | 2 |
| `hot_corner` not a boolean | as today: `... hot_corner: Must be true or false, got 'maybe'.` | 2 |
| the button image missing or unreadable | as today: `FAIL <image>: <why> Reinstall athc.` | 2 |
| start | `Watching for the Continue button. Press Ctrl+C to stop.` | |
| the settings, at start and when a reload changes one | `mouse_move_duration = 0.0` / `delay_before_continue = 1.0`; with `--delay 3`, `delay_before_continue = 3.0 (--delay)` once at start | |
| hot corner on | `Hot corner on: move the mouse to the top-left corner to stop.` | |
| hot corner off | `Hot corner off: press Ctrl+C to stop.` | |
| the first check, and whenever the game stops being the active window | `Waiting for the game window.` | |
| the first check, and whenever the game becomes the active window | `Game window active.` | |
| a reload that fails to parse | as today: `WARN <athc.ini>: <why> Keeping the previous settings.` | |
| a screen grab that fails (hidden screen) | as today: one `WARN` and a 60 s back-off | |
| stop (Ctrl+C, or the hot corner at a click) | `Stopped.` (stdout) | 0 |

- Order: the start line, `mouse_move_duration = ...`, `delay_before_continue = ...`, the hot-corner line, then one of `Waiting for the game window.` and `Game window active.`; while running, the window lines on each change, `WARN` lines as they happen, and the settings lines again when a reload changes a value not held by an option; `Stopped.` last, on stdout.
- Argument errors are all 2, before anything is imported or read.
- Lines that go: `AutoContinue is RUNNING. Press CTRL-C to exit.`, `MouseMoveDuration set to <n>`, `DelayBeforeContinue set to <n>`, `Shutting down AutoContinue`, `FAIL <athc.ini>: No [autocontinue] section. Add one, or set ATHC_CONFIG_DIR.`, `FAIL <athc.ini>: Missing required setting 'delay_before_continue' in [autocontinue].`, `FAIL <athc.ini>: [autocontinue] mouse_move_duration: Must be a number, got 'fast'.`

## Files to change

- `src/athc/cli/autocontinue.py`: `--delay` (`type=float`, `metavar="SECONDS"`, `default=None`, a callback raising `click.BadParameter(f"must be 0 or more, got {value}.", ctx, param)` below 0, as `convert_pdb._ext` does); the summary and description above; `auto_continue(hot_corner=hot_corner, delay=delay, progress=console.progress, warn=console.warn)`; the `KeyboardInterrupt` handler prints `Stopped.`.
- `src/athc/autocontinue/main.py`: `auto_continue(hot_corner=None, delay=None, *, progress=None, warn=None)`; `_resolve_delay(config, override)` beside `_resolve_hot_corner`; `_say_config_changes` prints the key-name lines and the `(--delay)` form and skips a key held by an option; the start, stop and hot-corner lines above; the module docstring (lines 4-5, `MouseMoveDuration / DelayBeforeContinue`) and `_apply_hot_corner`'s (line 191, "Ctrl-C only") say the new rules.

## Tests

In `tests/integration/test_autocontinue.py`:

- `--delay`: `0` accepted and forwarded as `0.0`; `-0.1` rejected with the callback's line; `fast` rejected with Click's float line; absent forwards `None`.
- `--help` shows `--delay SECONDS` and no `[x>=0]`.
- The loop, with pyautogui stubbed: `--delay` wins over the file and holds when a reload changes the key, with no line.
- The loop: a `FailSafeException` out of the stubbed `leftClick` stops the loop, as today.
- The loop: the start lines in order.
- An extra argument is Click's line, 2.
- Changed, `test_cli_keyboard_interrupt_exits_clean`: stdout `Stopped.`.
- Changed, `test_loop_status_goes_to_stderr_through_the_callbacks`: its `fake` takes `delay`; the start line's wording; stdout `Stopped.`.
- Changed, `test_config_changes_are_said_through_the_callback`: the key-name lines.
- Unchanged and passing: `test_cli_runs_with_config` and `test_cli_forwards_hot_corner_override` (their stubs take `**callbacks`); `test_cli_help_describes_continue`, `test_cli_missing_dependency_exits_2`, `test_cli_missing_button_image_exits_2_before_watching`, the `hot_corner`, signature, focus and image tests.

Elsewhere:

- `tests/integration/test_cli_root.py`: `test_usage_lists_each_option`'s autocontinue case stays `athc autocontinue [OPTIONS]`; `test_help_uses_lowercase_names` has no autocontinue row.
- `tests/integration/README.md`: the autocontinue tables.

## Docs and meta

- `docs/autocontinue/README.md` and `docs/autocontinue/ARCHITECTURE.md`: the options, the lines and codes, the sentences "run one copy at a time; two copies both click" and "keep the PC unlocked and the screensaver off"; the `AutoContinue` names go (docs-layout.md later folds both into `docs/autocontinue.md`).
- `config/release/docs/COMMANDS.txt` section 14: `--delay` with examples, `CTRL-C` to `Ctrl+C`, the one-copy sentence.
- `docs/design/TODO/plans/cli-help.md`, autocontinue: the summary `Click the game's Continue button between plays.`, `--delay SECONDS` (`--hot-corner` keeps its text), and the Ctrl+C fix extended to the status lines.
- `CHANGELOG.md`, `STATUS.md`, `TODO.md` (a 2.0.0 line pointing here).
