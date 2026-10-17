# autocontinue — Test Matrix

Cases for `athc autocontinue`, in [test_autocontinue.py](test_autocontinue.py) and [test_autocontinue_game.py](test_autocontinue_game.py) (the Sandbox tests slow). Design: [autocontinue.md](../../docs/autocontinue.md).

Config is `athc.ini [autocontinue]`, every key optional; the `config_dir` fixture isolates `ATHC_CONFIG_DIR`. The CLI is tested with `auto_continue` stubbed, and the loop on a stand-in desktop (`Desktop`: the game window, the screen, pyautogui's mouse calls and the clock), so nothing touches the screen or the mouse; a pass that clicks takes two screenshots, the scan and the check just before the click. Exit 0 stopped (Ctrl+C, the hot corner or the end of the game) / 2 error. `[P]` parametrized. Status: ☑ covered · ☐ no test yet.

### Config and change detection
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| No file / no section | config_dir; `[other]` only | the defaults, `Config(0.0, 1.0, 8.0, True, False, 1.5, 2.5, 1.5)` | `test_load_config_defaults_when_no_config` / `test_load_config_defaults_when_section_missing` | ☑ |
| Timing not a number | `mouse_move_duration = fast` | `ConfigFileError`: `... mouse_move_duration: Must be a number, 0 or more, got 'fast'.` | `test_load_config_errors_on_invalid_value` | ☑ |
| Timing just below 0, NaN, infinity | `-0.1`, `nan`, `inf` | `ConfigFileError`: `... continue_pause: Must be a number, 0 or more, got '-0.1'.` | `test_timing_rejects_a_value_below_zero_or_not_finite` `[P]` | ☑ |
| `hot_corner` spellings | `true`, `false`, `yes`, `off` | parsed | `test_hot_corner_parses_boolean` `[P]` | ☑ |
| Signature: missing / tuple / stable / changes | tmp | None; `(path, mtime_ns, size)`; the same twice; different after a rewrite | `test_signature_none_when_file_missing` / `test_signature_returns_tuple_for_existing_file` / `test_signature_stable_when_unchanged` / `test_signature_changes_when_rewritten` | ☑ |

### A test per setting
Each setting missing from athc.ini (its default, the code's), at `-1` and at `0`, through the command on the stand-in desktop. `-1`: exit 2, `FAIL <athc.ini>: [autocontinue] <key>: Must be a number, 0 or more, got '-1'.` (`Must be true or false` for `hot_corner` and `drive_league_pregame`), nothing watched. The default and `0`: the value read (`load_config`, and the key's start line) and its effect in a run.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `mouse_move_duration` | Continue | the move to Continue over 0.0 s, by default and at 0; at 0.5, over 0.5 s, so the setting is the one used | `test_setting_mouse_move_duration` `[P]` | ☑ |
| `continue_pause` | Continue | 1.0 s before the click by default; none at 0 | `test_setting_continue_pause` `[P]` | ☑ |
| `halftime_pause` | halftime | `Waiting 8 seconds.`, 8 s, then `Return button clicked.`; `Waiting 0 seconds.`, none, at 0 | `test_setting_halftime_pause` `[P]` | ☑ |
| `hot_corner` | — | the hot-corner-on line and pyautogui's fail-safe on by default; off at 0 | `test_setting_hot_corner` `[P]` | ☑ |
| `drive_league_pregame` | the league play screen | off by default and at 0: nothing clicked, the next scan a second later | `test_setting_drive_league_pregame` `[P]` | ☑ |
| `plans_profiles_pause` | the league play screen, pre-game on | the five clicks, 1.5 s after Plans/Profiles and Visitor; both skipped at 0 | `test_setting_plans_profiles_pause` `[P]` | ☑ |
| `conditions_pause` | the same | 2.5 s after Conditions; skipped at 0 | `test_setting_conditions_pause` `[P]` | ☑ |
| `venues_pause` | the same | 1.5 s after Venues; skipped at 0 | `test_setting_venues_pause` `[P]` | ☑ |

### CLI
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| `--help` | — | the whole help screen (in [test_cli_help.py](test_cli_help.py)) | `test_help_screen` `[P]` | ☑ |
| An argument | `x` | exit 2; stderr ends `Error: Got unexpected extra argument (x).` | `test_cli_rejects_an_argument` | ☑ |
| No config | config_dir; stand-in desktop | exit 0; stderr: the start lines with the defaults, then `Waiting for the game window.`; stdout: `Stopped.` | `test_cli_runs_on_the_defaults_with_no_config` | ☑ |
| Missing dependency (pyautogui) | `sys.modules` stub | exit 2; stderr: `FAIL Missing pyautogui. Reinstall athc.` | `test_cli_missing_dependency_exits_2` | ☑ |
| `--hot-corner/--no-hot-corner` forwarded (else None) | tmp ini | value passed to the loop | `test_cli_forwards_hot_corner_override` `[P]` | ☑ |
| `--continue-pause` forwarded (else None) | absent, `0`, `2.5` | `None`, `0.0`, `2.5` passed to the loop | `test_cli_forwards_the_continue_pause` `[P]` | ☑ |
| `--continue-pause` rejected | `-0.1`, `nan`, `inf`, `fast` | exit 2; stderr ends `Error: Invalid value for '--continue-pause': must be 0 or more, got -0.1.` (`fast`: Click's `'fast' is not a valid float.`) | `test_cli_rejects_a_bad_continue_pause` `[P]` | ☑ |
| `-n/--dry-run` forwarded (else False) | absent, `--dry-run`, `-n` | `False`, `True`, `True` | `test_cli_forwards_dry_run` `[P]` | ☑ |
| Hot corner exits clean (stubbed) | the loop raises `HotCornerStop` | exit 0; stderr: `Hot corner hit.`; stdout: `Stopped.` | `test_cli_hot_corner_says_so_and_exits_clean` | ☑ |
| End of the game exits clean (stubbed) | the loop returns | exit 0; no stop line; stdout: `Stopped.` | `test_cli_end_of_game_stops_clean` | ☑ |
| Loop status through the callbacks | stub calls `progress` and `warn` | exit 0; stderr: the status line, then `WARN ...`; stdout: `Stopped.` | `test_loop_status_goes_to_stderr_through_the_callbacks` | ☑ |
| Dry-run sightings on stdout | stub calls `report` | stdout: the sighting, then `Stopped.` | `test_dry_run_sightings_go_to_stdout` | ☑ |
| Missing image | tmp ini; `continue_button.png`'s path in an empty folder (the real-screen tests load all twelve) | exit 2 before watching; stderr: `FAIL <image>: The system cannot find the file specified. Reinstall athc.` | `test_cli_a_missing_image_exits_2_before_watching` | ☑ |

### Images and the screen
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Unreadable image | tmp file, not an image | `AthcError`: `<image>: Cannot read the image. Reinstall athc.` | `test_an_unreadable_image_fails_and_says_to_reinstall` | ☑ |
| The screen in gray | a red screenshot | one-channel, red as 76 | `test_the_screen_is_searched_in_gray` | ☑ |
| Search order and settings | stub screen and matcher; nothing found; the pre-game off and on | the same screen searched for the loaded Results label, Halftime label, the League play label (pre-game on only), then Continue button, each over the whole screenshot (no region), grayscale, confidence 0.8 | `test_scan_searches_the_screen_for_each_image_in_order` `[P]` | ☑ |
| Scan order | every image on screen; Halftime and Continue; Continue only | Results with Return; Halftime with Return; the Continue button | `test_scan_order` `[P]` | ☑ |
| A label without Return | nothing; a label and Continue but no Return | nothing found, not even Continue | `test_scan_finds_nothing_without_return_under_a_label` `[P]` | ☑ |
| League play label without Game | the label and Continue; the pre-game on | nothing found | `test_scan_finds_no_pregame_without_game` | ☑ |
| Return and Game under the pointer | the Halftime label; the League play label with the pre-game on | the labels searched at 0.8, Return and Game (drawn, then lit up) at 0.6 | `test_scan_finds_return_and_game_at_a_lower_confidence` `[P]` | ☑ |
| Return lit up | the Halftime or Results label with the highlighted Return | Return found | `test_scan_finds_return_highlighted` `[P]` | ☑ |
| Config changes are said once each | first config, then changed values | `mouse_move_duration = …`, `continue_pause = …`, `halftime_pause = …`, `drive_league_pregame = true`, `conditions_pause = …` | `test_config_changes_are_said_through_the_callback` | ☑ |
| The waiting line for 1 second | `1.0` | `Waiting 1 second.` (the halftime tests show 8, 2.5 and 0) | `test_waiting_line_says_1_second` | ☑ |
| Focus gating | window titles | the game title matches, case-insensitive substring | `test_game_has_focus_matches_title` `[P]` | ☑ |

### The watch loop, on the stand-in desktop
| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Start lines in order | no athc.ini; plain, `--no-hot-corner`, `--dry-run`, `--dry-run --hot-corner` | the start line, the seven settings, the hot-corner line (off in a dry run), the dry-run line, `Waiting for the game window.` | `test_loop_start_lines_in_order` `[P]` | ☑ |
| Window lines | the game active or not at the first check, then a change each way | one line at the first check and one per change, not per pass; 1 s between scans, 2 s between window checks | `test_loop_says_the_game_window_at_the_first_check_and_each_change` `[P]` | ☑ |
| `--continue-pause` wins and holds | athc.ini `continue_pause` 2.5, changed to 30.0 after a click; `--continue-pause 0.5` | both clicks wait 0.5 s; no settings line on the reload | `test_loop_continue_pause_option_wins_and_holds_across_a_reload` | ☑ |
| athc.ini deleted mid-run | deleted during the first pause | the defaults said and applied (an instant move, a 1.0 s delay); no `WARN` | `test_loop_a_deleted_athc_ini_means_the_defaults` | ☑ |
| Fail-safe from the click | stubbed `leftClick` raises `FailSafeException` | the loop stops (`HotCornerStop`, a KeyboardInterrupt) | `test_loop_a_fail_safe_from_the_click_stops_the_watcher` | ☑ |
| Dry run | the button on screen; `--dry-run --continue-pause 3` | the sighting through `report`, then an 8 s wait; no move, no click | `test_dry_run_reports_the_button_and_never_moves_or_clicks` | ☑ |
| Halftime | the Halftime screen; `mouse_move_duration = 0.5`, `halftime_pause = 2.5`, `--continue-pause 0.5` | the label and Return lines, `Waiting 2.5 seconds.`, `Return button clicked.`; an instant move to Return, a 2.5 s wait, the click on Return, then 4 s | `test_loop_halftime_moves_to_return_waits_then_clicks` | ☑ |
| Halftime, Return lit up by the mouse | the highlighted Return at the check before the click | the click on Return; `Return button clicked.` | `test_loop_halftime_clicks_return_highlighted_by_the_mouse` | ☑ |
| Halftime, focus lost during the pause | the game inactive after the wait | waits 8 s; no click | `test_loop_halftime_focus_lost_during_the_pause_means_no_click` | ☑ |
| Continue gone before the click | Continue, then an empty screen at the re-check | `Continue button gone; not clicked.`; no click | `test_loop_continue_gone_before_the_click_is_not_clicked` | ☑ |
| Halftime gone before the click | halftime, then an empty screen, or the label without Return, at the re-check | `Halftime label gone; Return not clicked.` / `Return button gone; not clicked.`; no click | `test_loop_halftime_gone_before_the_click_is_not_clicked` `[P]` | ☑ |
| A button moved before the click | Continue, or Return at halftime, found 6 pixels off a 10-pixel stand-in button at the re-check | `Continue button moved; not clicked.` / `Return button moved; not clicked.`; no click | `test_loop_a_button_moved_before_the_click_is_not_clicked` `[P]` | ☑ |
| A button moved but still under the spot | Continue found 5 pixels off at the re-check | the click, on the spot the scan found | `test_loop_a_button_still_under_the_old_spot_is_clicked` | ☑ |
| Focus lost just before the click | the game inactive at the last check | no click; `Waiting for the game window.` | `test_loop_focus_lost_just_before_the_click_means_no_click` | ☑ |
| A reload that fails mid-run | athc.ini rewritten as ANSI with an accent | `WARN <athc.ini>: Not UTF-8 text. Save it as UTF-8. Keeping the previous settings.`; the old delay; the click | `test_loop_a_reload_that_fails_warns_and_keeps_the_settings` | ☑ |
| Unexpected errors in passes | the screenshot raises `RuntimeError("driver hiccup")` twice, then `ValueError("bad pixels")` | the first of each kind through `warn_traced`, naming the run log; the repeat one `WARN` line; 5 s waits; then the next pass clicks | `test_loop_an_unexpected_error_is_traced_once_and_retried` | ☑ |
| The traceback reaches the run log | the stub calls `warn_traced` inside an `except` | stderr: one `WARN` line; the run log: the line, then `Traceback (most recent call last):` | `test_cli_an_unexpected_error_puts_its_traceback_in_the_run_log` | ☑ |
| Screen hidden before the click | Continue, then a hidden screen at the re-check | the locked-screen `WARN` and 60 s back-off; no line about the button; no click | `test_loop_a_hidden_screen_before_the_click_means_no_click` | ☑ |
| End of the game | the Results screen; `mouse_move_duration = 0.5` | the label and Return lines; an instant move to Return; the loop returns; no click, no wait | `test_loop_end_of_game_moves_to_return_and_stops` | ☑ |
| Dry run at halftime | the Halftime screen | the label and Return lines through `report`, then an 8 s wait; no move, no click | `test_dry_run_reports_halftime_and_never_moves_or_clicks` | ☑ |
| Dry run at the end of the game | the Results screen | the label and Return lines through `report`; the loop returns; no move, no click, no wait | `test_dry_run_reports_the_end_of_the_game_and_stops` | ☑ |

### The league play pre-game, on the stand-in desktop
The drive at the default pauses, and a pause of 0 skipping its click, are the setting tests above.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| A pause just over 0 | `conditions_pause = 0.1` | every button clicked; 0.1 s after Conditions | `test_loop_a_pregame_pause_over_0_clicks` | ☑ |
| Game lit up by the mouse | the highlighted Game; every pause 0 | the click on Game; `Game button clicked.` | `test_loop_pregame_clicks_game_lit_up_by_the_mouse` | ☑ |
| Label gone before a click | an empty screen before Visitor | `League play label gone; Visitor button not clicked.`; no more clicks | `test_loop_pregame_label_gone_means_no_more_clicks` | ☑ |
| Button not found | no Visitor button | `Visitor button not found; not clicked.`; an 8 s wait | `test_loop_pregame_button_not_found_is_not_clicked` | ☑ |
| Focus lost just before a click | the game inactive at the last check | no click; `Waiting for the game window.` | `test_loop_pregame_focus_lost_just_before_a_click_means_no_click` | ☑ |
| Dry run | the league play screen without Venues | the label line, each button's `found at` line or `Venues button not found.` through `report`, then an 8 s wait; no move, no click | `test_dry_run_reports_the_pregame_and_never_clicks` | ☑ |

### The shipped images on real game screens
Screenshots of the real game in `data/autocontinue_screens/`, cropped to the game window: the Windows Sandbox ones 641x506, the posted ones 642x507. Only the screenshot is stood in for: the images load, the screen turns gray and the matcher searches it as in a run, with `drive_league_pregame` on. A found middle may be up to 3 pixels from where the game draws it. A button that opens under the pointer a click on the screen before left there shows unlit, but Visitor, which the game lights even so; one the pointer moves onto lights up, but Continue, which has no lit look. No click leaves the pointer on Return.

"Every button" is every button autocontinue acts on: Continue, Return at halftime and at the end of the game, and the pre-game's Plans/Profiles, Visitor, Conditions, Venues and Game. Each is found on the screen it is acted on: Continue alone, Return under its label, a pre-game button on the pre-game screen, searched as its step is.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Pointer on no button | `continue.png`, `halftime.png`, `results.png`; the pre-game as it opens (Plans/Profiles), the home team's plans (Visitor), the visitor's (Conditions), Conditions (Venues), Venues (Game) | each button found where the game draws it | `test_real_button_found` `[P]` (`pointer elsewhere`) | ☑ |
| Pointer on every button | each button under the pointer a click on the screen before left there: Continue (the play before's), Plans/Profiles, Conditions and Venues on the page their own click opens, Visitor after Home at its spot (lit), Game where Accept was clicked | each button found; Venues, 0.77 under the pointer, matched at 0.7 | `test_real_button_found` `[P]` (`pointer on it`) | ☑ |
| Pointer on every button, lit | each button lit by the pointer moved onto it: Return at halftime and at the end, Plans/Profiles, Visitor, Conditions, Venues; Game with the hand at its corner | each button found | `test_real_button_found` `[P]` (`lit`) | ☑ |
| League pre-game on, the pointer on each button | the scan and each step's screenshot with the pointer on the button it clicks: left there by a click / lit | the label line, then the five buttons clicked in order where the game draws them, with their pauses | `test_real_pregame_driven_to_game` `[P]` | ☑ |
| League pre-game off | each pre-game page; no athc.ini | nothing said, moved or clicked | `test_real_pregame_left_alone_when_off` | ☑ |
| Exhibition, league pre-game on / off | each exhibition pre-game page: as it opens with the pointer on Game, the home team's plans, the visitor's, Conditions, Venues, Difficulty Levels, Game Controls | nothing said, moved or clicked | `test_real_exhibition_pregame_left_alone` `[P]` | ☑ |
| Nothing to act on | `coin_toss.png` (Receive, 0.76 like Continue); `league_play_schedule.png` (the League play label, no Game), `controllers.png` and `controllers_accept_lit.png` (Accept, unlit and lit, where Game shows next), the pre-game on | nothing found | `test_real_screen_with_nothing_to_act_on` `[P]` | ☑ |
| The game full screen, not windowed | — | — | — | ☐ |

### Each match cutoff, from either side
The matcher keeps only scores over its confidence. Each cutoff is tested on a screen scoring just over it and one just under: the button's image with noise added, under its label where the search needs one; the score is the best that any of the button's images (drawn, lit) reaches on it.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Each pre-game step | Plans/Profiles, Visitor and Conditions at 0.8; Venues at 0.7; Game, drawn or lit, at 0.6 | found just over; not found just under | `test_pregame_step_finds_its_button_over_its_cutoff` `[P]` | ☑ |
| The check before the Continue click | Continue at 0.8 | nothing said just over; `Continue button gone; not clicked.` just under | `test_before_the_click_continue_counts_over_0_8` `[P]` | ☑ |
| The check before the Return click | Return, drawn or lit, at 0.6, under the Halftime label | nothing said just over; `Return button gone; not clicked.` just under | `test_before_the_click_return_counts_over_0_6` `[P]` | ☑ |
| The scan's Return | Return, drawn or lit, at 0.6, under the Halftime label | halftime just over, at Return; nothing just under | `test_scan_finds_return_under_its_label_over_0_6` `[P]` | ☑ |
| The scan's Game | Game, drawn or lit, at 0.6, under the League play label; the pre-game on | the pre-game screen just over; nothing just under | `test_scan_finds_the_pregame_with_game_over_0_6` `[P]` | ☑ |

### The game each Sandbox test builds
In [test_autocontinue_game.py](test_autocontinue_game.py), not slow, on a fake install in the temp folder. The real build copies the game's own files from `ATHC_GAME_DIR`, as [game-files.txt](game-files.txt) lists them (a clean install's files and empty folders, its CD image left out), then lays `data/autocontinue_game/SIERRA` over them: `SETUP.INI`, the PNFL league with each team's plans and profiles, and an empty disc image.

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| Only the listed files | an install with the game's files, an empty `GameLogs`, a stray file and a coach's plan in `PNFL`; the list names the game's files and `GameLogs/` | only the listed files copied; `GameLogs` made | `test_only_the_listed_game_files_are_copied` | ☑ |
| The test files laid over | the same install; test files `SETUP.INI` and `PNFL/team.pln` | the test's `SETUP.INI`; its plan added; the game's listed files kept | `test_the_test_files_are_laid_over_the_game` | ☑ |
| `ATHC_GAME_DIR` set | the folder holding `FbPro98` | that folder | `test_the_game_dir_is_the_folder_holding_fbpro98` | ☑ |
| `ATHC_GAME_DIR` unset or empty | — | fails with the `setx ATHC_GAME_DIR` line | `test_no_game_dir_fails_saying_how_to_set_it` `[P]` | ☑ |
| No game there | an empty folder; the `FbPro98` folder itself | fails with `No game at ...` | `test_a_game_dir_with_no_game_fails` `[P]` | ☑ |

### The real game, in Windows Sandbox (slow, run on demand)
In [test_autocontinue_game.py](test_autocontinue_game.py), marked `slow`: `uv run pytest -m slow tests/integration/test_autocontinue_game.py --no-cov`. Needs Windows Sandbox, a built installer and the game installed (`ATHC_GAME_DIR`, the folder holding `FbPro98`). Each test builds its own game in its temp folder (above) and maps it writable; the sandbox mounts its empty disc image, installs athc and starts autocontinue, with the test's own athc.ini when it gives one; the test drives the menus by image (`data/autocontinue_game/agent.ps1` takes the screenshots and clicks; the menu images the test alone needs are in `data/autocontinue_game/images/`). The mouse is parked at the top left of the game window before each screenshot, so the game's pointer covers no button. In the exhibition game, `data/autocontinue_game/pointer-helper.ps1` looks at the game window every 100 ms, between searches. As each Continue or Return shows, it lights half (a move onto it, then 1 px), moves the pointer away from a quarter and leaves it on a quarter, leaving it only on a button it is already on, unlit, so the share left falls short when the game gives too few; it logs each with at most how long the button had been up and whether the pointer is on it. Continue's box opens where the one before was about a quarter of the time (24 of 84 in a captured game).

| Case | Input | Expected | Test | Status |
|---|---|---|---|---|
| An exhibition game, start to end, the pointer lit, away or left | Game Type, Exhibition, Accept, Computer for both teams, Accept, Game Controls, 6 Minutes, Game; the helper from then on | the halftime lines, `Waiting 8 seconds.`, `Return button clicked.`; at the end the Results and Return lines, then `Stopped.`; no `WARN Unexpected`; at least 40 buttons helped in time (within the 1 s Continue pause of showing), lit, away and left (the pointer on it) within 0.10 of 50/25/25; Return helped at halftime and at the end | `test_an_exhibition_game_through_halftime_to_the_end` | ☑ |
| A league pre-game, on | `drive_league_pregame = true`; Game Type, League, Schedule, every game to Sim, the first game to Play, Play, Computer for both teams, Accept | `League play label found at …`, then the five buttons clicked in order; once the 4 s after Game are up, the League play label gone; no `WARN` | `test_a_league_pregame_driven_to_the_game[on]` | ☑ |
| A league pre-game, off | `drive_league_pregame = false`; the same menus | after 20 s the screen is still on the home team's plans; no League play or clicked lines; no `WARN` | `test_a_league_pregame_left_alone_when_off[off]` | ☑ |
