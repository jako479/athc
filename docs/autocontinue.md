# autocontinue

Watches the screen for the FbPro '98 'Continue' button and clicks it — set it running for unattended sim runs and the game progresses through plays on its own.

## Install

pyautogui (+ Pillow/opencv) are required dependencies, so any install includes them; it still needs a display + Windows to run. For development:

```bash
uv sync
```

## Usage

```bash
athc autocontinue              # settings from athc.ini [autocontinue], or the defaults
athc autocontinue --delay 3    # wait 3 s before each click, this run only
athc autocontinue --dry-run    # report the button, never click
```

| Option | Meaning |
|---|---|
| `--delay SECONDS` | Seconds to wait before each click, 0 or more; overrides `delay_before_continue` for one run, through live reloads. |
| `-n, --dry-run` | Finds the button as usual and reports each sighting, never moving the mouse or clicking: a way to check a new monitor or display scaling before trusting it. `--delay` and the hot corner have no effect. |
| `--hot-corner/--no-hot-corner` | Overrides `hot_corner` for one run. |

It looks for the button only while the game is the active window, so switching to another app (which pauses the game) is safe. Ctrl+C stops it, or the hot corner. Run one copy at a time; two copies both click. Keep the PC unlocked and the screensaver off: Windows hides a locked screen, so nothing can be found or clicked.

Run the game on your **primary monitor** — autocontinue only watches that display. (A single-display VM also works, and keeps your other monitors free.)

## Config

Reads `[autocontinue]` from `athc.ini`, found via `ATHC_CONFIG_DIR` / the default config dir (see [architecture.md](architecture.md#config)) — there is no `--config` flag. Every key is optional: a missing file, section or key means the default, the value the shipped `athc.ini` has. A key that is present but wrong is an error.

| Setting | Default | Meaning |
|---|---|---|
| `mouse_move_duration` | `0.0` | Seconds to move the mouse to the button, 0 or more (`0.0` = instant). |
| `delay_before_continue` | `1.0` | Seconds to wait before each click, 0 or more (`0.0` = instant). |
| `hot_corner` | `true` | Stop when the mouse hits the top-left corner. |

The timings have no upper limit. The file is re-read whenever it changes, so edits apply while it runs; a value held by `--delay` or a hot-corner flag is not affected. A deleted file means the defaults again; a file that comes back is read like any change.

## Lines and exit codes

Status lines go to stderr and the run log; a dry run's sightings and `Stopped.` go to stdout and the run log.

| When | Line | Exit |
|---|---|---|
| start | `Watching for the Continue button. Press Ctrl+C to stop.` | |
| the settings, at start and when a reload changes one | `mouse_move_duration = 0.0`, `delay_before_continue = 1.0`; with `--delay 3`, `delay_before_continue = 3.0 (--delay)` once at start | |
| hot corner on | `Hot corner on: move the mouse to the top-left corner to stop.` | |
| hot corner off, or a dry run | `Hot corner off: press Ctrl+C to stop.` | |
| a dry run, at start | `Dry run: the Continue button is reported, never clicked.` | |
| the first check, and each time the game stops being the active window | `Waiting for the game window.` | |
| the first check, and each time the game becomes the active window | `Game window active.` | |
| a dry run, each sighting | `Continue button found at 812, 640.` | |
| a reload that fails | `WARN <athc.ini>: <why> Keeping the previous settings.` | |
| the screen hidden | `WARN The screen is locked, a screensaver is on, or Remote Desktop is disconnected. Retrying in 60 seconds.` | |
| stop: Ctrl+C, or the hot corner | `Stopped.` | 0 |
| a bad timing at start | `FAIL <athc.ini>: [autocontinue] delay_before_continue: Must be a number, 0 or more, got '-1.0'.` | 2 |
| a bad `hot_corner` at start | `FAIL <athc.ini>: [autocontinue] hot_corner: Must be true or false, got 'maybe'.` | 2 |
| pyautogui missing | `FAIL Missing pyautogui. Reinstall athc.` | 2 |
| the button image missing or unreadable | `FAIL <image>: <why> Reinstall athc.` | 2 |
| an argument, or a `--delay` that is not a number 0 or more | Click's `Error: ...` | 2 |

At start: the start line, the two settings, the hot-corner line, the dry-run line, then the first window line. The shared scheme: [architecture.md](architecture.md#console-run-log-and-errors).

## Tests

`pytest tests/integration/test_autocontinue.py` covers config loading and the defaults, change detection, the CLI with the loop stubbed, and the loop on a stand-in desktop (window, screen, mouse and clock faked). Live image matching stays manual — it depends on the display.

## How it works

- Only scans while the game is the foreground window (`GetForegroundWindow` title match) — the game auto-pauses on focus loss, so this keeps it from clicking while the commish is in another app. Works windowed or fullscreen (the window keeps its title either way). While the game is not active it checks again every 2 s.
- Loads `continue_button.png` once at start (grayscale, as the matcher reads it); a missing or unreadable image is a broken install.
- Polls the primary display for that image (PyAutoGUI grayscale match, confidence 0.8): one search a second. We don't use pyscreeze's `minSearchTime` — its retry loop has no sleep (busy-loops a core), so we pace it ourselves.
- On a hit, moves the mouse there over `mouse_move_duration` seconds, waits the delay, clicks on the button itself (back on it if the mouse moved), then waits 4 s. A dry run reports the hit instead and waits 8 s.
- Re-reads the INI only when the file changes on disk (`config_signature` fingerprints path/mtime/size), so settings tune live; a reload that fails validation is a `WARN` and the old settings are kept.
- When Windows hides the screen (locked, screensaver, disconnected Remote Desktop) the grab fails; it warns and backs off 60 s so the log doesn't flood.
- The hot corner is pyautogui's own fail-safe, pinned to the top-left corner (`FAILSAFE_POINTS`) so the other three stay free. pyautogui checks it inside its own mouse calls (the move to the button and the click); the loop adds no check of its own, so a dry run, which makes no mouse calls, cannot use it. A stop by the corner goes through the Ctrl+C path: `Stopped.`, exit 0.
- After the game ends it keeps scanning, and clicks nothing unless the button appears, until stopped; there is no timed stop.

### Layout

```
src/athc/autocontinue/
├── __init__.py
├── config.py        # Config (the defaults), load_config, config_signature, get_runtime_path
├── main.py          # auto_continue() watch loop, screen helpers (pyautogui, ctypes)
└── images/
    └── continue_button.png   # pyautogui match target (package_data)

src/athc/cli/autocontinue.py  # Click command; lazy-imports main so pyautogui loads only on run
```

### Boundaries

- **Windows-only** — queries screen size via `ctypes.windll.user32` with DPI-awareness.
- **Primary monitor only** — pyautogui/`ImageGrab` captures the primary display, so the game must run there. A single-display VM sidesteps this (the guest has one monitor, freeing the host's other monitors). Full multi-monitor support is out of scope (PIL has known multi-monitor/negative-coordinate bugs).
- No `--config` flag — config is `config_dir()/athc.ini` (`ATHC_CONFIG_DIR`), per [architecture.md](architecture.md#config); tests isolate by setting that env var.
- `--delay` and `--hot-corner/--no-hot-corner` (default unset) override their `athc.ini` values; unset, the config wins. The overrides hold across live reloads.
- pyautogui (+ opencv-python, which backs the confidence-based image match) is a **required dependency**, but the CLI still lazy-imports `main` so discovery and `--help` work even on a broken install; running without it then prints `FAIL Missing pyautogui. Reinstall athc.` and exits 2.
- Sees pixels only — never inspects or edits game files.
- No single-instance guard: run one copy at a time.
