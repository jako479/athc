# autocontinue

Watches the screen for the FbPro '98 'Continue' button and clicks it — set it running for unattended sim runs and the game progresses through plays on its own. It also clicks Return at halftime and stops at the end of the game. With `drive_league_pregame` on, it clicks through the league play pre-game screen and starts the game.

## Install

pyautogui (+ Pillow/opencv/numpy) are required dependencies, so any install includes them; it still needs a display + Windows to run. For development:

```bash
uv sync
```

## Usage

```bash
athc autocontinue                     # settings from athc.ini [autocontinue], or the defaults
athc autocontinue --continue-pause 3  # wait 3 s before each Continue click, this run only
athc autocontinue --dry-run           # report what it finds, never click
```

| Option | Meaning |
|---|---|
| `--continue-pause SECONDS` | Seconds to wait before each Continue click, 0 or more; overrides `continue_pause` for one run, through live reloads. Not the halftime wait. |
| `-n, --dry-run` | Scans as usual and reports each sighting (Continue, halftime, the end of the game), never moving the mouse or clicking: a way to check a new monitor or display scaling before trusting it. `--continue-pause` and the hot corner have no effect. |
| `--hot-corner/--no-hot-corner` | Overrides `hot_corner` for one run. |

It looks for the button only while the game is the active window, so switching to another app (which pauses the game) is safe. Ctrl+C stops it, or the hot corner, or the end of the game. Run one copy at a time; two copies both click. Keep the PC unlocked and the screensaver off: Windows hides a locked screen, so nothing can be found or clicked.

Run the game on your **primary monitor** — autocontinue only watches that display. (A single-display VM also works, and keeps your other monitors free.)

## Config

Reads `[autocontinue]` from `athc.ini`, found via `ATHC_CONFIG_DIR` / the default config dir (see [architecture.md](architecture.md#config)) — there is no `--config` flag. Every key is optional: a missing file, section or key means the default, the value the shipped `athc.ini` has, except `drive_league_pregame`, which the shipped file turns on. A key that is present but wrong is an error.

| Setting | Default | Meaning |
|---|---|---|
| `mouse_move_duration` | `0.0` | Seconds to move the mouse to the button, 0 or more (`0.0` = instant). |
| `continue_pause` | `1.0` | Seconds to wait before each Continue click, 0 or more (`0.0` = instant). |
| `halftime_pause` | `8.0` | Seconds to wait at halftime before clicking Return, 0 or more. |
| `hot_corner` | `true` | Stop when the mouse hits the top-left corner. |
| `drive_league_pregame` | `false` (`true` in the shipped file) | Click through the league play pre-game screen, then Game. |
| `plans_profiles_pause` | `1.5` | Seconds to wait after clicking Plans/Profiles, and again after Visitor; `0` skips both clicks. |
| `conditions_pause` | `2.5` | Seconds to wait after clicking Conditions; `0` skips the click. |
| `venues_pause` | `1.5` | Seconds to wait after clicking Venues; `0` skips the click. |

The timings have no upper limit. `halftime_pause` has no command-line option, and `--continue-pause` does not affect it. The file is re-read whenever it changes, so edits apply while it runs; a value held by `--continue-pause` or a hot-corner flag is not affected. A deleted file means the defaults again; a file that comes back is read like any change.

## Lines and exit codes

Status lines go to stderr and the run log; a dry run's sightings and `Stopped.` go to stdout and the run log.

| When | Line | Exit |
|---|---|---|
| start | `Watching for the Continue button. Press Ctrl+C to stop.` | |
| the settings, at start and when a reload changes one | `mouse_move_duration = 0.0`, `continue_pause = 1.0`, `halftime_pause = 8.0`, `drive_league_pregame = true`, `plans_profiles_pause = 1.5`, `conditions_pause = 2.5`, `venues_pause = 1.5`; with `--continue-pause 3`, `continue_pause = 3.0 (--continue-pause)` once at start | |
| hot corner on | `Hot corner on: move the mouse to the top-left corner to stop.` | |
| hot corner off, or a dry run | `Hot corner off: press Ctrl+C to stop.` | |
| a dry run, at start | `Dry run: what it finds is reported, never clicked.` | |
| the first check, and each time the game stops being the active window | `Waiting for the game window.` | |
| the first check, and each time the game becomes the active window | `Game window active.` | |
| a dry run, each sighting | `Continue button found at 812, 640.` | |
| halftime | `Halftime label found at 400, 120.`, `Return button found at 960, 700.`, `Waiting 8 seconds.`, then `Return button clicked.` | |
| the end of the game | `Results label found at 400, 120.`, `Return button found at 960, 700.`, then `Stopped.` | 0 |
| a dry run, at halftime or the end of the game | the same label and Return lines, without `Waiting ...`; the end of the game stops it | |
| the league play pre-game screen, with `drive_league_pregame` on | `League play label found at 571, 38.`, then `Plans/profiles button clicked.`, `Visitor button clicked.`, `Conditions button clicked.`, `Venues button clicked.`, `Game button clicked.`, less any a pause of 0 skips | |
| a dry run, on the pre-game screen | the label line, then `Plans/profiles button found at 154, 496.` or `Plans/profiles button not found.`, and so on for each button it would click | |
| just before a pre-game click, the screen gone (the coach clicked Game) or the button not found | `League play label gone; Visitor button not clicked.` or `Visitor button not found; not clicked.` | |
| just before a click, the button already gone (the coach clicked it) | `Continue button gone; not clicked.`; at halftime `Halftime label gone; Return not clicked.` or `Return button gone; not clicked.` | |
| just before a click, the button no longer under the spot found (the window was dragged) | `Continue button moved; not clicked.` or `Return button moved; not clicked.` | |
| a reload that fails | `WARN <athc.ini>: <why> Keeping the previous settings.` | |
| the screen hidden | `WARN The screen is locked, a screensaver is on, or Remote Desktop is disconnected. Retrying in 60 seconds.` | |
| any other failure in a pass, the first of its kind | `WARN Unexpected <error type>: <why>. See <athc.log> for details. Retrying in 5 seconds.`, the traceback in the run log | |
| the same failure again | `WARN Unexpected <error type>: <why>. Retrying in 5 seconds.` | |
| stop by Ctrl+C | `Ctrl+C pressed.`, then `Stopped.` | 0 |
| stop by the hot corner | `Hot corner hit.`, then `Stopped.` | 0 |
| stop at the end of the game | `Stopped.` (the Results lines say why) | 0 |
| a bad timing at start | `FAIL <athc.ini>: [autocontinue] continue_pause: Must be a number, 0 or more, got '-1.0'.` | 2 |
| a bad `hot_corner` at start | `FAIL <athc.ini>: [autocontinue] hot_corner: Must be true or false, got 'maybe'.` | 2 |
| pyautogui missing | `FAIL Missing pyautogui. Reinstall athc.` | 2 |
| an image missing or unreadable | `FAIL <image>: <why> Reinstall athc.` | 2 |
| an argument, or a `--continue-pause` that is not a number 0 or more | Click's `Error: ...` | 2 |

`Waiting` says `1 second` for a pause of 1. Every click is said except Continue, which comes 100 or more times a game. At start: the start line, the seven settings, the hot-corner line, the dry-run line, then the first window line. The shared scheme: [architecture.md](architecture.md#console-run-log-and-errors).

## Tests

`pytest tests/integration/test_autocontinue.py` covers config loading, a test per setting (missing, `-1` and `0`), change detection, the CLI with the loop stubbed, the loop on a stand-in desktop (window, screen, mouse and clock faked), and the shipped images on real game screenshots (`tests/integration/data/autocontinue_screens`), searched as in a run: every button it acts on with the game's pointer elsewhere, resting on it and lighting it, where the game has that look; the league play pre-game driven to Game with the pointer on each button; the pre-game left alone with `drive_league_pregame` off, and the exhibition pre-game left alone either way; and screens with nothing to act on (the coin toss, the league schedule, the Controllers screen). Each match cutoff is tested from both sides, on screens scoring just over and just under it. `tests/integration/test_autocontinue_game.py` is the real game: slow tests, run on demand with `uv run pytest -m slow tests/integration/test_autocontinue_game.py --no-cov`. In Windows Sandbox one plays an exhibition game with 6-minute quarters while a helper lights half the buttons as they show, moves the pointer off a quarter, and leaves it on a quarter it is already on, and checks the halftime click and the end-of-game stop; two take a league game to its pre-game screen and check it is driven to Game, and the screen left, with `drive_league_pregame` on, and left alone with it off. It needs Windows Sandbox, a built installer (`packaging/release-build.ps1`) and the game installed, with `ATHC_GAME_DIR` set to the folder holding `FbPro98`. Each test builds its own game in its temp folder: the game's own files from that install, as `tests/integration/game-files.txt` lists them, with the test league, each team's plans and profiles, `SETUP.INI` and an empty disc image laid over them; the sandbox plays that copy, so the install and the dev's own settings and leagues never matter. Fast tests in the same file check that build without a Sandbox. Every case: [test-matrix-autocontinue.md](../tests/integration/test-matrix-autocontinue.md).

## How it works

- Only scans while the game is the foreground window (`GetForegroundWindow` title match) — the game auto-pauses on focus loss, so this keeps it from clicking while the commish is in another app. Works windowed or fullscreen (the window keeps its title either way). While the game is not active it checks again every 2 s.
- Loads its twelve images once at start (grayscale, as the matcher reads them); a missing or unreadable image is a broken install.
- Takes one screenshot of the primary display a second, turns it gray once, and checks it, in order, for the Results label, the Halftime label, the League play label (only with `drive_league_pregame` on), then the Continue button (PyAutoGUI grayscale match, confidence 0.8). A Results or Halftime label counts only with the Return button on screen too; the League play label counts only with the Game button, since it also shows on other league screens, like the schedule. A label without its button means scan again next second.
- Return and Game are matched at 0.6, drawn or lit up: the game draws its own hand pointer, which sits on Return through the halftime pause and on Game where Accept was clicked. Measured on real screens, they score 0.77 and 0.72 under it, and nothing else on their screens scores above 0.50. Venues is matched at 0.7: 0.77 with the pointer resting on it, against 0.56 for the best other spot on the Conditions page it is searched on. The other pre-game buttons score over 0.8 under the pointer.
- On the league play pre-game screen, clicks Plans/Profiles, Visitor, Conditions, Venues, then Game, waiting each one's pause after its click (4 s after Game); a pause of 0 skips its click, and the Plans/Profiles pause skips Visitor too. Plans/Profiles is clicked even though league play opens on it. Before each click it checks the game is still the active window and takes a fresh screenshot to check the screen and the button are still there. A screen gone means no more clicks; a button not found means no more clicks and an 8 s wait, after which the next scan starts over. A dry run reports the label and each button it would click, found or not, then waits 8 s.
- On the Continue button, moves the mouse there over `mouse_move_duration` seconds, waits the delay, checks the game is still the active window, takes a fresh screenshot to check Continue is still there, clicks on the button itself (back on it if the mouse moved), then waits 4 s. A dry run reports the hit instead and waits 8 s.
- At halftime, moves the mouse instantly to Return, so it is clear of the halftime stats, waits `halftime_pause` seconds, checks the game is still the active window, takes a fresh screenshot to check the Halftime label and Return are still there, clicks Return, then waits 4 s. A dry run reports it instead and waits 8 s.
- The check before a click is there because the coach may have clicked the button himself, or dragged the window, during the wait: a button that is gone, or no longer under the spot the scan found, is never clicked; it says so and goes back to scanning. The game window is checked once more right before the click, so a click never lands in another app. The game draws its own mouse pointer over the button; this check matches as the scan does (0.8 for Continue, 0.6 for Return), since the mouse also stays on Continue for the next scan after every click.
- At the end of the game, moves the mouse instantly to Return and stops, without a click. A dry run reports it and stops too.
- Re-reads the INI only when the file changes on disk (`config_signature` fingerprints path/mtime/size), so settings tune live; a reload that fails validation is a `WARN` and the old settings are kept.
- When Windows hides the screen (locked, screensaver, disconnected Remote Desktop) the grab fails; it warns and backs off 60 s so the log doesn't flood.
- Any other failure in a pass is a `WARN` and a retry 5 s later, for as long as it lasts, never the end of the run: an unattended game would otherwise sit at the next Continue. The first failure of each kind writes its traceback to the run log and names the log; a repeat is one line.
- Each search covers the whole screenshot, so a change of screen size while it runs (the game going full screen) needs nothing.
- The hot corner is pyautogui's own fail-safe, pinned to the top-left corner (`FAILSAFE_POINTS`) so the other three stay free. pyautogui checks it inside its own mouse calls (the move to a button and the click); the loop adds no check of its own, so a dry run, which makes no mouse calls, cannot use it, and the corner hit during the halftime pause stops it at the Return click. A stop by the corner goes through the Ctrl+C path: `Stopped.`, exit 0.

### Layout

```
src/athc/autocontinue/
├── __init__.py
├── config.py        # Config (the defaults), load_config, config_signature, get_runtime_path
├── main.py          # auto_continue() watch loop, screen helpers (pyautogui, ctypes)
└── images/                   # pyautogui match targets (package_data)
    ├── continue_button.png
    ├── halftime_label.png
    ├── return_button.png     # the Return button, at halftime and the end of the game
    ├── return_highlight_button.png  # the same, lit up by the mouse on it
    ├── results_label.png
    ├── league_play_label.png        # the league play pre-game screen
    ├── plans_profiles_button.png
    ├── visitor_button.png
    ├── conditions_button.png
    ├── venues_button.png
    ├── game_button.png
    └── game_highlight_button.png    # Game, lit up by the mouse on it

src/athc/cli/autocontinue.py  # Click command; lazy-imports main so pyautogui loads only on run
```

### Boundaries

- **Windows-only** — reads the foreground window's title via `ctypes.windll.user32`; pyautogui makes the process DPI-aware when it loads.
- **Primary monitor only** — pyautogui/`ImageGrab` captures the primary display, so the game must run there. A single-display VM sidesteps this (the guest has one monitor, freeing the host's other monitors). Full multi-monitor support is out of scope (PIL has known multi-monitor/negative-coordinate bugs).
- No `--config` flag — config is `config_dir()/athc.ini` (`ATHC_CONFIG_DIR`), per [architecture.md](architecture.md#config); tests isolate by setting that env var.
- `--continue-pause` and `--hot-corner/--no-hot-corner` (default unset) override their `athc.ini` values; unset, the config wins. The overrides hold across live reloads.
- pyautogui (+ opencv-python, which backs the confidence-based image match) is a **required dependency**, but the CLI still lazy-imports `main` so discovery and `--help` work even on a broken install; running without it then prints `FAIL Missing pyautogui. Reinstall athc.` and exits 2.
- Sees pixels only — never inspects or edits game files.
- No single-instance guard: run one copy at a time.
