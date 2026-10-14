# autocontinue behavior plan

Makes every `[autocontinue]` setting optional with the shipped defaults, holds both timings to 0 or more, adds the game-window lines, and clicks on the button itself; help, options and the other lines are in [autocontinue-cli.md](autocontinue-cli.md).

## Decisions

- No arguments runs on the settings in `athc.ini`, and on the shipped defaults when the file, the section or a key is missing: `0.0` s mouse move, `1.0` s delay, hot corner on (the values `config/release/athc.ini` ships).
- A key that is present but wrong stays an error.
- `FAIL <athc.ini>: No [autocontinue] section. Add one, or set ATHC_CONFIG_DIR.` and `FAIL <athc.ini>: Missing required setting 'delay_before_continue' in [autocontinue].` go.
- A missing file, section or key prints nothing, at start or mid-run; the defaults apply.
- Mid-run, a deleted `athc.ini` reads as the defaults (the signature changes, `load_config` returns `{}`), applied and said through the settings lines like any other change, not a `WARN`: `mouse_move_duration = 0.0` / `delay_before_continue = 1.0`.
- An editor that saves by delete-and-rename changes the signature twice, and each change is applied.
- A file that reappears is read like any change.
- Both timings are 0 or more, in `athc.ini` and on the command line; 0 means instant; no upper limit.
- A value below 0 is rejected; today's `-1.0` "find but don't click" setting goes with no replacement.
- One validator for the two keys: `FAIL <athc.ini>: [autocontinue] delay_before_continue: Must be a number, 0 or more, got '-1.0'.`, exit 2; it replaces `FAIL <athc.ini>: [autocontinue] mouse_move_duration: Must be a number, got 'fast'.`.
- `--delay` (in [autocontinue-cli.md](autocontinue-cli.md)) takes the same bound: `Error: Invalid value for '--delay': must be 0 or more, got -1.0.`, exit 2.
- The loop says whether it has the game window, at start and on every change.
- The focus state starts unknown, so the first check always prints one of `Waiting for the game window.` and `Game window active.`; each later change prints one.
- `Waiting for the game window.`: on the first check, and whenever the game stops being the active window; the tool looks for the button only while the game is the active window, and checks again every 2 s.
- `Game window active.`: on the first check, and whenever the game becomes the active window; the tool scans the primary monitor every second and, on a match, moves the mouse to the button, waits the delay, clicks, then waits 4 s.
- The window lines go through `console.progress` (stderr and the run log), after the start, settings and hot-corner lines.
- The click lands on the button itself: after the delay the pointer goes back to the button and clicks there.
- The hot corner still stops the watcher before the click.

## Settings

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

- The file is re-read whenever it changes, as today; a value held by `--delay` or a hot-corner flag is not affected.
- A file that disappears mid-run means the defaults, said through the settings lines; a file that reappears is read like any change.
- `config/release/athc.ini` and `config/dev/athc.ini` keep their values; the "autocontinue requires its settings" comment goes.

## Files to change

- `src/athc/autocontinue/config.py`: `Config` gets `mouse_move_duration: float = 0.0` and `delay_before_continue: float = 1.0` beside `hot_corner: bool = True`, the one place for the defaults; `load_config` reads `load_athc_config().get(SECTION, {})`; `_required_float` becomes `_timing(section, key, default)`, returning the default for a missing key and raising the `Must be a number, 0 or more` error otherwise; the `ATHC_CONFIG_DIR` error goes; the module docstring (lines 3-5, "requires its settings") and the `load_config` docstring (lines 35-37) say the new rule.
- `src/athc/autocontinue/main.py`: the branch for a delay below 0 (find the button, never click) goes; a focus state that starts unknown and says `Waiting for the game window.` or `Game window active.` on the first check and each change; the `auto_continue` docstring (lines 57-58, "The initial load is required") says the new rule; `pyautogui.leftClick()` becomes `pyautogui.leftClick(location.x, location.y)`.
- `config/release/athc.ini`, `config/dev/athc.ini`: the comments in Settings.

## Tests

In `tests/integration/test_autocontinue.py`:

- Defaults: no `athc.ini`, a file with another section only, and a section with one key each give `Config(0.0, 1.0, True)` with the missing values filled.
- The timing validator, once for both keys: `0` accepted, `-0.1` rejected with the line; a non-number rejected with the new wording.
- The loop, with pyautogui stubbed: the first check prints `Game window active.` when the game is already active and `Waiting for the game window.` when it is not, then one line per change, not per pass.
- The loop: a deleted `athc.ini` mid-run applies the defaults and says the changed settings, with no `WARN`.
- The loop: the pointer moved off the button during the delay; the click still lands on the button.
- The loop: the pointer in the top-left corner during the delay, hot corner on; the watcher stops before the click.
- Changed, `test_load_config_errors_when_no_config`, `test_load_config_errors_when_section_missing` and `test_load_config_errors_on_missing_setting`: defaults now, not errors.
- Changed, `test_load_config_errors_on_invalid_value`: the new wording.
- Changed, `test_cli_no_config_exits_2`: runs on the defaults with the loop stubbed, exit 0.
- Unchanged and passing: the focus and signature tests.

Elsewhere:

- `tests/integration/test_config.py`: `test_release_autocontinue_section_loads` keeps passing.
- `tests/integration/README.md`: the autocontinue tables.

## Docs and meta

- `docs/autocontinue/README.md` and `docs/autocontinue/ARCHITECTURE.md`: the defaults, the window lines; the "required settings" paragraphs and the `-1.0` sentence go.
- `config/release/docs/COMMANDS.txt` section 14: the settings sentence.
- `config/release/docs/README.txt`: nothing (no setup step).
- `docs/design/architecture.md`: nothing; autocontinue now follows its Config rule (a missing file, section or key means the in-code defaults).
- `CHANGELOG.md`, `STATUS.md`, `TODO.md` (a 2.0.0 line pointing here).
