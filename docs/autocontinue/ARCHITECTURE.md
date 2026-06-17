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

- Polls the primary display for `continue_button.png` (PyAutoGUI grayscale match, confidence 0.8).
- On a hit, moves the mouse there over `mouse_move_duration` seconds and clicks after `delay_before_continue`.
- Re-reads the INI only when the file changes on disk (`config_signature` fingerprints path/mtime/size), so settings tune live; a reload that fails validation is logged and the old settings kept.
- Backs off `_LOCKED_SCREEN_BACKOFF` seconds when a screen grab fails (e.g. locked workstation) so the log doesn't flood.

## Boundaries

- **Windows-only** — queries screen size via `ctypes.windll.user32` with DPI-awareness.
- No `--config` flag — config is `config_dir()/athc.ini` (`ATHC_CONFIG_DIR`), per [config.md](../design/config.md); tests isolate by setting that env var.
- pyautogui is an **optional extra**; the CLI lazy-imports `main`, so discovery and `--help` work without it, and running without it exits 2 with an install hint.
- Sees pixels only — never inspects or edits game files.
- The watch loop is **manual-tested only** (depends on the live display). `config.py` + the CLI are covered by `pytest`.

## Config

`athc.ini [autocontinue]`, both settings required (no silent defaults):

| Setting | Meaning |
|---|---|
| `mouse_move_duration` | Seconds to move the mouse to the button (`0.0` = instant). |
| `delay_before_continue` | Seconds before clicking; `0.0` instant, `-1.0` finds but doesn't click. |

`ConfigError` covers a missing file, a missing `[autocontinue]` section, or a missing/non-numeric setting → the CLI logs it and exits 1.
