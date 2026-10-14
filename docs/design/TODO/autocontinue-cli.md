# autocontinue CLI plan

**Goal:** `athc autocontinue` with nothing after it watches the screen for the game's Continue button and clicks it between plays, with the timings from `athc.ini` or, when the section is missing, the shipped defaults, until the coach presses Ctrl+C or moves the mouse to the hot corner; `--delay` sets the pause before each click for one run.

**Status:** proposal, 2026-10-13; nothing changed yet. Every choice is decided below, with its reason next to it. Reviewed in three rounds for codebase fit and coach workflows; the findings are folded in. Depends on [cli-help.md](cli-help.md) landing first.

## 1. Today

- `athc autocontinue [--hot-corner | --no-hot-corner]` (`src/athc/cli/autocontinue.py`): no arguments. It imports `athc.autocontinue.main` lazily (pyautogui, OpenCV) before anything else runs; an `ImportError` names whichever module is missing, `FAIL Missing pyautogui. Reinstall athc.` or `FAIL Missing cv2. Reinstall athc.` (`error.name or 'pyautogui'`), exit 2. It calls `auto_continue(hot_corner, progress=console.progress, warn=console.warn)`; a `KeyboardInterrupt` out of the loop prints `Shutting down AutoContinue` through `console.result` and exits 0.
- The loop (`src/athc/autocontinue/main.py`): reads `[autocontinue]` from `athc.ini`, loads `images/continue_button.png` once (missing or unreadable: `FAIL <image>: <why> Reinstall athc.`, 2), says `AutoContinue is RUNNING. Press CTRL-C to exit.`, `MouseMoveDuration set to <n>`, `DelayBeforeContinue set to <n>` and a hot-corner line through `progress` (stderr and the run log). Then, forever: it re-reads `athc.ini` when the file's path, size or mtime changed (a reload that fails is `WARN <athc.ini>: <why> Keeping the previous settings.`); it scans the primary monitor only while the game is the active window (the title contains `Front Page Sports Football Pro '98`, case ignored; otherwise it sleeps 2 s and says nothing); on a match it moves the mouse over `mouse_move_duration` seconds, waits `delay_before_continue` seconds, calls `leftClick()` with no coordinates and sleeps 4 s; with `delay_before_continue` below 0 it still moves the mouse to the button, never clicks, sleeps 8 s and says nothing. A screen grab that fails (locked screen, screensaver, disconnected Remote Desktop) is one `WARN` and a 60 s back-off.
- `leftClick()` with no coordinates clicks wherever the pointer is when the delay ends (pyautogui's `click` takes the current `position()` when no point is given), so a coach who touches the mouse during the delay gets a click somewhere else in the game window, not on the button.
- The hot corner is pyautogui's fail-safe pinned to the top-left point (`FAILSAFE_POINTS = [(0, 0)]`, `FAILSAFE` on or off with the setting). pyautogui checks it only inside its own mouse and keyboard functions (`_genericPyAutoGUIChecks` wraps `moveTo` and `leftClick`, not `locateCenterOnScreen`), so today the corner stops the watcher only at the next sighting while the game is the active window: with the game unfocused, closed, or showing no button, the mouse in the corner does nothing. When it fires, `FailSafeException` is turned into `KeyboardInterrupt` by a `try` that wraps only the move and the click.
- Settings (`src/athc/autocontinue/config.py`): `mouse_move_duration` and `delay_before_continue` are required numbers, `hot_corner` an optional boolean, on when absent. No `athc.ini`, no section or a missing key is `FAIL <athc.ini>: No [autocontinue] section. Add one, or set ATHC_CONFIG_DIR.` or `FAIL <athc.ini>: Missing required setting 'delay_before_continue' in [autocontinue].`, 2; a non-number is `FAIL <athc.ini>: [autocontinue] mouse_move_duration: Must be a number, got 'fast'.`, 2; a bad boolean `... hot_corner: Must be true or false, got 'maybe'.`, 2. `--hot-corner/--no-hot-corner` overrides `hot_corner`, and the override holds across live reloads. `config/release/athc.ini` and `config/dev/athc.ini` both ship `0.0`, `1.0`, `true`.
- No `--league`, no path, no team: it reads no league data and nothing under `[league]`.
- The rules it departs from: `docs/design/architecture.md` (Config) says a missing file, section or key means the in-code defaults and a tool errors only for a value it needs at runtime that cannot be resolved; `docs/design/installer.md` and the header of the shipped `athc.ini` say every section and key is optional; the release `README.txt` promises that a new tool "runs with sensible defaults out of the box". `docs/autocontinue/README.md` and the `[autocontinue]` comment make this tool the one exception ("a clicking watcher shouldn't guess timings"). `convert-pdb` reads its section with a default per key (`src/athc/pdbtoexcel/config.py`).
- Where it stands: `STATUS.md` lists it DONE with halftime handling open; `TODO.md` holds "install: exclude autocontinue" (1.0.0), "add halftime" and a usability item (2.0.0). `docs/design/installer.md` says nothing about excluding it; the build collects its PNGs. The release `README.txt` lists it under Windows 10 or newer. The six `halftime*.png` images ship unused; only `continue_button.png` is read. Nothing stops a second copy from running beside the first, and no doc mentions it.
- Who it was written for: the README calls it a tool for "unattended sim runs", and the loop's comments name "the commish" as the person at the keyboard. `docs/design/fbpro98-game-behavior.md` covers injuries, positions and the play editor; nothing about running games.
- The real help today: `Usage: athc autocontinue [-h] [--hot-corner | --no-hot-corner]`, a six-line description with `CTRL-C`, and Click renders the pair as `--hot-corner / --no-hot-corner`.

## 2. Who runs it, for what

Who sits at the Continue prompt. The game shows Continue between plays in every game, whether a human plays or the computer plays the computer (the game's behavior, confirmed by the league's coaches; the README and COMMANDS.txt describe the prompt), so anyone running a game meets it: a coach watching a game of their own, and the commissioner on sim night (the README's "unattended sim runs", the code's "the commish"). The commissioner's use gets no row, since these plans cover coach workflows only.

| # | Who | Wants to | Runs | Gets |
|---|---|---|---|---|
| 1 | Coach | watch a game of their own without clicking Continue after every play | `athc autocontinue`, then starts the game | `Waiting for the game window.` until the game is the active window, then each Continue clicked `delay_before_continue` seconds after it appears |
| 2 | Coach | time to read each play's result before it advances | `athc autocontinue --delay 3` | three seconds before each click, for this run only; a mouse moved to the top-left corner during those seconds stops the watcher before the click |
| 3 | Coach | let a watched game run to the end while away from the PC | `athc autocontinue` | the game advances on its own; switching to another app pauses both; the PC must stay unlocked with the screensaver off (a hidden screen is a `WARN` and a 60 s pause); after the game ends it keeps scanning until stopped; moving the mouse to the top-left corner stops it at the next click |
| 4 | Coach | keep the top-left corner for Windows (the Start button, a docked app) | `athc autocontinue --no-hot-corner` | Ctrl+C is the only stop |
| 5 | Coach | the settings for every run | `delay_before_continue`, `mouse_move_duration` and `hot_corner` in `athc.ini`, edited while it runs if need be | the new values picked up on the next scan |
| 6 | Coach | from a batch file that also starts the game | the exit code: 0 when stopped, 2 when it could not start; `2> status.txt` keeps the status and problem lines, among them `Game window active.` when the game was started first; `Stopped.` stays on the console | |

## 3. What other tools do

- **A watcher runs until stopped, and says how.** Windows `ping /t`: "Specifies ping continue sending echo Request messages to the destination until interrupted. ... To interrupt and quit this command, press CTRL+C."; the same page offers the counted form, `/n <count>`: "Specifies the number of echo Request messages be sent." clig.dev: "If a user hits Ctrl-C (the INT signal), exit as soon as possible."; "Show progress if something takes a long time."; "If your program displays no output for a while, it will look broken."
- **Timing is a seconds option with a short name.** Windows `timeout /t <timeoutinseconds>`: "Specifies the decimal number of seconds (between -1 and 99999) to wait"; `ping /w <timeout>`: "the amount of time, in milliseconds, to wait"; `watch -n, --interval seconds`: "Specify update interval."; robocopy `/w:<n>`: "Specifies the wait time between retries, in seconds."
- **Flags beat the config file, for one run.** clig.dev: "Apply configuration parameters in order of precedence", flags first, then environment variables, then configuration files. In-house: `--hot-corner` over `hot_corner`, `--league` over `[athc] league`. (`convert-pdb --percentages/--no-percentages` over `calculate_percentages` is another: it overrides the setting both ways for one run.)
- **Defaults are the shipped values; a config section is optional.** clig.dev: "Make the default the right thing for most users." architecture.md: "In-code defaults are authoritative: missing file, section or key means defaults". `convert-pdb` reads `[convert-pdb]` with `.get(SECTION, {})` and a default per key.
- **Click's number types and boolean pairs.** Boolean flags: "declare `--{on-option}/--{off-option}`. Click will automatically set `is_flag=True`."; a pair declared without a default shows no `[default: ...]` (`core.py`, `get_help_record`). `FloatRange` carries its own words into the help and the errors: `core.py` appends the range to every range option's help (`[x>=0]`), and its type name is `float range`, so a bad value reads `'fast' is not a valid float range.` (`types.py`). Plain `float` reads `'fast' is not a valid float.` and adds nothing to the help; a bound then comes from a callback, as `convert-pdb`'s `_ext` does with `click.BadParameter("must have a .pdb extension.")`. An option without `metavar` shows its type name in capitals (`FLOAT`).
- **The fail-safe corner is the library's, checked only by its own input calls.** pyautogui: "When fail-safe mode is True", "moving the mouse to the upper-left will raise a pyautogui.FailSafeException"; `FAILSAFE_POINTS` defaults to the four corners of the primary monitor; `failSafeCheck()` is a public function that raises when `FAILSAFE` is on and the mouse is on one of the points, and `_genericPyAutoGUIChecks` calls it before `moveTo`, `leftClick` and the other input functions, never before the `locate*` functions (`pyautogui/__init__.py`). `moveTo`: "If `duration` is 0 or unspecified, movement is immediate."
- **Windows words.** ping's docs write CTRL+C; cli-help.md rule 9 writes Ctrl+C.

## 4. Decisions

1. **One command, no arguments, no league.** It acts on the screen, not on files: no PATH, no `.`, no team, and no `--league` (architecture.md: "Commands that never read league data don't have it"). The shared path rule (check-ppp decision 3: no path means the configured default, `.` the current folder, an explicit path overrides both), the default team (check-ppp decisions 4 and 5), the `--league` text (cli-help.md rule 10) and `-r` (check-ppp decision 9) do not apply, since there are no files, no team and no league. An argument is Click's own line with athc's period, `Error: Got unexpected extra argument (x).`, 2 (the period is added once where usage errors are rendered in `src/athc/cli/__init__.py`; the mechanism is in [convert-pdb-cli.md](convert-pdb-cli.md)).
2. **No arguments runs on the settings in `athc.ini`, and on the shipped defaults when the file, the section or a key is missing** (`0.0` s mouse move, `1.0` s delay, hot corner on: the values `config/release/athc.ini` ships). architecture.md, installer.md and the `athc.ini` header make every section and key optional with in-code defaults, and `convert-pdb` already works that way; the README's exception rests on "guessed timings", but the defaults are the shipped values, not guesses; and the current error tells a coach to set `ATHC_CONFIG_DIR`, a variable architecture.md says end users never set. A key that is present but wrong stays an error. The "No [autocontinue] section" and "Missing required setting" lines go. The same rule holds mid-run: a deleted `athc.ini` reads as the defaults (the signature changes, `load_config` returns `{}`), applied and said through the settings lines like any other change, not a `WARN`; an editor that saves by delete-and-rename changes the signature twice, and each change is applied.
3. **The timing keys stay in `athc.ini`; `--delay SECONDS` overrides `delay_before_continue` for one run; `mouse_move_duration` has no option.** The delay is what differs between a watched game (time to read each result, row 2) and an unattended one (row 3), so it is per run (clig.dev's precedence; the in-house `--hot-corner`). The glide time is taste, set once, like `include_category_worksheets` in `[convert-pdb]`. The name is one plain word, as `watch -n` and `timeout /t` are, with `SECONDS` as the placeholder (cli-help.md rule 2); the help names the key it overrides, as cli-help.md's `--hot-corner` text does. Like `--hot-corner`, the override holds across live reloads (today's rule in ARCHITECTURE.md): a reload that changes `delay_before_continue` neither applies nor prints while `--delay` is set.
4. **`--delay` is a plain `float` with a callback for the bound, not a `FloatRange`.** `FloatRange` would end the help line with `[x>=0]` and call a bad value `not a valid float range`, not the plain words cli-help.md wants in a coach's help (its rule 9 lists the Windows words; neither phrase is one); `float` keeps Click's `'fast' is not a valid float.` for a non-number, and the callback gives the bound in athc's words inside Click's frame, lowercase and ending in a period (architecture.md), as `convert-pdb`'s `_ext` callback does: `must be 0 or more, got -1.0.` `metavar="SECONDS"` is set explicitly (Click would print `FLOAT`).
5. **Both timings are 0 or more**, in `athc.ini` and on the command line. 0 means instant (pyautogui's `duration`); a value below 0 is rejected, so today's `-1.0` "find but don't click" setting goes with no replacement. One validator for the two keys, `Must be a number, 0 or more, got '-1.0'.`; the option's callback says `must be 0 or more, got -1.0.` No upper limit: a long delay is the coach's choice.
6. **The hot corner stays the library's (decided 2026-10-13).** pyautogui checks it inside its own mouse calls, as today; the loop adds no check of its own. `--hot-corner/--no-hot-corner` over `hot_corner`, on by default, pinned to the top-left point, with cli-help.md's help text; Click shows no default for a boolean pair declared without one, so "(on by default)" stays in words.
7. **It stops by Ctrl+C or the hot corner, exit 0, as today; there is no timed stop and no stop when the game closes.** A watcher runs until stopped (`ping /t`); the stop is the normal end, which is why architecture.md keeps 0 here instead of 130. ping also offers a counted form (`/n`), but this loop has no natural count: plays per game vary, and it cannot tell a closed game from one not yet started, since it knows the game only by the active window's title and row 1 starts it before the game. The consequence for row 3 is stated there: after the game ends it keeps scanning, every second while the game window is active and every 2 s otherwise, and clicks nothing unless the button appears, until the coach stops it.
8. **The loop says whether it has the game window, at start and on every change.** Today nothing prints while the game is not the active window or the image never matches, which clig.dev calls looking broken; a coach who starts the watcher first (row 1) sees nothing, and a batch file that starts the game first (row 6) never learns the watcher sees it. The focus state starts unknown, so the first check always prints one of the two lines, `Waiting for the game window.` or `Game window active.`, and each later change prints one. Alt-tabbing prints two lines; an unattended night prints none after the first.
9. **The status lines name what the coach sees, never the tool**: the Continue button, `Ctrl+C` (cli-help.md rule 9; ping's docs write CTRL+C) and the `athc.ini` key names (`delay_before_continue = 1.0`). architecture.md puts no `athc <command>:` prefix on a line, so `AutoContinue` goes the same way as `DelayBeforeContinue`, a name in no file of athc's: the start line is `Watching for the Continue button. Press Ctrl+C to stop.` and the stop line `Stopped.` One verb, "stop", in every line and in the help.
10. **No single-instance guard; the docs will say to run one copy at a time.** Two copies both click one Continue. No athc command guards against a second copy, and ping's documented parameters include none; a lock file would be athc's only one and would outlive a crash. Today no doc mentions a second copy; the README and COMMANDS.txt gain the sentence (section 11).
11. **Setup order: the options, the import, the settings, the button image, then the screen.** A bad option is Click's usage error before anything runs; the lazy import of `athc.autocontinue.main` comes next, so `FAIL Missing <module>. Reinstall athc.` precedes any `athc.ini` error; a wrong value in `athc.ini` fails next; a missing image fails with `Reinstall athc.`; the loop starts last. Nothing is clicked before every start line has printed.
12. **Help text follows cli-help.md's style** (section 5): `[OPTIONS]`, a new summary (today's is 59 characters, over rule 6's 55), `--delay SECONDS`, cli-help.md's `--hot-corner` text, an Examples epilog. cli-help.md lands first, so this plan describes that form only.
13. **`config set` keeps to `league`.** The three keys are edited by hand in `athc.ini`, like `[convert-pdb]`'s, and check-ppp decision 14 made the same call for `team`; `athc config edit` opens the file.
14. **The installer item is out of scope.** "install: exclude autocontinue" (TODO 1.0.0) is a packaging decision; the command is the same whether or not the public setup.exe ships it, and `docs/design/installer.md` today collects its images like any package data. This plan changes nothing there.
15. **Halftime is out of scope** (TODO 2.0.0); nothing here depends on it, and the shipped `halftime*.png` images stay unused until that work.

## 5. The command

As Click renders it with the chosen types (`float` with `metavar="SECONDS"`, a boolean pair without a default): no `[x>=0]`, no `[default: ...]`.

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

### Modes

| Mode | Finds the button | Then | Pace | Lines while running |
|---|---|---|---|---|
| default | while the game is the active window | moves the mouse to the button over `mouse_move_duration` s, waits the delay, clicks | 1 s between scans, 4 s after a click | the window lines and `WARN` lines (stderr) |

- **The delay in force:** `--delay` when given, else `delay_before_continue` from `athc.ini`, else `1.0`. The hot corner: `--hot-corner`/`--no-hot-corner` when given, else `hot_corner`, else on; checked by pyautogui inside its mouse calls, as today.
- **Order of output:** the start line, `mouse_move_duration = ...`, `delay_before_continue = ...`, the hot-corner line, then one of `Waiting for the game window.` and `Game window active.` (always one, decision 8); while running, the window lines on each change, `WARN` lines as they happen, and the settings lines again when a reload changes a value not held by an option; `Stopped.` last, on stdout.
- **Argument errors:** an extra argument is Click's `Got unexpected extra argument (x).` (athc's period, added once in `src/athc/cli/__init__.py`); `--delay` not a number is Click's `'fast' is not a valid float.`; `--delay` below 0 is the callback's `must be 0 or more, got -1.0.`, both inside Click's `Invalid value for '--delay':` frame; all 2, before anything is imported or read.

## 6. Settings

In `athc.ini`:

```ini
; autocontinue: every key is optional; a missing one uses the value shown.
[autocontinue]
; seconds to move the mouse to the button (0.0 = instant)
mouse_move_duration = 0.0
; seconds to wait before each click (0.0 = instant); --delay overrides it for one run
delay_before_continue = 1.0
; stop the watcher when the mouse hits the top-left corner (default on)
hot_corner = true
```

- The file is re-read whenever it changes, as today; a value held by `--delay` or a hot-corner flag is not affected. A file that disappears mid-run means the defaults, said through the settings lines (decision 2); a file that reappears is read like any change.
- Shipped files: `config/release/athc.ini` and `config/dev/athc.ini` keep their values; the "autocontinue requires its settings" comment goes.
- Nothing under `[league]` is read; `--league` does not exist here.

## 7. Lines and exit codes

New and changed lines, in the project's wording; everything else prints as today.

| When | Line | Code |
|---|---|---|
| an argument | `Error: Got unexpected extra argument (x).` (Click's text, athc's period added once in `src/athc/cli/__init__.py`) | 2 |
| `--delay` not a number | `Error: Invalid value for '--delay': 'fast' is not a valid float.` (Click's own) | 2 |
| `--delay` below 0 | `Error: Invalid value for '--delay': must be 0 or more, got -1.0.` | 2 |
| a module missing | `FAIL Missing pyautogui. Reinstall athc.` (or `cv2`), as today, before any `athc.ini` error | 2 |
| no `athc.ini`, no section, a key missing, at start or mid-run | nothing; the defaults apply (mid-run, the settings lines below say what changed) | |
| a timing key not a number, or below 0 | `FAIL <athc.ini>: [autocontinue] delay_before_continue: Must be a number, 0 or more, got '-1.0'.` | 2 |
| `hot_corner` not a boolean | as today | 2 |
| start | `Watching for the Continue button. Press Ctrl+C to stop.` | |
| the settings, at start and when a reload changes one | `mouse_move_duration = 0.0` / `delay_before_continue = 1.0`; with `--delay 3`, `delay_before_continue = 3.0 (--delay)` once at start | |
| hot corner on | `Hot corner on: move the mouse to the top-left corner to stop.` | |
| hot corner off | `Hot corner off: press Ctrl+C to stop.` | |
| the first check, and whenever the game stops being the active window | `Waiting for the game window.` | |
| the first check, and whenever the game becomes the active window | `Game window active.` | |
| a reload that fails to parse, a hidden screen, a missing image | as today | |
| stop (Ctrl+C, or the hot corner at a click) | `Stopped.` (stdout) | 0 |

Codes stay 0 stopped and 2 error; never 1 (nothing is a finding) and never 130 (architecture.md's one exception). The start, settings, hot-corner and window lines go through `console.progress` (stderr and the run log); the stop line through `console.result` (stdout and the run log).

## 8. Related commands

None reads the screen, and no command points at autocontinue. `athc config edit` and `athc config path` reach the `athc.ini` its keys live in; `config set` stays `league`-only (decision 13).

## 9. Code

- `src/athc/cli/autocontinue.py`: `--delay` (`type=float`, `metavar="SECONDS"`, `default=None`, a callback raising `click.BadParameter(f"must be 0 or more, got {value}.", ctx, param)` below 0, as `convert_pdb._ext` does), the summary and description of section 5; `auto_continue(hot_corner=hot_corner, delay=delay, progress=console.progress, warn=console.warn)`; the `KeyboardInterrupt` handler prints `Stopped.`.
- `src/athc/autocontinue/config.py`: `Config` gets `mouse_move_duration: float = 0.0` and `delay_before_continue: float = 1.0` beside `hot_corner: bool = True`, the one place for the defaults; `load_config` reads `load_athc_config().get(SECTION, {})`; `_required_float` becomes `_timing(section, key, default)`, returning the default for a missing key and raising the `Must be a number, 0 or more` error otherwise; the `ATHC_CONFIG_DIR` error goes. The module docstring (lines 3-5, "requires its settings") and the `load_config` docstring (lines 35-37) say the new rule.
- `src/athc/autocontinue/main.py`: `auto_continue(hot_corner=None, delay=None, *, progress=None, warn=None)`; today's branch for a delay below 0 (find the button, never click) goes; `_resolve_delay(config, override)` beside `_resolve_hot_corner`; a focus state that starts unknown and says `Waiting for the game window.` or `Game window active.` on the first check and each change; `_say_config_changes` prints the key-name lines and the `(--delay)` form, and skips a key held by an option; the start, stop and hot-corner lines of section 7. The module docstring (lines 4-5, `MouseMoveDuration / DelayBeforeContinue`), the `auto_continue` docstring (lines 57-58, "The initial load is required") and `_apply_hot_corner`'s (line 191, "Ctrl-C only") say the new rules.
- `config/release/athc.ini`, `config/dev/athc.ini`: the comments in section 6.

## 10. Tests

`tests/integration/test_autocontinue.py`:

- Defaults: no `athc.ini`, a file with another section only, and a section with one key each give `Config(0.0, 1.0, True)` with the missing values filled.
- The timing validator, once for both keys: `0` accepted, `-0.1` rejected with the line; a non-number rejected with the new wording.
- `--delay`: `0` accepted and forwarded as `0.0`; `-0.1` rejected with the callback's line; `fast` rejected with Click's float line; absent forwards `None`; `--help` shows `--delay SECONDS` and no `[x>=0]`.
- The loop, with pyautogui stubbed: `--delay` wins over the file and holds when a reload changes the key, with no line; a `FailSafeException` out of the stubbed `leftClick` stops the loop, as today; the first check prints `Game window active.` when the game is already active and `Waiting for the game window.` when it is not, then one line per change, not per pass; a deleted `athc.ini` mid-run applies the defaults and says the changed settings, with no `WARN`; the start lines in order.
- An extra argument is Click's line, 2.
- Existing tests that change: `test_load_config_errors_when_no_config`, `test_load_config_errors_when_section_missing` and `test_load_config_errors_on_missing_setting` (defaults now, not errors); `test_load_config_errors_on_invalid_value` (the new wording); `test_cli_no_config_exits_2` (runs on the defaults with the loop stubbed, exit 0); `test_cli_keyboard_interrupt_exits_clean` (stdout `Stopped.`); `test_loop_status_goes_to_stderr_through_the_callbacks` (its `fake` takes `delay`; the start line's wording; stdout `Stopped.`); `test_config_changes_are_said_through_the_callback` (the key-name lines). `test_cli_runs_with_config` and `test_cli_forwards_hot_corner_override` keep passing unchanged, since their stubs take `**callbacks`; `test_cli_help_describes_continue`, `test_cli_missing_dependency_exits_2`, `test_cli_missing_button_image_exits_2_before_watching`, the `hot_corner`, signature, focus and image tests keep passing by design.
- `tests/integration/test_cli_root.py`: `test_usage_lists_each_option`'s autocontinue case stays `athc autocontinue [OPTIONS]` as cli-help.md sets it (the new options sit under Options, not in the usage line); `test_help_uses_lowercase_names` has no autocontinue row. `tests/integration/test_config.py`: `test_release_autocontinue_section_loads` keeps passing.
- `tests/integration/README.md`: the autocontinue tables.

## 11. Docs and meta

- `docs/autocontinue/README.md` and `docs/autocontinue/ARCHITECTURE.md`: the options, the defaults, the lines and codes above, the window lines, the new sentences "run one copy at a time; two copies both click" and "keep the PC unlocked and the screensaver off"; the "required settings" paragraphs, the `-1.0` sentence and the `AutoContinue` names go. (docs-layout.md later folds both into `docs/autocontinue.md`.)
- `config/release/docs/COMMANDS.txt` section 14: the settings sentence, `--delay` with examples, `CTRL-C` to `Ctrl+C`, the one-copy sentence; `config/release/athc.ini` comments; `config/release/docs/README.txt`: nothing (no setup step).
- `docs/design/architecture.md`: nothing; autocontinue now follows its Config rule.
- `docs/design/TODO/cli-help.md`, autocontinue: the summary `Click the game's Continue button between plays.`, `--delay SECONDS`, and its Ctrl+C fix extended to the status lines.
- `CHANGELOG.md`, `STATUS.md`, `TODO.md` (a 1.0.0 line pointing here).

### cli-help.md changes

- A new summary: today's `Watch for the 'Continue' button between plays and click it.` is 59 characters, over rule 6's 55; cli-help.md lists no new summary for autocontinue.
- A new option, `--delay SECONDS`; `--hot-corner` keeps the text cli-help.md already gives it.
- The Ctrl+C fix covers the status lines as well as the help text.

## Shared vocabulary

- `--delay SECONDS`: a one-run override of a seconds setting in `athc.ini`; its help names the key (`Overrides delay_before_continue in athc.ini`), the pattern `--hot-corner` set. Declared as `float` with a callback for the bound, never `FloatRange`, so the help and the errors stay in plain words.
- `SECONDS`: the placeholder for a time in seconds; decimals allowed; 0 means instant.

## Sources

- Windows `ping`: <https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/ping>; `timeout`: <https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/timeout>; `robocopy`: <https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/robocopy>
- `watch -n`: <https://man7.org/linux/man-pages/man1/watch.1.html>
- clig.dev: <https://clig.dev/>
- Click boolean flags: <https://click.palletsprojects.com/en/stable/options/>; ranges and FLOAT: <https://click.palletsprojects.com/en/stable/parameter-types/>; `click/core.py` (`_parse_decls`, `get_help_record` and `get_help_extra` for the `[x>=0]` suffix, `make_metavar`, the extra-argument text), `click/types.py` (`_NumberParamTypeBase.convert`, `FloatParamType.name`, `FloatRange.name`, `_describe_range`) in the venv
- pyautogui fail-safe, `moveTo` and `click`: <https://pyautogui.readthedocs.io/en/latest/quickstart.html>; `pyautogui/__init__.py` in the venv (`FAILSAFE`, `FAILSAFE_POINTS`, `failSafeCheck`, `_genericPyAutoGUIChecks`, `_normalizeXYArgs`, `click`, `leftClick`, `moveTo`, `locateCenterOnScreen`)
- athc: `src/athc/cli/autocontinue.py`, `src/athc/autocontinue/config.py`, `src/athc/autocontinue/main.py`, `src/athc/cli/__init__.py`, `src/athc/cli/convert_pdb.py`, `src/athc/pdbtoexcel/config.py`, `src/athc/pdbtoexcel/excel_workbook.py`, `src/athc/config.py`, `src/athc/errors.py`, `src/athc/console.py`, `docs/autocontinue/README.md`, `docs/autocontinue/ARCHITECTURE.md`, `docs/design/architecture.md`, `docs/design/installer.md`, `docs/design/fbpro98-game-behavior.md`, `docs/design/TODO/cli-help.md`, `docs/design/TODO/check-ppp-cli.md`, `docs/design/TODO/docs-layout.md`, `config/release/athc.ini`, `config/dev/athc.ini`, `config/release/docs/COMMANDS.txt`, `config/release/docs/README.txt`, `pyproject.toml`, `STATUS.md`, `TODO.md`, `tests/integration/test_autocontinue.py`, `tests/integration/test_cli_root.py`, `tests/integration/test_config.py`, `tests/integration/README.md`, `tests/conftest.py`; `athc autocontinue --help` run on 2026-10-13
