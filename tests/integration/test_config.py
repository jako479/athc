"""Direct tests for `athc.config` league resolution — the shared resolver every
`--league` tool calls.

`load_league_config` reads `config_dir()/athc.ini` and `leagues/<NAME>/league.ini`,
so per testing-integration.md these live in the integration tier (unit tests never
read config). Covered once here rather than per command. A league is a folder under
`leagues/`; `[athc] league` in athc.ini names the one used when no flag is given.

Also covers the `athc config` command group (path / edit / reveal), with the
editor and Explorer launches mocked.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from athc.cli.config import config as config_group
from athc.cli.config.edit import edit
from athc.cli.config.path import path
from athc.cli.config.reveal import reveal
from athc.config import (
    ConfigFileError,
    LeagueError,
    available_leagues,
    league_dir,
    load_league,
    load_league_config,
    resolve_league,
    resolve_path,
)

WriteConfig = Callable[..., Path]
MakeLeague = Callable[..., Path]


# ── resolution priority: --league arg → [athc] league ──


def test_resolves_explicit_league_arg(make_league: MakeLeague) -> None:
    make_league("PNFL", "[league]\nplay_path = D:/p\n")
    assert load_league("PNFL")["play_path"] == "D:/p"


def test_resolves_from_configured_league(
    make_league: MakeLeague, write_config: WriteConfig
) -> None:
    make_league("PNFL", "[league]\nplay_path = D:/p\n")
    write_config("[athc]\nleague = PNFL\n")
    assert load_league()["play_path"] == "D:/p"


# ── resolve_league: the name alone, same priority ──


def test_resolve_league_returns_the_explicit_name(make_league: MakeLeague) -> None:
    make_league("PNFL", "[league]\nplay_path = D:/p\n")
    assert resolve_league("PNFL") == "PNFL"


def test_resolve_league_falls_back_to_configured(
    make_league: MakeLeague, write_config: WriteConfig
) -> None:
    make_league("DEF")
    write_config("[athc]\nleague = DEF\n")
    assert resolve_league() == "DEF"


def test_resolve_league_errors_when_none_resolvable(make_league: MakeLeague) -> None:
    make_league("PNFL")
    with pytest.raises(LeagueError, match="no league selected"):
        resolve_league()


def test_resolve_league_errors_on_unknown_name(make_league: MakeLeague) -> None:
    make_league("PNFL")
    with pytest.raises(LeagueError, match="PCFL"):
        resolve_league("PCFL")


# ── LeagueConfig helpers ──


def test_league_config_names_folder(make_league: MakeLeague, config_dir: Path) -> None:
    make_league("PNFL", "[league]\nplay_path = D:/p\n")
    cfg = load_league_config("PNFL")
    assert cfg.name == "PNFL"
    assert cfg.dir == config_dir / "leagues" / "PNFL"
    assert cfg.values == {"play_path": "D:/p"}


def test_missing_league_ini_gives_empty_values(make_league: MakeLeague) -> None:
    make_league("PNFL")  # folder only
    assert load_league_config("PNFL").values == {}


def test_path_resolves_relative_against_league_dir(make_league: MakeLeague) -> None:
    folder = make_league("PNFL", "[league]\nplay_path = plays\nabs = D:/x\n")
    cfg = load_league_config("PNFL")
    assert cfg.path("play_path") == folder / "plays"
    assert cfg.path("abs") == Path("D:/x")
    assert cfg.path("missing") is None


def test_rules_file_only_when_present(make_league: MakeLeague) -> None:
    folder = make_league("PNFL")
    cfg = load_league_config("PNFL")
    assert cfg.rules_file("gameplan.toml") is None
    (folder / "rules" / "gameplan.toml").write_text("", encoding="utf-8")
    assert cfg.rules_file("gameplan.toml") == folder / "rules" / "gameplan.toml"


def test_rule_files_default_is_the_fixed_file(make_league: MakeLeague) -> None:
    folder = make_league("PNFL")
    (folder / "rules" / "gameplan.toml").write_text("", encoding="utf-8")
    cfg = load_league_config("PNFL")
    assert cfg.rule_files("gameplan_rules", "gameplan.toml") == (
        folder / "rules" / "gameplan.toml",
    )


def test_rule_files_default_empty_when_fixed_file_missing(
    make_league: MakeLeague,
) -> None:
    make_league("PNFL")
    assert (
        load_league_config("PNFL").rule_files("gameplan_rules", "gameplan.toml") == ()
    )


def test_rule_files_list_replaces_default_in_order(make_league: MakeLeague) -> None:
    folder = make_league(
        "PNFL",
        "[league]\ngameplan_rules =\n    rules\\base.toml\n    D:\\house.toml\n",
    )
    (folder / "rules" / "gameplan.toml").write_text("", encoding="utf-8")
    cfg = load_league_config("PNFL")
    assert cfg.rule_files("gameplan_rules", "gameplan.toml") == (
        folder / "rules" / "base.toml",
        Path("D:\\house.toml"),
    )


# ── errors ──


def test_no_league_resolvable_lists_available(make_league: MakeLeague) -> None:
    make_league("PNFL")
    make_league("PCFL")
    with pytest.raises(LeagueError) as exc:
        load_league()
    msg = str(exc.value)
    assert "no league selected" in msg
    assert "athc config set league" in msg
    assert "Available: PCFL, PNFL" in msg


def test_no_league_and_no_folders(config_dir: Path) -> None:
    with pytest.raises(LeagueError) as exc:
        load_league()
    assert str(config_dir / "leagues") in str(exc.value)


def test_unknown_league_errors(make_league: MakeLeague) -> None:
    make_league("PNFL")
    with pytest.raises(LeagueError) as exc:
        load_league("PCFL")
    msg = str(exc.value)
    assert "PCFL" in msg and "not found" in msg
    assert "Available: PNFL" in msg


def test_empty_league_key_is_no_league(write_config: WriteConfig) -> None:
    write_config("[athc]\nleague =\n")
    with pytest.raises(LeagueError, match="no league selected"):
        load_league()


@pytest.mark.parametrize("name", ["..", "..\\x", "a/b", "a\\b"])
def test_league_dir_rejects_path_segments(name: str, config_dir: Path) -> None:
    (config_dir / "x").mkdir()  # a real sibling folder `..\x` would point at
    with pytest.raises(LeagueError, match="not found"):
        league_dir(name)


@pytest.mark.parametrize("name", ["", "   "])
def test_league_dir_rejects_blank_names(name: str, config_dir: Path) -> None:
    (config_dir / "leagues").mkdir()  # "" would resolve to this folder itself
    with pytest.raises(LeagueError, match="not found"):
        league_dir(name)


def test_resolve_league_blank_arg_is_no_arg(
    make_league: MakeLeague, write_config: WriteConfig
) -> None:
    # `--league "   "` behaves like no flag: the configured league is used.
    make_league("PNFL")
    write_config("[athc]\nleague = PNFL\n")
    assert load_league_config("   ").name == "PNFL"


def test_malformed_athc_ini_errors(
    make_league: MakeLeague, write_config: WriteConfig
) -> None:
    # No explicit league: the league must come from athc.ini, so the malformed
    # file is actually read.
    make_league("PNFL")
    ini = write_config("[athc\nbroken\n")
    with pytest.raises(ConfigFileError) as exc:
        load_league_config()
    assert str(ini) in str(exc.value)


def test_percent_in_league_ini_is_config_file_error(make_league: MakeLeague) -> None:
    # `%LOCALAPPDATA%\plays` is the native Windows idiom; configparser sees a
    # broken `%(...)s` interpolation. It must surface as a ConfigFileError naming
    # the file, not as a raw configparser error.
    folder = make_league("PNFL", "[league]\nplay_path = %LOCALAPPDATA%\\plays\n")
    with pytest.raises(ConfigFileError) as exc:
        load_league("PNFL")
    assert str(folder / "league.ini") in str(exc.value)


def test_malformed_league_ini_errors(make_league: MakeLeague) -> None:
    folder = make_league("PNFL", "[league\nbroken")
    with pytest.raises(ConfigFileError) as exc:
        load_league("PNFL")
    assert str(folder / "league.ini") in str(exc.value)


def test_available_leagues_lists_folders_only(
    make_league: MakeLeague, config_dir: Path
) -> None:
    make_league("B")
    make_league("A")
    (config_dir / "leagues" / "stray.txt").write_text("", encoding="utf-8")
    assert available_leagues() == ["A", "B"]


def test_available_leagues_without_folder(config_dir: Path) -> None:
    assert available_leagues() == []


# ── resolve_path: config-relative (ruff/mypy idiom), absolute untouched ──


def test_resolve_path_relative_is_under_config_dir(config_dir: Path) -> None:
    assert resolve_path("rules\\x.toml") == config_dir / "rules" / "x.toml"


def test_resolve_path_absolute_is_unchanged() -> None:
    assert resolve_path("D:\\rules\\x.toml") == Path("D:\\rules\\x.toml")


# ── %(key)s interpolation inside league.ini ──


def test_interpolation_within_league_ini(make_league: MakeLeague) -> None:
    make_league(
        "PNFL",
        "[league]\nleague_root = D:/Leagues/PNFL\nplay_path = %(league_root)s/plays\n",
    )
    assert load_league("PNFL")["play_path"] == "D:/Leagues/PNFL/plays"


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


def test_edit_opens_associated_app(
    runner, config_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launched: list[tuple[object, ...]] = []
    monkeypatch.setattr("click.launch", lambda *a, **k: launched.append(a))
    result = runner.invoke(edit, [])
    assert result.exit_code == 0
    ini = config_dir / "athc.ini"
    assert ini.exists()  # created when missing
    assert launched == [(str(ini),)]


def test_edit_ignores_editor_env(
    runner, config_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VISUAL", "myvisual")
    monkeypatch.setenv("EDITOR", "myeditor")
    edited: list[dict[str, object]] = []
    launched: list[tuple[object, ...]] = []
    monkeypatch.setattr("click.edit", lambda **k: edited.append(k))
    monkeypatch.setattr("click.launch", lambda *a, **k: launched.append(a))
    result = runner.invoke(edit, [])
    assert result.exit_code == 0
    assert edited == []
    assert launched == [(str(config_dir / "athc.ini"),)]


def test_edit_preserves_existing_file(
    runner, write_config: WriteConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    ini = write_config("[athc]\nleague = PNFL\n")
    monkeypatch.setattr("click.launch", lambda *a, **k: None)
    result = runner.invoke(edit, [])
    assert result.exit_code == 0
    assert ini.read_text(encoding="utf-8") == "[athc]\nleague = PNFL\n"


# ── shipped release/: every loader reads it as installed ──

RELEASE = Path(__file__).resolve().parents[2] / "release"


@pytest.fixture
def release_config_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point config lookup at the shipped `release/` folder itself (overriding the
    autouse temp dir), as on a fresh install."""
    monkeypatch.setenv("ATHC_CONFIG_DIR", str(RELEASE))


@pytest.mark.usefixtures("release_config_dir")
def test_release_league_loads() -> None:
    cfg = load_league_config()  # [athc] league -> leagues/PNFL/
    assert cfg.name == "PNFL"
    assert cfg.values["play_path"]
    assert (cfg.dir / "standings").is_dir()


@pytest.mark.usefixtures("release_config_dir")
@pytest.mark.parametrize("name", ["PNFL", "PCFL"])
def test_release_every_league_has_a_play_path(name: str) -> None:
    assert load_league(name)["play_path"]


@pytest.mark.usefixtures("release_config_dir")
def test_release_autocontinue_section_loads() -> None:
    from athc.autocontinue import config as autocontinue_config

    autocontinue_config.load_config()


@pytest.mark.usefixtures("release_config_dir")
def test_release_gameplan_config_loads() -> None:
    from athc.gameplan import config as gameplan_config

    cfg = gameplan_config.load_config()
    assert cfg.playpool_rules is not None and cfg.playpool_rules.is_file()
    assert cfg.rule_files and all(p.is_file() for p in cfg.rule_files)


@pytest.mark.usefixtures("release_config_dir")
def test_release_profile_config_loads() -> None:
    from athc.profile import config as profile_config

    cfg = profile_config.load_config()
    assert cfg.rule_files and all(p.is_file() for p in cfg.rule_files)


@pytest.mark.usefixtures("release_config_dir")
def test_release_convert_pdb_config_loads() -> None:
    from athc.pdbtoexcel import config as pdbtoexcel_config

    cfg = pdbtoexcel_config.load_config()
    assert cfg.playpool_rules is not None and cfg.playpool_rules.is_file()
    # A play_path override alone still reads the league's rules\playpool.toml.
    rules = pdbtoexcel_config.load_config(play_path="D:/plays").playpool_rules
    assert rules == RELEASE / "leagues" / "PNFL" / "rules" / "playpool.toml"
    # The shipped [convert-pdb] section spells out the defaults.
    assert cfg.calculate_percentages is True
    assert cfg.include_category_worksheets is False
    assert cfg.exclude_sacks_from_pass_attempts is True


@pytest.mark.usefixtures("release_config_dir")
@pytest.mark.parametrize(("league", "season"), [("PNFL", 2048), ("PCFL", 2029)])
def test_release_scheduler_files_load(league: str, season: int) -> None:
    from athc.scheduler.config import (
        find_league_path,
        load_scheduler_config,
        scheduler_rules_path,
    )

    load_scheduler_config(scheduler_rules_path(league))
    assert find_league_path(league, season).is_file()


def test_dev_mirrors_release_layout() -> None:
    dev = RELEASE.parent / "dev"
    for rel in (
        "athc.ini",
        "leagues/PNFL/league.ini",
        "leagues/PNFL/rules/gameplan.toml",
        "leagues/PNFL/rules/profile.toml",
        "leagues/PNFL/rules/playpool.toml",
        "leagues/PNFL/rules/scheduler.toml",
        "leagues/PNFL/standings/2048.league.ini",
        "leagues/PCFL/league.ini",
        "leagues/PCFL/rules/scheduler.toml",
        "leagues/PCFL/standings/2029.league.ini",
    ):
        assert (dev / rel).is_file(), rel
        assert (RELEASE / rel).is_file(), rel
