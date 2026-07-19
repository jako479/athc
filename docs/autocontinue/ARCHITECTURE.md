# autocontinue — Architecture

A `athc autocontinue` command that polls the screen for the FbPro '98 'Continue' button and clicks it, so unattended sim runs progress without manual clicking.

## Layout

```
src/athc/autocontinue/
├── __init__.py
├── config.py        # Config, ConfigError, load_config, config_signature, get_runtime_path
├── main.py          # auto_continue() watch loop, screen helpers (pyautogui, ctypes)
└── images/
    └── continue_button.png   # pyautogui match target (package_data)

src/athc/cli/autocontinue.py  # Click command; lazy-imports main so pyautogui loads only on run
```

## How it works

- Only scans while the game is the foreground window (`GetForegroundWindow` title match) — the game auto-pauses on focus loss, so this keeps it from clicking while the commish is in another app. Works windowed or fullscreen (the window keeps its title either way).
- Polls the primary display for `continue_button.png` (PyAutoGUI grayscale match, confidence 0.8): one search per loop, paced by `_SCAN_INTERVAL`. We don't use pyscreeze's `minSearchTime` — its retry loop has no sleep (busy-loops a core), so we pace it ourselves.
- On a hit, moves the mouse there over `mouse_move_duration` seconds and clicks after `delay_before_continue`.
- Re-reads the INI only when the file changes on disk (`config_signature` fingerprints path/mtime/size), so settings tune live; a reload that fails validation is logged and the old settings kept.
- Backs off `_LOCKED_SCREEN_BACKOFF` seconds when a screen grab fails (e.g. locked workstation) so the log doesn't flood.
- Stops on Ctrl-C, or — when the **hot corner** is enabled (default) — when the cursor reaches the top-left corner. The fail-safe is pinned to that one corner (`FAILSAFE_POINTS`), so the other three stay free, and is funneled through the Ctrl-C path so both exit cleanly. `hot_corner = false` (or `--no-hot-corner`) disables it, leaving Ctrl-C only; on launch the watcher logs which mode is active (info).

## Boundaries

- **Windows-only** — queries screen size via `ctypes.windll.user32` with DPI-awareness.
- **Primary monitor only** — pyautogui/`ImageGrab` captures the primary display, so the game must run there. A single-display VM sidesteps this (the guest has one monitor, freeing the host's other monitors). Full multi-monitor support is out of scope (PIL has known multi-monitor/negative-coordinate bugs).
- No `--config` flag — config is `config_dir()/athc.ini` (`ATHC_CONFIG_DIR`), per [config.md](../design/config.md); tests isolate by setting that env var.
- `--hot-corner/--no-hot-corner` (default unset) overrides the `hot_corner` config value; unset, the config wins. The override holds across live reloads.
- pyautogui (+ opencv-python, which backs the confidence-based image match) is a **required dependency**, but the CLI still lazy-imports `main` so discovery and `--help` work even on a broken install; running without it then exits 1 with a "reinstall" hint.
- Sees pixels only — never inspects or edits game files.
- The watch loop is **manual-tested only** (depends on the live display). `config.py` + the CLI are covered by `pytest`.

## Config

`athc.ini [autocontinue]`; the two timing settings are required (no silent defaults):

| Setting | Meaning |
|---|---|
| `mouse_move_duration` | Seconds to move the mouse to the button (`0.0` = instant). |
| `delay_before_continue` | Seconds before clicking; `0.0` instant, `-1.0` finds but doesn't click. |
| `hot_corner` | Optional bool; stop on the top-left corner. Missing/blank → enabled. |

`ConfigError` covers a missing file, a missing `[autocontinue]` section, a missing/non-numeric timing setting, or a non-boolean `hot_corner` → the CLI logs it and exits 1.

## Exit codes

| Exit | Meaning |
|---|---|
| `0` | **OK** — ran, including a clean Ctrl-C stop. |
| `1` | **Error** — config missing/invalid, or pyautogui not installed (reinstall hint). |
| `2` | **Usage** — bad arguments (Click). |
