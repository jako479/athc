# autocontinue

Watches the screen for the FbPro '98 'Continue' button and clicks it — set it running for unattended sim runs and the game progresses through plays on its own. It also clicks Return at halftime and stops at the end of the game. With `drive_league_pregame` on, it clicks through the league play pre-game screen and starts the game.

Usage, options, settings, lines and exit codes: [usage/autocontinue.txt](../usage/autocontinue.txt).

## Install

pyautogui (+ Pillow/opencv/numpy) are required dependencies, so any install includes them; it still needs a display + Windows to run. For development:

```bash
uv sync
```

## Tests

`pytest tests/integration/test_autocontinue.py` covers config loading, a test per setting (missing, `-1` and `0`), change detection, the CLI with the loop stubbed, the loop on a stand-in desktop (window, screen, mouse and clock faked), and the shipped images on real game screenshots (`tests/integration/data/autocontinue_screens`), searched as in a run: every button it acts on with the game's pointer elsewhere, resting on it and lighting it, where the game has that look; the league play pre-game driven to Game with the pointer on each button; the pre-game left alone with `drive_league_pregame` off, and the exhibition pre-game left alone either way; and screens with nothing to act on (the coin toss, the league schedule, the Controllers screen). Each match cutoff is tested from both sides, on screens scoring just over and just under it. `tests/integration/test_autocontinue_game.py` is the real game: slow tests, run on demand with `uv run pytest -m slow tests/integration/test_autocontinue_game.py --no-cov`. In Windows Sandbox one plays an exhibition game with 6-minute quarters while a helper lights half the buttons as they show, moves the pointer off a quarter, and leaves it on a quarter it is already on, and checks the halftime click and the end-of-game stop; two take a league game to its pre-game screen and check it is driven to Game, and the screen left, with `drive_league_pregame` on, and left alone with it off. It needs Windows Sandbox, a built installer (`packaging/release-build.ps1`) and the game installed, with `ATHC_GAME_DIR` set to the folder holding `FbPro98`. Each test builds its own game in its temp folder: the game's own files from that install, as `tests/integration/game-files.txt` lists them, with the test league, each team's plans and profiles, `SETUP.INI` and an empty disc image laid over them; the sandbox plays that copy, so the install and the dev's own settings and leagues never matter. Fast tests in the same file check that build without a Sandbox. Every case: [test-matrix-autocontinue.md](../../tests/integration/test-matrix-autocontinue.md).

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
- Re-reads athc.toml only when the file changes on disk (`config_signature` fingerprints path/mtime/size), so settings tune live; a reload that fails validation is a `WARN` and the old settings are kept.
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
- No `--config` flag — config is `config_dir()/athc.toml` (`ATHC_CONFIG_DIR`), per [architecture.md](architecture.md#config); tests isolate by setting that env var.
- `--continue-pause` and `--hot-corner/--no-hot-corner` (default unset) override their `athc.toml` values; unset, the config wins. The overrides hold across live reloads.
- pyautogui (+ opencv-python, which backs the confidence-based image match) is a **required dependency**, but the CLI still lazy-imports `main` so discovery and `--help` work even on a broken install; running without it then prints `FAIL Missing pyautogui. Reinstall athc.` and exits 2.
- Sees pixels only — never inspects or edits game files.
- No single-instance guard: run one copy at a time.
