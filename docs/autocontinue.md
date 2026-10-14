# autocontinue

Watches the screen for the FbPro '98 'Continue' button and clicks it — set it running for unattended sim runs and the game progresses through plays on its own.

## Install

pyautogui (+ Pillow/opencv) are required dependencies, so any install includes them; it still needs a display + Windows to run. For development:

```bash
uv sync
```

## Usage

```bash
athc autocontinue   # settings from athc.ini [autocontinue]
```

`CTRL-C` stops it, or move the mouse to the top-left screen corner (the "hot corner", on by default; disable with `--no-hot-corner` or `hot_corner = false`). It only clicks while the game is the active window, so switching to another app (which pauses the game) is safe. The INI is re-read whenever the file changes, so edits apply while it runs. Its status (`AutoContinue is RUNNING...`, the settings in use) prints on stderr and in the run log; a failed config reload, or a screen that is locked, behind a screensaver or in a disconnected Remote Desktop session, is a `WARN` line and it keeps going. Stopping prints `Shutting down AutoContinue`, exit `0`. A config error, a missing pyautogui, or a missing or unreadable button image is `FAIL <why>`, exit `2`. Shared console and codes: [architecture](architecture.md#console-run-log-and-errors).

Run the game on your **primary monitor** — autocontinue only watches that display. (A single-display VM also works, and keeps your other monitors free.)

## Config

Reads `[autocontinue]` from `athc.ini`, found via `ATHC_CONFIG_DIR` / the default config dir (see [architecture.md](architecture.md#config)) — there is no `--config` flag. Unlike most tools, both settings are **required** (a clicking watcher shouldn't run on guessed timings); a missing section or setting is an error.

| Setting | Meaning |
|---|---|
| `mouse_move_duration` | Seconds to move the mouse to the button (`0.0` = instant). |
| `delay_before_continue` | Seconds to wait before clicking. `0.0` = instant; `-1.0` = find but don't click. |
| `hot_corner` | Stop when the mouse hits the top-left corner. Optional; missing = enabled. |

`-1.0` is useful for detection-only logging when the game already auto-advances. The two timing settings are required; `hot_corner` is optional. `--hot-corner/--no-hot-corner` overrides it for one run.

## Tests

`pytest tests/integration/test_autocontinue.py` covers config loading, change detection, and the CLI. The image-matching watch loop is manual-only — it depends on the live display.

## How it works

- Only scans while the game is the foreground window (`GetForegroundWindow` title match) — the game auto-pauses on focus loss, so this keeps it from clicking while the commish is in another app. Works windowed or fullscreen (the window keeps its title either way).
- Loads `continue_button.png` once at start (grayscale, as the matcher reads it); a missing or unreadable image is a broken install: `FAIL <image>: <why> Reinstall athc.`, exit 2.
- Polls the primary display for that image (PyAutoGUI grayscale match, confidence 0.8): one search per loop, paced by `_SCAN_INTERVAL`. We don't use pyscreeze's `minSearchTime` — its retry loop has no sleep (busy-loops a core), so we pace it ourselves.
- On a hit, moves the mouse there over `mouse_move_duration` seconds and clicks after `delay_before_continue`.
- Re-reads the INI only when the file changes on disk (`config_signature` fingerprints path/mtime/size), so settings tune live; a reload that fails validation is logged and the old settings kept.
- When Windows hides the screen (locked, screensaver, disconnected Remote Desktop) the grab fails: `WARN The screen is locked, a screensaver is on, or Remote Desktop is disconnected. Retrying in 60 seconds.`, then it backs off `_LOCKED_SCREEN_BACKOFF` seconds so the log doesn't flood.
- Stops on Ctrl-C, or — when the **hot corner** is enabled (default) — when the cursor reaches the top-left corner. The fail-safe is pinned to that one corner (`FAILSAFE_POINTS`), so the other three stay free, and is funneled through the Ctrl-C path so both exit cleanly. `hot_corner = false` (or `--no-hot-corner`) disables it, leaving Ctrl-C only; on launch the watcher logs which mode is active (info).
- `ConfigFileError` covers a missing file, a missing `[autocontinue]` section, a missing/non-numeric timing setting, or a non-boolean `hot_corner` → a `FAIL` line, exit 2; a missing or blank `hot_corner` means enabled.

### Layout

```
src/athc/autocontinue/
├── __init__.py
├── config.py        # Config, load_config (raises ConfigFileError), config_signature, get_runtime_path
├── main.py          # auto_continue() watch loop, screen helpers (pyautogui, ctypes)
└── images/
    └── continue_button.png   # pyautogui match target (package_data)

src/athc/cli/autocontinue.py  # Click command; lazy-imports main so pyautogui loads only on run
```

### Boundaries

- **Windows-only** — queries screen size via `ctypes.windll.user32` with DPI-awareness.
- **Primary monitor only** — pyautogui/`ImageGrab` captures the primary display, so the game must run there. A single-display VM sidesteps this (the guest has one monitor, freeing the host's other monitors). Full multi-monitor support is out of scope (PIL has known multi-monitor/negative-coordinate bugs).
- No `--config` flag — config is `config_dir()/athc.ini` (`ATHC_CONFIG_DIR`), per [architecture.md](architecture.md#config); tests isolate by setting that env var.
- `--hot-corner/--no-hot-corner` (default unset) overrides the `hot_corner` config value; unset, the config wins. The override holds across live reloads.
- pyautogui (+ opencv-python, which backs the confidence-based image match) is a **required dependency**, but the CLI still lazy-imports `main` so discovery and `--help` work even on a broken install; running without it then prints `FAIL Missing pyautogui. Reinstall athc.` and exits 2.
- Sees pixels only — never inspects or edits game files.
- The watch loop is **manual-tested only** (depends on the live display). `config.py` + the CLI are covered by `pytest`.

### Exit codes

| Exit | Meaning |
|---|---|
| `0` | **Done** — ran, including a clean Ctrl-C stop. |
| `2` | **Error** — a `FAIL` line: config missing/invalid, pyautogui not installed or the button image missing/unreadable (reinstall hint); or usage, bad arguments (Click). |

The shared scheme: [architecture.md](architecture.md#console-run-log-and-errors).
