# autocontinue

Watches the screen for the FbPro '98 'Continue' button and clicks it — set it running for unattended sim runs and the game progresses through plays on its own.

## Install

Needs a display + Windows, so it ships as an optional extra (not in the core install):

```bash
uv pip install -e ".[autocontinue]"
```

## Usage

```bash
athc autocontinue   # settings from athc.ini [autocontinue]
```

`CTRL-C` stops it; move the mouse to a screen corner for PyAutoGUI's fail-safe. The INI is re-read whenever the file changes, so edits apply while it runs. Exit `0` (clean / Ctrl-C), `1` (config error), `2` (pyautogui not installed).

## Config

Reads `[autocontinue]` from `athc.ini`, found via `ATHC_CONFIG_DIR` / the default config dir (see [../design/config.md](../design/config.md)) — there is no `--config` flag. Unlike most tools, both settings are **required** (a clicking watcher shouldn't run on guessed timings); a missing section or setting is an error.

| Setting | Meaning |
|---|---|
| `mouse_move_duration` | Seconds to move the mouse to the button (`0.0` = instant). |
| `delay_before_continue` | Seconds to wait before clicking. `0.0` = instant; `-1.0` = find but don't click. |

`-1.0` is useful for detection-only logging when the game already auto-advances.

## Tests

`pytest tests/integration/test_autocontinue.py` covers config loading, change detection, and the CLI. The image-matching watch loop is manual-only — it depends on the live display.
