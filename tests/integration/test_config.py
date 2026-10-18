"""Direct tests for `athc.config` league resolution — the shared resolver every
`--league` tool calls.

`load_league_config` reads `config_dir()/athc.toml` and `leagues/<NAME>/league.toml`,
so per testing-integration.md these live in the integration tier (unit tests never
read config). Covered once here rather than per command. A league is a folder under
`leagues/`; `[athc] league` in athc.toml names the one used when no flag is given.

Also covers the `athc config` command group (path / edit / reveal / get), with
the editor and Explorer launches mocked.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import click
import pytest

from athc.cli import cli
from athc.cli.config import config as config_group
from athc.cli.config.edit import edit
from athc.cli.config.get import get
from athc.cli.config.path import path
from athc.cli.config.reveal import reveal
from athc.config import (
    ConfigFileError,
    LeagueError,
    available_leagues,
    league_dir,
    load_config,
    load_league,
    load_league_config,
    play_dir,
    resolve_league,
    resolve_path,
)
from athc.errors import ACCESS_DENIED, DIRECTORY_INVALID, PATH_NOT_FOUND
from athc.fbpro98_play import CategoryLabels
from tests.conftest import (
    CATEGORIES_TOML,
    LEAGUE,
    OTHER_LEAGUE,
    PNFL_LABELS,
    athc_toml,
    league_not_found,
    no_league_selected,
    toml_error,
)

WriteConfig = Callable[..., Path]
MakeLeague = Callable[..., Path]

# An athc.toml that is not valid TOML.
BROKEN = "[athc\nbroken\n"


# ── resolution priority: --league arg → [athc] league ──


def test_resolves_explicit_league_arg(make_league: MakeLeague) -> None:
    make_league(LEAGUE, "[league]\nplay_path = 'D:/p'\n")
    assert load_league(LEAGUE)["play_path"] == "D:/p"


def test_resolves_from_configured_league(
    make_league: MakeLeague, write_config: WriteConfig
) -> None:
    make_league(LEAGUE, "[league]\nplay_path = 'D:/p'\n")
    write_config(athc_toml())
    assert load_league()["play_path"] == "D:/p"


# ── resolve_league: the name alone, same priority ──


def test_resolve_league_returns_the_explicit_name(make_league: MakeLeague) -> None:
    make_league(LEAGUE, "[league]\nplay_path = 'D:/p'\n")
    assert resolve_league(LEAGUE) == LEAGUE


def test_resolve_league_falls_back_to_configured(
    make_league: MakeLeague, write_config: WriteConfig
) -> None:
    make_league("DEF")
    write_config(athc_toml("DEF"))
    assert resolve_league() == "DEF"


def test_resolve_league_errors_when_none_resolvable(make_league: MakeLeague) -> None:
    make_league()
    with pytest.raises(LeagueError, match="League is not set"):
        resolve_league()


def test_resolve_league_errors_on_unknown_name(make_league: MakeLeague) -> None:
    make_league()
    with pytest.raises(LeagueError, match=OTHER_LEAGUE):
        resolve_league(OTHER_LEAGUE)


# ── LeagueConfig helpers ──


def test_league_config_names_folder(make_league: MakeLeague, config_dir: Path) -> None:
    make_league(LEAGUE, "[league]\nplay_path = 'D:/p'\n")
    cfg = load_league_config(LEAGUE)
    assert cfg.name == LEAGUE
    assert cfg.dir == config_dir / "leagues" / LEAGUE
    assert cfg.values == {"play_path": "D:/p"}


def test_missing_league_toml_gives_empty_values(make_league: MakeLeague) -> None:
    make_league()  # folder only
    assert load_league_config(LEAGUE).values == {}


def test_path_resolves_relative_against_league_dir(make_league: MakeLeague) -> None:
    folder = make_league(LEAGUE, "[league]\nplay_path = 'plays'\nabs = 'D:/x'\n")
    cfg = load_league_config(LEAGUE)
    assert cfg.path("play_path") == folder / "plays"
    assert cfg.path("abs") == Path("D:/x")
    assert cfg.path("missing") is None


def test_rules_file_only_when_present(make_league: MakeLeague) -> None:
    folder = make_league()
    cfg = load_league_config(LEAGUE)
    assert cfg.rules_file("gameplan.toml") is None
    (folder / "gameplan.toml").write_text("", encoding="utf-8")
    assert cfg.rules_file("gameplan.toml") == folder / "gameplan.toml"


def test_rule_files_default_is_the_fixed_file(make_league: MakeLeague) -> None:
    folder = make_league()
    (folder / "gameplan.toml").write_text("", encoding="utf-8")
    cfg = load_league_config(LEAGUE)
    assert cfg.rule_files("gameplan_rules", "gameplan.toml") == (
        folder / "gameplan.toml",
    )


def test_rule_files_default_empty_when_fixed_file_missing(
    make_league: MakeLeague,
) -> None:
    make_league()
    assert (
        load_league_config(LEAGUE).rule_files("gameplan_rules", "gameplan.toml") == ()
    )


def test_rule_files_list_replaces_default_in_order(make_league: MakeLeague) -> None:
    folder = make_league(
        LEAGUE,
        "[league]\ngameplan_rules = ['base.toml', 'D:\\house.toml']\n",
    )
    (folder / "gameplan.toml").write_text("", encoding="utf-8")
    cfg = load_league_config(LEAGUE)
    assert cfg.rule_files("gameplan_rules", "gameplan.toml") == (
        folder / "base.toml",
        Path("D:\\house.toml"),
    )


# ── errors ──


def test_no_league_resolvable_lists_available(make_league: MakeLeague) -> None:
    make_league()
    make_league(OTHER_LEAGUE)
    with pytest.raises(LeagueError) as exc:
        load_league()
    msg = str(exc.value)
    assert "League is not set" in msg
    assert "athc config set league" in msg
    assert f"Available: {OTHER_LEAGUE}, {LEAGUE}" in msg


def test_no_league_and_no_folders(config_dir: Path) -> None:
    with pytest.raises(LeagueError) as exc:
        load_league()
    assert str(config_dir / "leagues") in str(exc.value)


def test_unknown_league_errors(make_league: MakeLeague) -> None:
    make_league()
    with pytest.raises(LeagueError) as exc:
        load_league(OTHER_LEAGUE)
    msg = str(exc.value)
    assert OTHER_LEAGUE in msg and "not found" in msg
    assert f"Available: {LEAGUE}" in msg


def test_empty_league_key_is_no_league(write_config: WriteConfig) -> None:
    write_config('[athc]\nleague = ""\n')
    with pytest.raises(LeagueError, match="League is not set"):
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
    make_league()
    write_config(athc_toml())
    assert load_league_config("   ").name == LEAGUE


def test_malformed_athc_toml_errors(write_config: WriteConfig) -> None:
    # No explicit league: the league must come from athc.toml, so the malformed
    # file is actually read.
    body = "[athc\nbroken\n"
    toml = write_config(body)
    with pytest.raises(ConfigFileError) as exc:
        load_league_config()
    assert str(exc.value) == f"{toml}: {toml_error(body)}"
    assert exc.value.path == toml


def test_an_athc_toml_that_is_not_utf8_names_the_file(config_dir: Path) -> None:
    """Saved as ANSI with an accent in it: a config error naming the file, not
    a crash."""
    toml = config_dir / "athc.toml"
    toml.write_bytes(b"[athc]\n# caf\xe9\nleague = 'PNFL'\n")
    with pytest.raises(ConfigFileError) as exc:
        load_config()
    assert str(exc.value) == f"{toml}: Not UTF-8 text. Save it as UTF-8."


def test_an_athc_toml_that_cannot_be_opened_fails_in_windows_words(
    config_dir: Path,
) -> None:
    """Never read as an empty file: a folder in its place reads as `type`
    says of one."""
    toml = config_dir / "athc.toml"
    toml.mkdir(parents=True)
    with pytest.raises(ConfigFileError) as exc:
        load_config()
    assert str(exc.value) == f"{toml}: {ACCESS_DENIED}"


def test_an_athc_toml_with_a_bom_loads(
    config_dir: Path, make_league: MakeLeague
) -> None:
    """A UTF-8 byte-order mark (Notepad) is dropped, not a parse error."""
    make_league()
    (config_dir / "athc.toml").write_text(athc_toml(LEAGUE), encoding="utf-8-sig")
    assert resolve_league() == LEAGUE


def test_league_must_be_a_string(
    write_config: WriteConfig, make_league: MakeLeague
) -> None:
    make_league()
    toml = write_config("[athc]\nleague = 1\n")
    with pytest.raises(ConfigFileError) as exc:
        resolve_league()
    assert str(exc.value) == f"{toml}: [athc] league: Expected a string."


def test_a_section_written_as_a_value_is_an_error(write_config: WriteConfig) -> None:
    toml = write_config("athc = 1\n")
    with pytest.raises(ConfigFileError) as exc:
        resolve_league()
    assert str(exc.value) == f"{toml}: [athc]: Must be a table."


def test_percent_in_league_toml_is_literal(make_league: MakeLeague) -> None:
    # TOML has no %-interpolation, so a native Windows `%LOCALAPPDATA%` path
    # loads as written.
    make_league(LEAGUE, "[league]\nplay_path = '%LOCALAPPDATA%\\plays'\n")
    assert load_league(LEAGUE)["play_path"] == "%LOCALAPPDATA%\\plays"


def test_malformed_league_toml_errors(make_league: MakeLeague) -> None:
    folder = make_league(LEAGUE, "[league\nbroken")
    with pytest.raises(ConfigFileError) as exc:
        load_league(LEAGUE)
    assert str(folder / "league.toml") in str(exc.value)


def test_a_league_toml_that_is_not_utf8_names_the_file(make_league: MakeLeague) -> None:
    """Saved as ANSI with an accent in it: a config error naming the file, as
    for athc.toml, not a crash."""
    toml = make_league() / "league.toml"
    toml.write_bytes(b"[league]\n# caf\xe9\nteam = 'Denver'\n")
    with pytest.raises(ConfigFileError) as exc:
        load_league_config(LEAGUE)
    assert str(exc.value) == f"{toml}: Not UTF-8 text. Save it as UTF-8."


def test_bom_in_league_toml_is_skipped(make_league: MakeLeague) -> None:
    """A UTF-8 byte-order mark (Notepad, Excel) is dropped, not a parse error."""
    folder = make_league(LEAGUE)
    (folder / "league.toml").write_text(
        "[league]\nplay_path = 'plays'\n", encoding="utf-8-sig"
    )
    assert load_league(LEAGUE)["play_path"] == "plays"


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


# ── [league] value types ──


def test_no_interpolation_in_league_toml(make_league: MakeLeague) -> None:
    body = "[league]\nleague_root = 'D:/x'\nplay_path = '%(league_root)s/plays'\n"
    make_league(LEAGUE, body)
    assert load_league(LEAGUE)["play_path"] == "%(league_root)s/plays"


def test_league_list_is_kept_apart_from_values(make_league: MakeLeague) -> None:
    make_league(LEAGUE, "[league]\nplay_path = 'D:/p'\ngameplan_rules = ['a.toml']\n")
    cfg = load_league_config(LEAGUE)
    assert cfg.values == {"play_path": "D:/p"}
    assert cfg.lists == {"gameplan_rules": ("a.toml",)}


@pytest.mark.parametrize(
    "body",
    [
        "[league]\nplay_path = 1\n",
        "[league]\ngameplan_rules = ['a.toml', 1]\n",
        "[league]\nplay_path = { x = 1 }\n",
    ],
)
def test_league_value_wrong_type_errors(make_league: MakeLeague, body: str) -> None:
    folder = make_league(LEAGUE, body)
    with pytest.raises(ConfigFileError) as exc:
        load_league_config(LEAGUE)
    assert "Expected a string or an array of strings." in str(exc.value)
    assert str(folder / "league.toml") in str(exc.value)


def test_path_rejects_an_array_value(make_league: MakeLeague) -> None:
    folder = make_league(LEAGUE, "[league]\nplay_path = ['D:/p']\n")
    cfg = load_league_config(LEAGUE)
    with pytest.raises(ConfigFileError, match="play_path: Expected a string") as exc:
        cfg.path("play_path")
    assert str(folder / "league.toml") in str(exc.value)
    assert exc.value.path == folder / "league.toml"


@pytest.mark.parametrize(
    ("line", "value"),
    [
        ("team = 'Denver'\n", "Denver"),
        ("team = ' Denver '\n", "Denver"),
        ("team = '  '\n", None),
        ("", None),
    ],
    ids=["value", "spaces around", "blank", "absent"],
)
def test_string_value(make_league: MakeLeague, line: str, value: str | None) -> None:
    make_league(LEAGUE, f"[league]\n{line}")
    assert load_league_config(LEAGUE).string("team") == value


def test_string_rejects_an_array_value(make_league: MakeLeague) -> None:
    folder = make_league(LEAGUE, "[league]\nteam = ['Denver']\n")
    cfg = load_league_config(LEAGUE)
    with pytest.raises(ConfigFileError) as exc:
        cfg.string("team")
    assert str(exc.value) == (
        f"{folder / 'league.toml'}: [league] team: Expected a string, got an array."
    )


def test_rule_files_rejects_a_string_value(make_league: MakeLeague) -> None:
    folder = make_league(LEAGUE, "[league]\ngameplan_rules = 'house.toml'\n")
    cfg = load_league_config(LEAGUE)
    with pytest.raises(
        ConfigFileError, match="gameplan_rules: Expected an array of strings"
    ) as exc:
        cfg.rule_files("gameplan_rules", "gameplan.toml")
    assert str(folder / "league.toml") in str(exc.value)


def test_league_section_not_a_table_errors(make_league: MakeLeague) -> None:
    make_league(LEAGUE, "league = 1\n")
    with pytest.raises(ConfigFileError, match=r"\[league\]: Must be a table\."):
        load_league_config(LEAGUE)


# ── [categories] → CategoryLabels ──


def test_categories_load(make_league: MakeLeague) -> None:
    make_league(LEAGUE, "[league]\nplay_path = 'D:/p'\n" + CATEGORIES_TOML)
    assert load_league_config(LEAGUE).categories == PNFL_LABELS


def test_categories_absent_is_no_labels(make_league: MakeLeague) -> None:
    make_league(LEAGUE, "[league]\nplay_path = 'D:/p'\n")
    assert load_league_config(LEAGUE).categories == CategoryLabels()


def test_one_side_only_loads(make_league: MakeLeague) -> None:
    make_league(LEAGUE, '[categories.defense]\n"Run Left" = "RunLeft"\n')
    cfg = load_league_config(LEAGUE)
    assert cfg.categories.offense == {}
    assert cfg.categories.defense_by_label("RunLeft") is not None


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ('[categories.offense]\n"Run Rite" = "RR"\n', "Not a game category name"),
        ('[categories.offense]\n"Run Right" = ""\n', "non-empty string"),
        ('[categories.offense]\n"Run Right" = 1\n', "non-empty string"),
        (
            '[categories.offense]\n"Run Right" = "RR"\n"Run Left" = "RR"\n',
            "already used",
        ),
        ('[categories.defense]\n"Run Right" = "Run Left"\n', "is a game category name"),
        ("[categories]\noffense = 1\n", r"\[categories.offense\]: Must be a table\."),
        ("categories = 1\n", r"\[categories\]: Must be a table\."),
    ],
)
def test_categories_errors_name_the_file(
    make_league: MakeLeague, body: str, message: str
) -> None:
    folder = make_league(LEAGUE, body)
    with pytest.raises(ConfigFileError, match=message) as exc:
        load_league_config(LEAGUE)
    assert str(folder / "league.toml") in str(exc.value)
    assert exc.value.path == folder / "league.toml"


# ── athc config command group: path / edit / reveal / get ──

Launches = list[tuple[tuple[object, ...], dict[str, object]]]


def test_group_lists_subcommands(runner) -> None:
    result = runner.invoke(config_group, ["--help"])
    assert result.exit_code == 0
    assert "path" in result.stdout
    assert "edit" in result.stdout
    assert "reveal" in result.stdout
    assert "get" in result.stdout


def test_path_prints_config_file(runner, config_dir: Path) -> None:
    result = runner.invoke(path, [])
    assert result.exit_code == 0
    assert result.stdout == f"{config_dir / 'athc.toml'}\n"


def test_reveal_selects_existing_file(
    runner, write_config: WriteConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    toml = write_config("[athc]\n")
    launched: list[tuple[tuple[object, ...], dict[str, object]]] = []
    monkeypatch.setattr("click.launch", lambda *a, **k: launched.append((a, k)))
    result = runner.invoke(reveal, [])
    assert result.exit_code == 0
    assert launched == [((str(toml),), {"locate": True})]


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
    monkeypatch.setattr("os.startfile", lambda *a, **k: launched.append(a))
    result = runner.invoke(edit, [])
    assert result.exit_code == 0
    toml = config_dir / "athc.toml"
    assert toml.exists()  # created when missing
    assert launched == [(str(toml),)]


def test_edit_ignores_editor_env(
    runner, config_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VISUAL", "myvisual")
    monkeypatch.setenv("EDITOR", "myeditor")
    edited: list[dict[str, object]] = []
    launched: list[tuple[object, ...]] = []
    monkeypatch.setattr("click.edit", lambda **k: edited.append(k))
    monkeypatch.setattr("os.startfile", lambda *a, **k: launched.append(a))
    result = runner.invoke(edit, [])
    assert result.exit_code == 0
    assert edited == []
    assert launched == [(str(config_dir / "athc.toml"),)]


def test_edit_preserves_existing_file(
    runner, write_config: WriteConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    toml = write_config(athc_toml())
    monkeypatch.setattr("os.startfile", lambda *a, **k: None)
    result = runner.invoke(edit, [])
    assert result.exit_code == 0
    assert toml.read_text(encoding="utf-8") == athc_toml()


# Windows' text for error 1155, as Python gives it (without the period).
NO_APP = "No application is associated with the specified file for this operation"


def test_edit_reports_a_file_windows_cannot_open(
    runner, config_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_app(path: str) -> None:
        raise OSError(0, NO_APP, path, 1155)  # errno, text, file name, winerror

    monkeypatch.setattr("os.startfile", no_app)
    result = runner.invoke(edit, [])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {config_dir / 'athc.toml'}: {NO_APP}.\n"
    assert result.stdout == ""


def test_edit_league_toml_missing_fails(
    runner,
    make_league: MakeLeague,
    write_config: WriteConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    folder = make_league()  # no league.toml
    write_config(athc_toml())
    launched: list[tuple[object, ...]] = []
    monkeypatch.setattr("os.startfile", lambda *a, **k: launched.append(a))
    result = runner.invoke(edit, ["league.toml"])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {folder / 'league.toml'}: The system cannot find the file specified.\n"
    )
    assert not (folder / "league.toml").exists()  # nothing created
    assert launched == []  # nothing opened


def test_edit_league_toml_opens_it(
    runner,
    make_league: MakeLeague,
    write_config: WriteConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    folder = make_league(LEAGUE, "[league]\nteam = 'Denver'\n")
    write_config(athc_toml())
    launched: list[tuple[object, ...]] = []
    monkeypatch.setattr("os.startfile", lambda *a, **k: launched.append(a))
    result = runner.invoke(edit, ["league.toml"])
    assert result.exit_code == 0
    assert result.stdout == ""
    assert launched == [(str(folder / "league.toml"),)]
    toml = folder / "league.toml"
    assert toml.read_text(encoding="utf-8") == "[league]\nteam = 'Denver'\n"


def test_reveal_league_toml_selects_it(
    runner,
    make_league: MakeLeague,
    write_config: WriteConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    folder = make_league(LEAGUE, "[league]\n")
    write_config(athc_toml())
    launched: Launches = []
    monkeypatch.setattr("click.launch", lambda *a, **k: launched.append((a, k)))
    result = runner.invoke(reveal, ["league.toml"])
    assert result.exit_code == 0
    assert launched == [((str(folder / "league.toml"),), {"locate": True})]


def test_reveal_league_toml_missing_opens_the_league_folder(
    runner,
    make_league: MakeLeague,
    write_config: WriteConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    folder = make_league()  # no league.toml
    write_config(athc_toml())
    launched: Launches = []
    monkeypatch.setattr("click.launch", lambda *a, **k: launched.append((a, k)))
    result = runner.invoke(reveal, ["league.toml"])
    assert result.exit_code == 0
    assert launched == [((str(folder),), {})]


# ── FILE and --league on path, edit and reveal ──


@pytest.mark.parametrize("file", ["league.toml", "League.TOML"])
def test_league_toml_is_the_league_in_use(
    runner, make_league: MakeLeague, write_config: WriteConfig, file: str
) -> None:
    folder = make_league(LEAGUE, "[league]\n")
    make_league(OTHER_LEAGUE, "[league]\n")
    write_config(athc_toml())
    result = runner.invoke(path, [file])
    assert result.exit_code == 0
    assert result.stdout == f"{folder / 'league.toml'}\n"


def test_path_league_toml_missing_prints_the_path(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    folder = make_league()  # no league.toml
    write_config(athc_toml())
    result = runner.invoke(path, ["league.toml"])
    assert result.exit_code == 0
    assert result.stdout == f"{folder / 'league.toml'}\n"
    assert not (folder / "league.toml").exists()


def test_file_rejects_another_word(runner, make_league: MakeLeague) -> None:
    """FILE's two names are accepted above; a league name typed there is not.
    path, edit and reveal share the one FILE check."""
    make_league("PCFL")
    result = runner.invoke(path, ["PCFL"])
    assert result.exit_code == 2
    assert result.stderr.endswith(
        "Error: Invalid value for 'FILE': 'PCFL' is not one of 'athc.toml', "
        "'league.toml'.\n"
    )


@pytest.mark.parametrize(
    ("command", "args"),
    [
        (path, ["athc.toml", "x"]),
        (edit, ["athc.toml", "x"]),
        (reveal, ["athc.toml", "x"]),
        (get, ["league", "x"]),
    ],
    ids=["path", "edit", "reveal", "get"],
)
def test_a_word_too_many(
    runner, monkeypatch: pytest.MonkeyPatch, command: click.Command, args: list[str]
) -> None:
    launched: list[tuple[object, ...]] = []
    monkeypatch.setattr("os.startfile", lambda *a, **k: launched.append(a))
    monkeypatch.setattr("click.launch", lambda *a, **k: launched.append(a))
    result = runner.invoke(command, args)
    assert result.exit_code == 2
    assert result.stderr.endswith("Error: Got unexpected extra argument (x).\n")
    assert launched == []


@pytest.mark.parametrize(
    "args",
    [["--league", OTHER_LEAGUE], ["league.toml", "--league", OTHER_LEAGUE]],
    ids=["league alone", "league.toml and league"],
)
def test_named_league_is_its_league_toml(
    runner, make_league: MakeLeague, write_config: WriteConfig, args: list[str]
) -> None:
    make_league(LEAGUE, "[league]\n")
    other = make_league(OTHER_LEAGUE, "[league]\n")
    write_config(athc_toml())
    result = runner.invoke(path, args)
    assert result.exit_code == 0
    assert result.stdout == f"{other / 'league.toml'}\n"


def test_athc_toml_with_a_named_league_is_athc_toml(
    runner, make_league: MakeLeague, config_dir: Path
) -> None:
    make_league(OTHER_LEAGUE)
    result = runner.invoke(path, ["athc.toml", "--league", OTHER_LEAGUE])
    assert result.exit_code == 0
    assert result.stdout == f"{config_dir / 'athc.toml'}\n"


def test_athc_toml_with_an_unknown_league_fails(
    runner, make_league: MakeLeague, config_dir: Path
) -> None:
    make_league()
    result = runner.invoke(path, ["athc.toml", "--league", "NOPE"])
    assert result.exit_code == 2
    assert result.stderr == league_not_found(config_dir, "NOPE", LEAGUE)
    assert result.stdout == ""


def test_league_toml_with_no_league_set(
    runner, make_league: MakeLeague, config_dir: Path
) -> None:
    make_league()
    result = runner.invoke(path, ["league.toml"])
    assert result.exit_code == 2
    assert result.stderr == no_league_selected(config_dir, LEAGUE)
    assert result.stdout == ""


def test_unknown_named_league(
    runner, make_league: MakeLeague, config_dir: Path
) -> None:
    make_league()
    result = runner.invoke(path, ["--league", "NOPE"])
    assert result.exit_code == 2
    assert result.stderr == league_not_found(config_dir, "NOPE", LEAGUE)


def test_league_without_a_name(runner) -> None:
    result = runner.invoke(path, ["--league"])
    assert result.exit_code == 2
    assert result.stderr.endswith("Error: Option '--league' requires an argument.\n")


def test_league_toml_with_a_malformed_athc_toml(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    make_league()
    toml = write_config(BROKEN)
    result = runner.invoke(path, ["league.toml"])
    assert result.exit_code == 2
    assert result.stderr == (f"FAIL {toml}: {toml_error(BROKEN)}\n")


# ── athc config get ──

# Written as a coach writes it; printed the same way.
FOLDER = "C:\\SIERRA\\FBPRO98"
NOT_SET_LINES = {
    "path": "League files folder is not set. Run 'athc config set path FOLDER'.",
    "play_path": "Play pool folder is not set. Run 'athc config set play_path FOLDER'.",
    "team": "Team is not set. Run 'athc config set team NAME'.",
}
PPP_PATH_NOT_SET = "Game plan and profile folder is not set. The folders the league file names are used."


@pytest.mark.parametrize("key", ["league", "League", "LEAGUE"])
def test_get_league_prints_the_league_in_use(
    runner, make_league: MakeLeague, write_config: WriteConfig, key: str
) -> None:
    make_league()
    write_config(athc_toml())
    result = runner.invoke(get, [key])
    assert result.exit_code == 0
    assert result.stdout == f"{LEAGUE}\n"
    assert result.stderr == ""


def test_get_league_named(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    make_league()
    make_league(OTHER_LEAGUE)
    write_config(athc_toml())
    result = runner.invoke(get, ["league", "--league", OTHER_LEAGUE])
    assert result.exit_code == 0
    assert result.stdout == f"{OTHER_LEAGUE}\n"


@pytest.mark.parametrize(
    "body",
    ["", '[athc]\nleague = ""\n', '[athc]\nleague = "  "\n'],
    ids=["unset", "empty", "blank"],
)
def test_get_league_not_set(
    runner,
    make_league: MakeLeague,
    write_config: WriteConfig,
    config_dir: Path,
    body: str,
) -> None:
    make_league()
    make_league(OTHER_LEAGUE)
    write_config(body)
    result = runner.invoke(get, ["league"])
    assert result.exit_code == 2
    assert result.stderr == no_league_selected(config_dir, OTHER_LEAGUE, LEAGUE)
    assert result.stdout == ""


def test_get_league_folder_gone(
    runner, make_league: MakeLeague, write_config: WriteConfig, config_dir: Path
) -> None:
    make_league()
    write_config(athc_toml(OTHER_LEAGUE))
    result = runner.invoke(get, ["league"])
    assert result.exit_code == 2
    assert result.stderr == league_not_found(config_dir, OTHER_LEAGUE, LEAGUE)
    assert result.stdout == ""


def test_get_league_named_unknown(
    runner, make_league: MakeLeague, config_dir: Path
) -> None:
    make_league()
    result = runner.invoke(get, ["league", "--league", "NOPE"])
    assert result.exit_code == 2
    assert result.stderr == league_not_found(config_dir, "NOPE", LEAGUE)


def test_get_league_malformed_athc_toml(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    make_league()
    toml = write_config(BROKEN)
    result = runner.invoke(get, ["league"])
    assert result.exit_code == 2
    assert result.stderr == (f"FAIL {toml}: {toml_error(BROKEN)}\n")


def test_get_rejects_an_unknown_key(runner) -> None:
    """The five keys are accepted in the tests around this one; one past them
    is not."""
    result = runner.invoke(get, ["colour"])
    assert result.exit_code == 2
    assert result.stderr.endswith(
        "Error: Invalid value for 'KEY': 'colour' is not one of 'league', 'path', "
        "'play_path', 'team', 'ppp_path'.\n"
    )


def test_get_needs_a_key(runner) -> None:
    result = runner.invoke(get, [])
    assert result.exit_code == 2
    assert result.stderr.endswith("Error: Missing argument 'KEY'.\n")


@pytest.mark.parametrize("key", ["path", "play_path"])
def test_get_absolute_folder_as_written(
    runner, make_league: MakeLeague, write_config: WriteConfig, key: str
) -> None:
    make_league(LEAGUE, f"[league]\n{key} = '{FOLDER}'\n")
    write_config(athc_toml())
    result = runner.invoke(get, [key])
    assert result.exit_code == 0
    assert result.stdout == f"{FOLDER}\n"
    assert result.stderr == ""


def test_get_relative_ppp_path_is_under_the_league_folder(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    folder = make_league(LEAGUE, "[league]\nppp_path = 'Denver'\n")
    write_config(athc_toml())
    result = runner.invoke(get, ["ppp_path"])
    assert result.exit_code == 0
    assert result.stdout == f"{folder / 'Denver'}\n"


def test_get_team_as_written(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    make_league(LEAGUE, "[league]\nteam = 'Las Vegas'\n")
    write_config(athc_toml())
    result = runner.invoke(get, ["team"])
    assert result.exit_code == 0
    assert result.stdout == "Las Vegas\n"


@pytest.mark.parametrize("body", ["[league]\n", None], ids=["no value", "no file"])
@pytest.mark.parametrize(("key", "line"), NOT_SET_LINES.items())
def test_get_required_key_not_set(
    runner,
    make_league: MakeLeague,
    write_config: WriteConfig,
    key: str,
    line: str,
    body: str | None,
) -> None:
    folder = make_league(LEAGUE, body)
    write_config(athc_toml())
    result = runner.invoke(get, [key])
    assert result.exit_code == 2
    assert result.stderr == f"FAIL {folder / 'league.toml'}: {line}\n"
    assert result.stdout == ""


@pytest.mark.parametrize("body", ["[league]\n", None], ids=["no value", "no file"])
def test_get_ppp_path_not_set_is_a_warning(
    runner, make_league: MakeLeague, write_config: WriteConfig, body: str | None
) -> None:
    folder = make_league(LEAGUE, body)
    write_config(athc_toml())
    result = runner.invoke(get, ["ppp_path"])
    assert result.exit_code == 0
    assert result.stdout == ""
    assert result.stderr == f"WARN {folder / 'league.toml'}: {PPP_PATH_NOT_SET}\n"


@pytest.mark.parametrize("key", ["play_path", "team"])
def test_get_array_value_fails(
    runner, make_league: MakeLeague, write_config: WriteConfig, key: str
) -> None:
    folder = make_league(LEAGUE, f"[league]\n{key} = ['x']\n")
    write_config(athc_toml())
    result = runner.invoke(get, [key])
    assert result.exit_code == 2
    assert result.stderr == (
        f"FAIL {folder / 'league.toml'}: [league] {key}: "
        "Expected a string, got an array.\n"
    )


def test_get_reads_the_named_league(
    runner, make_league: MakeLeague, write_config: WriteConfig
) -> None:
    make_league(LEAGUE, "[league]\nteam = 'Denver'\n")
    make_league(OTHER_LEAGUE, "[league]\nteam = 'Miami'\n")
    write_config(athc_toml())
    result = runner.invoke(get, ["team", "--league", OTHER_LEAGUE])
    assert result.exit_code == 0
    assert result.stdout == "Miami\n"


def test_get_league_key_with_no_league_set(
    runner, make_league: MakeLeague, config_dir: Path
) -> None:
    make_league(LEAGUE, "[league]\nteam = 'Denver'\n")
    result = runner.invoke(get, ["team"])
    assert result.exit_code == 2
    assert result.stderr == no_league_selected(config_dir, LEAGUE)
    assert result.stdout == ""


# ── help screens, as an 80-column console shows them ──

# Click wraps help 78 wide in an 80-column console; CliRunner would force 80.
IN_80_COLUMNS: dict[str, Any] = {"prog_name": "athc", "terminal_width": 78}

CONFIG_HELP = """\
Usage: athc config [OPTIONS] COMMAND [ARGS]...

  Show or change athc settings (athc.toml, league.toml).

  Both live in your settings folder, %LOCALAPPDATA%\\athc.

Options:
  -h, --help  Show this message and exit.

Commands:
  edit    Open athc.toml or league.toml in its default app.
  get     Print a setting.
  path    Print the path of athc.toml or league.toml.
  reveal  Show athc.toml or league.toml in File Explorer.
  set     Set a value in athc.toml or league.toml.

  Examples:

    athc config set league PCFL
    athc config edit league.toml
"""

PATH_HELP = """\
Usage: athc config path [OPTIONS] [FILE]

  Print the path of athc.toml or league.toml.

  The file need not exist yet.

Positional arguments:
  FILE  athc.toml or league.toml (default: athc.toml, or league.toml when
        --league is given).

Options:
  --league NAME  League to use (default: the one set with athc config set
                 league).
  -h, --help     Show this message and exit.

  Examples:

    athc config path
    athc config path league.toml
"""

EDIT_HELP = """\
Usage: athc config edit [OPTIONS] [FILE]

  Open athc.toml or league.toml in its default app.

  A missing athc.toml is created empty first.

Positional arguments:
  FILE  athc.toml or league.toml (default: athc.toml, or league.toml when
        --league is given).

Options:
  --league NAME  League to use (default: the one set with athc config set
                 league).
  -h, --help     Show this message and exit.

  Examples:

    athc config edit
    athc config edit league.toml
    athc config edit --league PCFL
"""

REVEAL_HELP = """\
Usage: athc config reveal [OPTIONS] [FILE]

  Show athc.toml or league.toml in File Explorer.

  Selects the file, or opens its folder when the file is missing.

Positional arguments:
  FILE  athc.toml or league.toml (default: athc.toml, or league.toml when
        --league is given).

Options:
  --league NAME  League to use (default: the one set with athc config set
                 league).
  -h, --help     Show this message and exit.

  Examples:

    athc config reveal
    athc config reveal league.toml
"""

GET_HELP = """\
Usage: athc config get [OPTIONS] KEY

  Print a setting.

  league comes from athc.toml, the other keys from the league's league.toml.

Positional arguments:
  KEY  Setting to print: league, path, play_path, team or ppp_path.

Options:
  --league NAME  League to use (default: the one set with athc config set
                 league).
  -h, --help     Show this message and exit.

  Examples:

    athc config get league
    athc config get play_path
"""

HELP_SCREENS = [
    (("config",), CONFIG_HELP),
    (("config", "path"), PATH_HELP),
    (("config", "edit"), EDIT_HELP),
    (("config", "reveal"), REVEAL_HELP),
    (("config", "get"), GET_HELP),
]


@pytest.mark.parametrize(
    ("words", "screen"), HELP_SCREENS, ids=[" ".join(w) for w, _ in HELP_SCREENS]
)
def test_help_screen(runner, words: tuple[str, ...], screen: str) -> None:
    """The group lists get; --league NAME shows on every verb and FILE on path,
    edit and reveal."""
    result = runner.invoke(cli, [*words, "--help"], **IN_80_COLUMNS)
    assert result.exit_code == 0
    assert result.stdout == screen


# ── shipped config/release/: every loader reads it as installed ──

RELEASE = Path(__file__).resolve().parents[2] / "config" / "release"
# Every shipped league folder; each one runs the same tests.
SHIPPED_LEAGUES = sorted(p.name for p in (RELEASE / "leagues").iterdir() if p.is_dir())


@pytest.fixture
def release_config_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point config lookup at the shipped `config/release/` folder itself (overriding the
    autouse temp dir), as on a fresh install."""
    monkeypatch.setenv("ATHC_CONFIG_DIR", str(RELEASE))


def test_release_ships_leagues() -> None:
    assert SHIPPED_LEAGUES


@pytest.mark.usefixtures("release_config_dir")
def test_release_selected_league_loads() -> None:
    assert load_league_config().name in SHIPPED_LEAGUES


@pytest.mark.usefixtures("release_config_dir")
@pytest.mark.parametrize("name", SHIPPED_LEAGUES)
def test_release_league_loads(name: str) -> None:
    cfg = load_league_config(name)
    assert cfg.values["play_path"]
    assert cfg.values["path"]
    assert cfg.categories.offense and cfg.categories.defense


@pytest.mark.usefixtures("release_config_dir")
def test_release_autocontinue_section_loads() -> None:
    from athc.autocontinue import config as autocontinue_config

    autocontinue_config.load_config()


@pytest.mark.usefixtures("release_config_dir")
@pytest.mark.parametrize("name", SHIPPED_LEAGUES)
def test_release_gameplan_config_loads(name: str) -> None:
    from athc.gameplan import config as gameplan_config

    cfg = gameplan_config.load_config(name)
    assert cfg.rule_files and all(p.is_file() for p in cfg.rule_files)


@pytest.mark.usefixtures("release_config_dir")
@pytest.mark.parametrize("name", SHIPPED_LEAGUES)
def test_release_gameplan_rules_load_with_the_league_labels(name: str) -> None:
    from athc.gameplan import config as gameplan_config
    from athc.gameplan import load_rules

    cfg = gameplan_config.load_config(name)
    rules = load_rules(cfg.rule_files, labels=cfg.categories)
    assert "Run Middle" in rules.offense_categories


@pytest.mark.usefixtures("release_config_dir")
@pytest.mark.parametrize("name", SHIPPED_LEAGUES)
def test_release_profile_rules_load_with_the_league_labels(name: str) -> None:
    from athc.profile import config as profile_config
    from athc.profile import load_rules

    cfg = profile_config.load_config(name)
    assert cfg.categories.offense and cfg.categories.defense
    load_rules(cfg.rule_files, labels=cfg.categories)


@pytest.mark.usefixtures("release_config_dir")
@pytest.mark.parametrize("name", SHIPPED_LEAGUES)
def test_release_profile_config_loads(name: str) -> None:
    from athc.profile import config as profile_config

    cfg = profile_config.load_config(name)
    assert cfg.rule_files and all(p.is_file() for p in cfg.rule_files)


@pytest.mark.usefixtures("release_config_dir")
@pytest.mark.parametrize("name", SHIPPED_LEAGUES)
def test_release_convert_pdb_config_loads(name: str) -> None:
    from athc.pdbtoexcel import config as pdbtoexcel_config

    cfg = pdbtoexcel_config.load_config(name)
    assert cfg.deleted_plays_file == RELEASE / "athc.toml"
    assert [len(order) for order in cfg.category_order.values()] == [4, 9, 10]


@pytest.mark.usefixtures("release_config_dir")
def test_release_convert_pdb_defaults() -> None:
    from athc.pdbtoexcel import config as pdbtoexcel_config

    # The shipped [convert-pdb] section in athc.toml spells out every option; the
    # release counts sacks as pass attempts (the dev config leaves them out).
    cfg = pdbtoexcel_config.load_config()
    assert cfg.calculate_percentages is True
    assert cfg.include_category_worksheets is False
    assert cfg.exclude_sacks_from_pass_attempts is False


@pytest.mark.usefixtures("release_config_dir")
@pytest.mark.parametrize("name", SHIPPED_LEAGUES)
def test_release_scheduler_files_load(name: str) -> None:
    from athc.scheduler.config import load_scheduler_config, scheduler_rules_path

    assert scheduler_rules_path(name) == RELEASE / "leagues" / name / "scheduler.toml"
    load_scheduler_config(scheduler_rules_path(name))


def test_dev_mirrors_release_layout() -> None:
    def shipped(root: Path) -> set[Path]:
        patterns = (
            "athc.toml",
            "leagues/*/league.toml",
            "leagues/*/*.toml",
        )
        return {p.relative_to(root) for pat in patterns for p in root.glob(pat)}

    dev = RELEASE.parent / "dev"
    assert shipped(RELEASE)
    assert shipped(dev) == shipped(RELEASE)


# ── play_dir ──────────────────────────────────────────────────────────────────


def test_play_dir_is_the_folder(tmp_path: Path) -> None:
    assert play_dir(tmp_path) == tmp_path


def test_play_dir_missing(tmp_path: Path) -> None:
    with pytest.raises(ConfigFileError) as exc:
        play_dir(tmp_path / "gone")
    assert str(exc.value) == (
        f"{tmp_path / 'gone'}: {PATH_NOT_FOUND} Run 'athc config set play_path FOLDER'."
    )


def test_play_dir_is_a_file(tmp_path: Path) -> None:
    a_file = tmp_path / "plays.txt"
    a_file.write_text("x", encoding="utf-8")
    with pytest.raises(ConfigFileError) as exc:
        play_dir(a_file)
    assert str(exc.value) == (
        f"{a_file}: {DIRECTORY_INVALID} Run 'athc config set play_path FOLDER'."
    )
