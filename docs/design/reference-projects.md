# Reference projects

Projects athc models itself on. These are **normal modern end-user Python CLIs and
desktop apps** — tools people install to get a job done — not Python build/meta
tooling (linters, formatters, packagers, frameworks) and not enterprise platforms.
Best 2–3 matches per category.

## Peer end-user CLIs (overall model)

The shape athc aims for: a normal installable CLI for non-dev users.

- [pgcli](https://github.com/dbcli/pgcli) / [mycli](https://github.com/dbcli/mycli) — interactive Postgres/MySQL CLIs (dbcli). Closest peers for **config handling**: a self-documenting config seeded into the user dir, defaults layered underneath, never overwritten on upgrade.
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — end-user downloader; optional `#`-commented config, everything also reachable via `--help`.
- [llm](https://github.com/simonw/llm) / [sqlite-utils](https://github.com/simonw/sqlite-utils) — Simon Willison's Click CLIs; closest analogs for athc's shape (solo-maintained, plugin ecosystem, Click over data files).

## Self-documenting user config

- [pgcli](https://github.com/dbcli/pgcli) / [mycli](https://github.com/dbcli/mycli) — **direct model.** Ship one fully-commented config; copy it into the user dir on first run; layer it under the user's file at runtime so new keys work from the default; never overwrite the user's file. "See the file itself for a description of all available options" — no separate reference/example file.
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — optional config, inline `#` comments, options documented in `--help`/README.
- [httpie](https://github.com/httpie/cli) — small `config.json`, defaults in code, documented online.

**Adaptation for athc**: in-code defaults are authoritative (every section/key optional; missing → default), so a config file is never required. The shipped `athc.ini` is a single self-documenting PNFL starter — no `.example` twin.

## Config dir override (env var)

For running from source with a config separate from the installed one.

- [httpie](https://github.com/httpie/cli) — `HTTPIE_CONFIG_DIR` checked first in path resolution.
- [llm](https://github.com/simonw/llm) — `LLM_USER_PATH` overrides the default app dir.
- [tmuxp](https://github.com/tmux-python/tmuxp) — `TMUXP_CONFIGDIR` env var.

Pattern adopted for athc: `ATHC_CONFIG_DIR` env var, no `--config` flag. Mechanics in [cli.md](cli.md).

## Output file location (CWD, never a fixed app dir)

Default location for a produced file when no path is given.

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — CWD default; `-o` template, `-P` sets the base.
- [cookiecutter](https://github.com/cookiecutter/cookiecutter) — generates into CWD; `-o` defaults to `.`.
- [ffmpeg](https://ffmpeg.org/ffmpeg.html) — output is a required positional (relative → CWD).

**Adaptation for athc**: produced output (schedule, report, convert-pdb `.xlsx`, diff export) stays CWD-relative or explicit, like CLI paths in [config.py](../../src/athc/config.py). `platformdirs` is config-only; fixed dirs are for state, not output ([clig.dev](https://clig.dev/)).

## Multi-profile config (named variants selected at runtime)

For athc's multi-league pattern (selected via `--league NAME`). Grounded in ubiquitous
end-user tools, not enterprise CLIs.

- **git** `config` — `[remote "origin"]`, `[branch "main"]`: a section type plus a quoted/dotted name. Closest precedent for namespacing a name under a kind.
- **OpenSSH** `~/.ssh/config` — `Host NAME` blocks selected by name; per-host keys with global fallbacks. Precedent for "pick a named block, fall back to defaults."

**Adaptation for athc**: dotted `[league.NAME]` sections (the dot is valid TOML, so it survives a future move off INI), `--league` per-command (not umbrella-level). `configparser`'s `[DEFAULT]` + `%(key)s` interpolation handle inheritance natively. Selection priority: `--league` → `ATHC_LEAGUE` → `[athc] default_league` → error.

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

## Plugins via entry points

athc discovers subcommands at runtime via setuptools entry points (`athc.commands`).

- [Flask](https://github.com/pallets/flask) — **the direct model.** `FlaskGroup._load_plugin_commands` is the template for `AthcGroup`'s lazy entry-point loader; plugin group `flask.commands` → `athc.commands`. Flask is a framework, but this specific `click.Group` subclass *is* what athc copied.

Peer end-user CLIs that take plugins the same way:

- [llm](https://github.com/simonw/llm) — plugin ecosystem via `pluggy`/entry points; install a package, new commands appear. Closest peer analog.
- [sqlite-utils](https://github.com/simonw/sqlite-utils) — same `pluggy` plugin model over a Click CLI.
- [httpie](https://github.com/httpie/cli) — auth/transport plugins registered via entry points.

## Windows packaging for end users

End-user Python apps (not packagers) that ship a self-contained Windows install.

- [Calibre](https://github.com/kovidgoyal/calibre) — large end-user Python desktop app; bundles its own runtime so users install nothing extra.
- [MusicBrainz Picard](https://github.com/metabrainz/picard) — end-user Python/Qt app; offline Windows installer with bundled deps.

**Adaptation for athc**: offline-bundled wheels (`--no-index --find-links --offline`) for reproducibility and failure tolerance (PyPI outages, corporate firewalls, AV TLS interception). Build script in `release/`, final artifact in `dist/` (standard Python build output). Future direction: an [Inno Setup](https://jrsoftware.org/isinfo.php) `.exe` (used by Audacity, qBittorrent).

## Testing exemplars

Peer Click CLIs whose product is a generated/queried file.

- [sqlite-utils](https://github.com/simonw/sqlite-utils) — closest structural match: Click CLI over data files, `CliRunner`, **reopen-the-produced-artifact** asserts, `test_cli*.py` split out.
- [httpie](https://github.com/httpie/cli) — `CliRunner`-style invocation tests with `isolated_filesystem`: write input, invoke, assert exit code + output.

athc's own discipline (golden input→expected-output fixtures with a regen script) is documented in [testing-unit.md](testing-unit.md) and [testing-integration.md](testing-integration.md).

## Direct design influences

| Decision | Project(s) |
|---|---|
| CLI framework: Click | llm, sqlite-utils, httpie |
| Lazy plugin loader (`AthcGroup`) | Flask (`FlaskGroup._load_plugin_commands`) |
| Entry-points group naming (`athc.commands`) | Flask (`flask.commands`) |
| Runtime plugin discovery via entry points | Flask; llm, sqlite-utils (`pluggy` ecosystems) |
| Project layout (`<pkg>/cli/` for CLI, `<pkg>/<tool>/` for logic) | pnfl predecessor |
| Tool vs library distinction (`py.typed`) | pnfl predecessor |
| INI format over TOML | Non-dev user familiarity (no specific precedent) |
| Single self-documenting `athc.ini`, no `.example` | pgcli, mycli |
| In-code defaults; missing section/key → no error | pgcli, mycli, yt-dlp |
| Config dir override (`ATHC_CONFIG_DIR` env var) | httpie (`HTTPIE_CONFIG_DIR`), llm (`LLM_USER_PATH`), tmuxp |
| Output → CWD/explicit, never a fixed app dir | yt-dlp, cookiecutter, ffmpeg; clig.dev |
| Multi-league named sections + `[DEFAULT]` cascade | git `[remote "name"]`, ssh `Host` blocks |
| Offline-bundled install (`--no-index --find-links --offline`) | Calibre, MusicBrainz Picard; pnfl predecessor |
| Release artifact location (`dist/`) | Standard Python build output |
| Windows installer toolkit (future): Inno Setup | Audacity, qBittorrent |
| Doc format: `.txt` over `.md` for end users | Classic Unix `README.txt` / man pages |
| Testing layout (CliRunner, reopen artifact, golden files) | sqlite-utils, httpie |
