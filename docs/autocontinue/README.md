# autocontinue

Watches the screen for the FbPro '98 'Continue' button and clicks it — set it running for unattended sim runs and the game progresses through plays on its own.

## Install

pyautogui (+ Pillow/opencv) are required dependencies, so any install includes them; it still needs a display + Windows to run. For development:

```bash
uv pip install -e ".[dev]"
```

## Usage

```bash
athc autocontinue   # settings from athc.ini [autocontinue]
```

`CTRL-C` stops it, or move the mouse to the top-left screen corner (the "hot corner", on by default; disable with `--no-hot-corner` or `hot_corner = false`). It only clicks while the game is the active window, so switching to another app (which pauses the game) is safe. The INI is re-read whenever the file changes, so edits apply while it runs. Exit `0` (clean stop), `1` (config error or pyautogui not installed).

Run the game on your **primary monitor** — autocontinue only watches that display. (A single-display VM also works, and keeps your other monitors free.)

## Config

Reads `[autocontinue]` from `athc.ini`, found via `ATHC_CONFIG_DIR` / the default config dir (see [../design/config.md](../design/config.md)) — there is no `--config` flag. Unlike most tools, both settings are **required** (a clicking watcher shouldn't run on guessed timings); a missing section or setting is an error.

| Setting | Meaning |
|---|---|
| `mouse_move_duration` | Seconds to move the mouse to the button (`0.0` = instant). |
| `delay_before_continue` | Seconds to wait before clicking. `0.0` = instant; `-1.0` = find but don't click. |
| `hot_corner` | Stop when the mouse hits the top-left corner. Optional; missing = enabled. |

`-1.0` is useful for detection-only logging when the game already auto-advances. The two timing settings are required; `hot_corner` is optional. `--hot-corner/--no-hot-corner` overrides it for one run.

## Tests

`pytest tests/integration/test_autocontinue.py` covers config loading, change detection, and the CLI. The image-matching watch loop is manual-only — it depends on the live display.
