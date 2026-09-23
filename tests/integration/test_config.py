"""Direct tests for `athc.config.load_league` — the shared league resolver.

`load_league` reads `config_dir()/athc.ini`, so per testing-integration.md these
live in the integration tier (unit tests never read config). It is shared
infrastructure every `--league` tool calls, so it is covered once here rather
than per command. League sections use the `[league.NAME]` convention; bare
sections (`[athc]`, `[gameplan]`) are not leagues.

Also covers the `athc config` command group (path / edit / reveal), with the
editor and Explorer launches mocked, and loads the shipped `release/athc.ini`
through every section loader so the bundled config cannot silently go stale.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from athc.autocontinue import config as autocontinue_config
from athc.cli.config import config as config_group
from athc.cli.config.edit import edit
from athc.cli.config.path import path
from athc.cli.config.reveal import reveal
from athc.config import LeagueError, load_league, resolve_path
from athc.gameplan import config as gameplan_config
from athc.pdbtoexcel import config as pdbtoexcel_config
from athc.profile import config as profile_config

WriteConfig = Callable[..., Path]


# ── resolution priority: --league arg → ATHC_LEAGUE → [athc] default_league ──


def test_resolves_explicit_league_arg(write_config: WriteConfig) -> None:
    write_config("[league.PNFL]\nplay_path = D:/p\n")
    assert load_league("PNFL")["play_path"] == "D:/p"


def test_resolves_from_env(
    write_config: WriteConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_config("[league.PNFL]\nplay_path = D:/p\n")
    monkeypatch.setenv("ATHC_LEAGUE", "PNFL")
    assert load_league()["play_path"] == "D:/p"


def test_resolves_from_default_league(
    write_config: WriteConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ATHC_LEAGUE", raising=False)
    write_config("[athc]\ndefault_league = PNFL\n[league.PNFL]\nplay_path = D:/p\n")
    assert load_league()["play_path"] == "D:/p"


def test_arg_beats_env(
    write_config: WriteConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_config("[league.ARG]\nk = arg\n[league.ENV]\nk = env\n")
    monkeypatch.setenv("ATHC_LEAGUE", "ENV")
    assert load_league("ARG")["k"] == "arg"


def test_env_beats_default_league(
    write_config: WriteConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_config(
        "[athc]\ndefault_league = DFLT\n[league.ENV]\nk = env\n[league.DFLT]\nk = dflt\n",
    )
    monkeypatch.setenv("ATHC_LEAGUE", "ENV")
    assert load_league()["k"] == "env"


# ── errors ──


def test_no_league_resolvable_lists_configured(
    write_config: WriteConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ATHC_LEAGUE", raising=False)
    write_config(
        "[league.PNFL]\nk = 1\n[league.PCFL]\nk = 2\n[gameplan]\nrule_files =\n",
    )
    with pytest.raises(LeagueError) as exc:
        load_league()
    msg = str(exc.value)
    assert "no league selected" in msg
    # prefix stripped; tool section [gameplan] is not a league
    assert "Configured leagues: PNFL, PCFL" in msg


def test_unknown_league_errors(write_config: WriteConfig) -> None:
    write_config("[league.PNFL]\nk = 1\n")
    with pytest.raises(LeagueError) as exc:
        load_league("PCFL")
    assert "[league.PCFL]" in str(exc.value)


def test_misspelled_prefix_section_is_inert(
    write_config: WriteConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    # `[leagu.AFCL]` (typo'd prefix) is well-formed INI — configparser accepts it,
    # no parse error. But it is not a league: absent from the hint, and selecting
    # AFCL fails looking for the correctly-spelled `[league.AFCL]`.
    monkeypatch.delenv("ATHC_LEAGUE", raising=False)
    write_config("[leagu.AFCL]\nplay_path = D:/x\n")
    with pytest.raises(LeagueError) as exc:
        load_league()
    msg = str(exc.value)
    assert "AFCL" not in msg
    assert "Configured leagues" not in msg
    with pytest.raises(LeagueError) as exc2:
        load_league("AFCL")
    assert "[league.AFCL]" in str(exc2.value)


# ── resolve_path: config-relative (ruff/mypy idiom), absolute untouched ──


def test_resolve_path_relative_is_under_config_dir(config_dir: Path) -> None:
    assert resolve_path("rules\\PNFL.gameplan.toml") == (
        config_dir / "rules" / "PNFL.gameplan.toml"
    )


def test_resolve_path_absolute_is_unchanged() -> None:
    assert resolve_path("D:\\rules\\x.toml") == Path("D:\\rules\\x.toml")


# ── [DEFAULT] cascade + %(key)s interpolation ──


def test_default_cascade_and_interpolation(write_config: WriteConfig) -> None:
    write_config(
        "[DEFAULT]\nroster_path = %(league_root)s/rosters\n"
        "[league.PNFL]\nleague_root = D:/Leagues/PNFL\nplay_path = %(league_root)s/plays\n",
    )
    cfg = load_league("PNFL")
    assert cfg["play_path"] == "D:/Leagues/PNFL/plays"  # in-section interpolation
    assert cfg["roster_path"] == "D:/Leagues/PNFL/rosters"  # DEFAULT cascade + interp


# ── shipped release/athc.ini: every section loader reads it as installed ──

RELEASE = Path(__file__).resolve().parents[2] / "release"


@pytest.fixture
def release_config_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point config lookup at the shipped `release/` folder itself (overriding the
    autouse temp dir) so relative rule paths resolve to the bundled
    `release/rules/`. `ATHC_LEAGUE` is cleared so the league comes from the file,
    as on a fresh install."""
    monkeypatch.setenv("ATHC_CONFIG_DIR", str(RELEASE))
    monkeypatch.delenv("ATHC_LEAGUE", raising=False)


@pytest.mark.usefixtures("release_config_dir")
def test_release_league_section_loads() -> None:
    league = load_league()  # [athc] default_league -> [league.PNFL]
    assert league["play_path"]
    assert resolve_path(league["playpool_rules"]).is_file()


@pytest.mark.usefixtures("release_config_dir")
def test_release_autocontinue_section_loads() -> None:
    autocontinue_config.load_config()


@pytest.mark.usefixtures("release_config_dir")
def test_release_gameplan_config_loads() -> None:
    cfg = gameplan_config.load_config()
    assert cfg.playpool_rules is not None and cfg.playpool_rules.is_file()
    assert cfg.rule_files and all(p.is_file() for p in cfg.rule_files)


@pytest.mark.usefixtures("release_config_dir")
def test_release_profile_config_loads() -> None:
    cfg = profile_config.load_config()
    assert cfg.rule_files and all(p.is_file() for p in cfg.rule_files)


@pytest.mark.usefixtures("release_config_dir")
def test_release_convert_pdb_config_loads() -> None:
    cfg = pdbtoexcel_config.load_config()
    assert cfg.playpool_rules is not None and cfg.playpool_rules.is_file()


# ── athc config command group: path / edit / reveal ──


def test_group_lists_subcommands(runner) -> None:
    result = runner.invoke(config_group, ["--help"])
    assert result.exit_code == 0
    assert "path" in result.output
    assert "edit" in result.output
    assert "reveal" in result.output


def test_path_prints_config_file(runner, config_dir: Path) -> None:
    result = runner.invoke(path, [])
    assert result.exit_code == 0
    assert result.output.strip() == str(config_dir / "athc.ini")


def test_reveal_selects_existing_file(
    runner, write_config: WriteConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    ini = write_config("[athc]\n")
    launched: list[tuple[tuple[object, ...], dict[str, object]]] = []
    monkeypatch.setattr("click.launch", lambda *a, **k: launched.append((a, k)))
    result = runner.invoke(reveal, [])
    assert result.exit_code == 0
    assert launched == [((str(ini),), {"locate": True})]


def test_reveal_opens_folder_when_absent(
    runner, config_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launched: list[tuple[tuple[object, ...], dict[str, object]]] = []
    monkeypatch.setattr("click.launch", lambda *a, **k: launched.append((a, k)))
    result = runner.invoke(reveal, [])
    assert result.exit_code == 0
    assert launched == [((str(config_dir),), {})]


def test_edit_no_env_opens_associated_app(
    runner, config_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("VISUAL", raising=False)
    monkeypatch.delenv("EDITOR", raising=False)
    launched: list[tuple[object, ...]] = []
    monkeypatch.setattr("click.launch", lambda *a, **k: launched.append(a))
    result = runner.invoke(edit, [])
    assert result.exit_code == 0
    ini = config_dir / "athc.ini"
    assert ini.exists()  # created when missing
    assert launched == [(str(ini),)]


def test_edit_uses_editor_env(
    runner, config_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("EDITOR", "myeditor")
    edited: list[dict[str, object]] = []
    launched: list[tuple[object, ...]] = []
    monkeypatch.setattr("click.edit", lambda **k: edited.append(k))
    monkeypatch.setattr("click.launch", lambda *a, **k: launched.append(a))
    result = runner.invoke(edit, [])
    assert result.exit_code == 0
    assert edited == [{"filename": str(config_dir / "athc.ini")}]
    assert launched == []


def test_edit_preserves_existing_file(
    runner, write_config: WriteConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("VISUAL", raising=False)
    monkeypatch.delenv("EDITOR", raising=False)
    ini = write_config("[athc]\ndefault_league = PNFL\n")
    monkeypatch.setattr("click.launch", lambda *a, **k: None)
    result = runner.invoke(edit, [])
    assert result.exit_code == 0
    assert ini.read_text(encoding="utf-8") == "[athc]\ndefault_league = PNFL\n"
