# config behavior plan

`athc config set` writes `path`, `play_path`, `team` and `ppp_path` to the league's `league.toml`, and `athc config edit` opens files with `os.startfile`; help, options and lines are in config-cli.md.

Depends on cli-help.md landing first.

## Decisions

- `set` stays the one writer.
- `set` writes `league` to `athc.ini`, and `path`, `play_path`, `team` and `ppp_path` to the league's `league.toml`, the league in use or `--league NAME`.
- This reverses check-ppp-cli.md's choice to keep `team` and `ppp_path` edited by hand in `league.toml`.
- `set path`, `set play_path` and `set ppp_path` take a FOLDER, written as supplied (no folder check, nothing resolved); `set team` a NAME.
- A missing `league.toml`, or one with no `[league]` section, is Windows' `FAIL <league.toml>: The system cannot find the file specified.` and nothing is written: athc does not repair a broken install. Exit 2.
- A malformed `league.toml` is its parse error line, as every reader prints it, and nothing is written. Exit 2.
- `--league` is not valid with `set league`: `Error: --league cannot be used with set league.` Exit 2.
- `league.toml` is written through a TOML library that keeps comments, so its comments and other lines stay as they were, as ConfigUpdater keeps them in `athc.ini`.
- `set` of a league key reads `league.toml` to rewrite it.
- Order of checks in `set`: KEY (Click); for `league`, VALUE (the folder), then `athc.ini` (parse, write); for a league key, the league (its folder must exist), then `league.toml` (parse, write); then the `OK` line.
- A usage error never touches the file, and a malformed file is reported before anything is written.
- `edit` opens the file with `os.startfile` directly, so a failure reaches `main`, which prints `FAIL <file>: <Windows' text>` and exits 2.
- A file with no associated app: `FAIL <athc.ini>: No application is associated with the specified file for this operation.` (any other Windows text the same way). Exit 2.
- `EDITOR` and `VISUAL` stay ignored.
- `edit league.toml` with the file missing is `set`'s error, `FAIL <league.toml>: The system cannot find the file specified.`, exit 2, and nothing is created.
- `reveal` keeps `click.launch`.

## Files to change

- `src/athc/config.py`: `league_file(league: str | None) -> Path`: `league_dir(resolve_league(league)) / LEAGUE_FILE`, raising `LeagueError` as those two do; `check_ppp.py` and `play_dir` keep building the path from `LeagueConfig.dir`, unchanged.
- `src/athc/config.py`: `set_league_value(league: str | None, key: str, value: str) -> Path`: writes `key = value` under `[league]` in `league_file(league)` through a TOML library that keeps comments, so its comments and other lines stay, and returns the path written; the library is not picked yet and is added with `uv add`.
- `src/athc/cli/config/set.py`: a league key goes through `set_league_value(league, key, value)`; `--league` with `set league` is `Error: --league cannot be used with set league.`
- `src/athc/cli/config/edit.py`: `os.startfile(path)` instead of `click.launch(path)`, its `OSError` left to `main`.

## Tests

`tests/integration/test_config_set.py` (`set`) and `tests/integration/test_config.py` (`edit`); no new fixtures (`config_dir`, `write_config` and `make_league` in `tests/conftest.py` cover it).

- `set path`, `set play_path` and `set ppp_path` with a folder and `set team Denver` write the key under `[league]` in the `league.toml` of the league in use; every comment and other line of the file is kept.
- `set <league key> --league PCFL` writes PCFL's `league.toml`.
- `set` of a league key with no league set and no `--league`: `League is not set`, 2.
- `set` of a league key with `--league NOPE`: `not found`, 2.
- `set team Denver` with the league's `league.toml` missing: `FAIL <league.toml>: The system cannot find the file specified.`, 2, no file created.
- `set team Denver` with a `league.toml` that has no `[league]` section: the same line, 2, the file unchanged.
- `set team Denver` with a malformed `league.toml`: its parse error line, 2, the file unchanged.
- `set league PCFL --league PNFL`: `Error: --league cannot be used with set league.`, 2, `athc.ini` unchanged.
- `set ppp_path` with a relative folder and `set path` with a folder that does not exist: each written as supplied, 0.
- `edit`: `os.startfile` monkeypatched; a stub raising `OSError` with `winerror=1155`, Windows' text and the file name gives `FAIL <athc.ini>: No application is associated with the specified file for this operation.` and exit 2.
- `test_config.py`: `test_edit_opens_associated_app`, `test_edit_ignores_editor_env` and `test_edit_preserves_existing_file` monkeypatch `os.startfile` instead of `click.launch`.
- `tests/integration/README.md`: the `athc config` table's `edit` rows (`launch(<athc.ini>)`) change; both config tables gain the rows above.

## Docs and meta

- `docs/config/ARCHITECTURE.md`: `edit` is `os.startfile`; the exit table gains the `FAIL` case for an unassociated file; Boundaries says `set` writes `league.toml`. (docs-layout.md folds the pair into one `config.md`; whichever lands first carries these changes.)
- `docs/design/architecture.md`, Config: the bullet's `set` part (`path`, `play_path`, `team`, `ppp_path` to the league's `league.toml` through a TOML library that keeps comments) and `edit` part (`os.startfile`), in the bullet text config-cli.md quotes.
- `CHANGELOG.md`: `config: edit reports a file Windows cannot open instead of doing nothing`.
- `TODO.md`: this plan's entry, ticked when done.
