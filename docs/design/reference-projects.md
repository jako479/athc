# Reference projects

Projects we cited as design references for athc. Best 2–3 matches per category.

## Python CLI: umbrella + plugins via entry points

- [Flask](https://github.com/pallets/flask) — `FlaskGroup._load_plugin_commands` is the direct template for `AthcGroup`. Plugin entry-point group `flask.commands`.
- [dbt-core](https://github.com/dbt-labs/dbt-core) — Click + adapter plugins; `cli/` layout informed ours. Closest precedent for our core/extension split (dbt-core + dbt-adapters).
- [Poetry](https://github.com/python-poetry/poetry) — Click umbrella with same-org separate-repo plugins (poetry-plugin-export, poetry-plugin-bundle).

## Small team / solo dev Python CLIs

- [uv](https://github.com/astral-sh/uv) and [ruff](https://github.com/astral-sh/ruff) — Astral; `scripts/release.sh`/`.py` convention. uv is also our package manager + winget source.
- [Black](https://github.com/psf/black) — `scripts/release.py` informed our release-script location and pattern.
- [llm](https://github.com/simonw/llm) — Simon Willison solo project, Click + plugin ecosystem; closest analog for athc's shape. Source of the `ATHC_CONFIG_DIR` env-var dev-override pattern (`LLM_USER_PATH`).

## Windows desktop apps with user config files

- [Notepad++](https://github.com/notepad-plus-plus/notepad-plus-plus) — `config.xml` (user-owned) + `config.model.xml` (always-overwritten reference). **Direct influence on our `athc.ini.example` pattern.**
- [VS Code](https://github.com/microsoft/vscode) — `settings.json` + layered defaults, `deprecationMessage` for deprecated keys. **Direct influence on our deprecation pattern.**
- [Sublime Text](https://www.sublimetext.com/) — `Default.sublime-settings` + per-user override file. **Direct influence on our layered-defaults approach.**

## Multi-profile config (named variants selected at runtime)

For athc's multi-league pattern (selected via `--league NAME`).

- [AWS CLI](https://github.com/aws/aws-cli) — `~/.aws/config` with `[default]` + `[profile NAME]`; `--profile` flag + `AWS_PROFILE` env. **Closest direct analog: INI-format, named sections, flag + env + default fallback.**
- [Snowflake CLI](https://github.com/snowflakedb/snowflake-cli) — `~/.snowflake/connections.toml` with `[NAME]` flat sections; `--connection` + `SNOWFLAKE_DEFAULT_CONNECTION_NAME` env.
- [dbt-core](https://github.com/dbt-labs/dbt-core) — `~/.dbt/profiles.yml` with named targets; `--target` + `DBT_TARGET` env.

**Adaptation for athc**: dotted `[league.NAME]` sections (after setuptools' `setup.cfg`, e.g. `[options.extras_require]`) instead of AWS's space form `[profile NAME]`, and `--league` per-command instead of umbrella-level. Dot is the one delimiter that's also valid TOML, so it survives a future move off INI. `configparser`'s `[DEFAULT]` + `%(key)s` interpolation handle inheritance natively. Selection priority: `--league` → `ATHC_LEAGUE` → `[athc] default_league` → error.

Example:

```ini
[DEFAULT]
RosterPath = %(LeagueRoot)s\rosters

[athc]
default_league = PNFL

[league.PNFL]
LeagueRoot = D:\Leagues\PNFL
PlayPath = D:\Leagues\PNFL\plays

[league.PCFL]
LeagueRoot = E:\Leagues\PCFL
PlayPath = E:\Leagues\PCFL\plays_v2
```

Full design: [config.md](config.md). CLI mechanics: [cli.md](cli.md).

## Dev config override (env var)

For running from source with a config different from production.

- [llm](https://github.com/simonw/llm) — `LLM_USER_PATH` env var overrides the default `click.app_dir`. Closest analog (solo dev, Click, plugins).
- [httpie](https://github.com/httpie/cli) — `HTTPIE_CONFIG_DIR` env var checked first in path resolution.
- [tmuxp](https://github.com/tmux-python/tmuxp) — `TMUXP_CONFIGDIR` env var; also project-local `.tmuxp.yaml`.

Pattern adopted for athc: `ATHC_CONFIG_DIR` env var, no `--config` flag. Mechanics in [cli.md](cli.md).

## Release pipeline / artifact location

- [PyInstaller](https://github.com/pyinstaller/pyinstaller) — `release/` folder for pipeline assets; `dist/` for final artifacts. **Direct influence on our script + output locations.**
- [Briefcase](https://github.com/beeware/briefcase) — `dist/` for installer artifacts (MSI, .pkg, .deb, .zip).
- [Hatch](https://github.com/pypa/hatch) — `release/macos/` and `release/windows/` for platform installer pipelines; `dist/` for build targets.

## Windows installer toolkits (future)

- [Inno Setup](https://jrsoftware.org/isinfo.php) — open-source de-facto Windows installer toolkit. Used by Audacity, qBittorrent, many Python apps. Likely future direction.

## Testing exemplars

Test suites athc's testing models. Details: [testing-unit.md](testing-unit.md), [testing-integration.md](testing-integration.md).

- [Black](https://github.com/psf/black) — **input→expected-output cases**: each `tests/data/cases/*.py` holds input + expected in one file split by a `# output` marker, auto-parametrized over the dir.
- [sqlfluff](https://github.com/sqlfluff/sqlfluff) — **sidecar expected-output fixtures** (`name.sql` + generated `name.yml`) with a regen script and an in-repo testing guide (`test/AGENTS.md`); closest to our binary→structured-output case.
- [pip-tools](https://github.com/jazzband/pip-tools) — clean **`CliRunner` + `isolated_filesystem`** model for a CLI whose product is a generated file: write input, invoke, assert exit code + contents.
- [sqlite-utils](https://github.com/simonw/sqlite-utils) — closest structural match (Click CLI over data files): separate `test_cli*.py`, `CliRunner`, **reopen-the-produced-artifact** asserts.

## Direct design influences

The specific decisions and which projects informed each.

| Decision | Project(s) |
|---|---|
| CLI framework: Click over Typer | Flask, Poetry, dbt |
| Entry-points group naming (`athc.commands`) | Flask (`flask.commands`) |
| Lazy plugin loader (`AthcGroup`) | Flask (`FlaskGroup._load_plugin_commands`) |
| Project layout (`<pkg>/cli/` for CLI, `<pkg>/<tool>/` for logic) | pnfl predecessor; dbt |
| Tool vs library distinction (`py.typed`) | pnfl predecessor |
| INI format over TOML | Non-dev user familiarity (no specific precedent) |
| `athc.ini` + `athc.ini.example` pattern | Notepad++, Sublime Text |
| In-code defaults; missing section → no error | pytest, mkdocs, Sphinx, Flask, Hatch |
| Deprecation: log warning for 2–3 releases | VS Code (`deprecationMessage`) |
| Multi-league sections + `[DEFAULT]` cascade | AWS CLI `[profile NAME]`; setuptools dotted `setup.cfg` sections |
| Dev config override (`ATHC_CONFIG_DIR` env var) | llm (`LLM_USER_PATH`), httpie, tmuxp |
| Build script location (inside `release/`) | PyInstaller, Hatch |
| Release artifact location (`dist/`) | PyInstaller, Briefcase, Hatch, pnfl predecessor |
| Offline-bundled install (`--no-index --find-links --offline`) | pnfl predecessor; Calibre, MusicBrainz Picard, Briefcase |
| `uv tool update-shell` + "new terminal" hint | pnfl predecessor's install-uv.bat |
| Doc format: `.txt` over `.md` for end users | Classic Unix `README.txt` / man pages |
| Windows installer toolkit (future): Inno Setup | Audacity, qBittorrent |
| Winget install command for uv | astral-sh.uv |
| Testing layout + golden-file discipline | Black, sqlfluff, pip-tools, sqlite-utils |
