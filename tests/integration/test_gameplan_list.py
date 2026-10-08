"""Integration tests for `athc gameplan list-normals` / `list-specials`."""

from __future__ import annotations

import logging
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from athc.cli.gameplan.list_normals import list_normals
from athc.cli.gameplan.list_specials import list_specials
from athc.fbpro98_gameplan import ProfileType, write_gameplan
from tests.conftest import LEAGUE, OTHER_LEAGUE, league_toml
from tests.integration.conftest import (
    EXPECTED,
    GP_DEFENSE,
    GP_OFFENSE,
    build_gameplan,
    offense_normal,
)

MakeLeague = Callable[..., Path]
WriteConfig = Callable[..., Path]


@pytest.fixture(autouse=True)
def league(make_league: MakeLeague, write_config: WriteConfig) -> Path:
    """The selected league, carrying the PNFL category labels; list-normals
    needs nothing else from it."""
    write_config(f"[athc]\nleague = {LEAGUE}\n")
    return make_league(LEAGUE, league_toml())


def _expected(name: str) -> list[str]:
    return (EXPECTED / name).read_text(encoding="utf-8").splitlines()


# ── list-normals ──────────────────────────────────────────────────────────────


def test_normals_requires_path(runner) -> None:
    assert runner.invoke(list_normals, []).exit_code == 2


def test_normals_rejects_invalid_sort(runner) -> None:
    assert (
        runner.invoke(list_normals, [str(GP_OFFENSE), "--sort", "bogus"]).exit_code == 2
    )


def test_normals_help_uses_lowercase_names(runner) -> None:
    result = runner.invoke(list_normals, ["--help"])
    assert result.exit_code == 0
    assert "] gameplan [output_file]" in " ".join(result.output.split())  # wraps
    assert "GAMEPLAN" not in result.output and "OUTPUT_PATH" not in result.output


@pytest.mark.parametrize("option", ["--force", "--output"])
def test_normals_removed_options_rejected(runner, tmp_path: Path, option: str) -> None:
    out = tmp_path / "plays.txt"
    result = runner.invoke(list_normals, [str(GP_OFFENSE), option, str(out)])
    assert result.exit_code == 2
    assert "No such option" in result.output


def test_normals_default_writes_next_to_gameplan(runner, tmp_path: Path) -> None:
    gp = tmp_path / "OFF.pln"
    shutil.copy2(GP_OFFENSE, gp)
    result = runner.invoke(list_normals, [str(gp)])
    assert result.exit_code == 0
    out = tmp_path / "OFF.normals.txt"
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith(":: ") and str(gp.resolve()) in lines[0]
    assert lines[1:] == _expected("offense_normals_slot.txt")


def test_normals_creates_missing_folder(runner, tmp_path: Path) -> None:
    out = tmp_path / "lists" / "plays.txt"
    result = runner.invoke(list_normals, [str(GP_OFFENSE), str(out)])
    assert result.exit_code == 0
    assert out.read_text(encoding="utf-8").splitlines()[1:] == _expected(
        "offense_normals_slot.txt"
    )


def test_normals_creates_missing_folders_in_full(runner, tmp_path: Path) -> None:
    out = tmp_path / "lists" / "2049" / "plays.txt"
    result = runner.invoke(list_normals, [str(GP_OFFENSE), str(out)])
    assert result.exit_code == 0
    assert out.is_file()


def test_normals_output_folder_is_a_file_exit_1(runner, tmp_path: Path, caplog) -> None:
    (tmp_path / "lists").write_text("x", encoding="utf-8")
    out = tmp_path / "lists" / "plays.txt"
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(list_normals, [str(GP_OFFENSE), str(out)])
    assert result.exit_code == 1
    assert out.parent.name in caplog.text


def test_normals_overwrites_existing_file(runner, tmp_path: Path) -> None:
    out = tmp_path / "plays.txt"
    out.write_text("existing\n", encoding="utf-8")
    result = runner.invoke(list_normals, [str(GP_OFFENSE), str(out)])
    assert result.exit_code == 0
    assert out.read_text(encoding="utf-8").splitlines()[1:] == _expected(
        "offense_normals_slot.txt"
    )


def test_normals_dash_offense_slot(runner) -> None:
    result = runner.invoke(list_normals, [str(GP_OFFENSE), "-"])
    assert result.exit_code == 0
    assert result.output.splitlines() == _expected("offense_normals_slot.txt")


def test_normals_dash_defense_slot(runner) -> None:
    result = runner.invoke(list_normals, [str(GP_DEFENSE), "-"])
    assert result.exit_code == 0
    assert result.output.splitlines() == _expected("defense_normals_slot.txt")


def test_normals_dash_sort_name(runner) -> None:
    result = runner.invoke(list_normals, [str(GP_OFFENSE), "-", "--sort", "name"])
    assert result.exit_code == 0
    assert result.output.splitlines() == _expected("offense_normals_name.txt")


def test_normals_dash_sort_category_offense(runner) -> None:
    result = runner.invoke(list_normals, [str(GP_OFFENSE), "-", "--sort", "category"])
    assert result.exit_code == 0
    assert result.output.splitlines() == _expected("offense_normals_category.txt")


def test_normals_dash_sort_category_defense(runner) -> None:
    result = runner.invoke(list_normals, [str(GP_DEFENSE), "-", "--sort", "category"])
    assert result.exit_code == 0
    assert result.output.splitlines() == _expected("defense_normals_category.txt")


def test_normals_sort_category_game_name_without_label(runner, tmp_path: Path) -> None:
    """A category the league has no label for is headed by its game name; Pass
    Long Left/Middle sit before PLR, Razzle Dazzle Run before PRD, User Specific
    last; an empty category gets no header; slot order holds within one."""
    plays = [
        offense_normal("USR1", 0xFF),  # User Specific
        offense_normal("PRD1", 0x0F),
        offense_normal("RRD1", 0x0D),
        offense_normal("PLR1", 0x23),
        offense_normal("PLM1", 0x2B),
        offense_normal("PLL1", 0x27),
        offense_normal("PLL2", 0xA7),  # bits 7-6 vary within a category
    ]
    gp = build_gameplan(ProfileType.OFFENSE, normals=dict(enumerate(plays)))
    path = tmp_path / "OFF.pln"
    write_gameplan(gp, path)
    result = runner.invoke(list_normals, [str(path), "-", "--sort", "category"])
    assert result.exit_code == 0
    assert result.output.splitlines() == [
        ":: Pass Long Left", "PLL1", "PLL2",
        ":: Pass Long Middle", "PLM1",
        ":: PLR", "PLR1",
        ":: Razzle Dazzle Run", "RRD1",
        ":: PRD", "PRD1",
        ":: User Specific", "USR1",
    ]  # fmt: skip


def test_normals_sort_category_without_league_labels(runner, league: Path) -> None:
    (league / "league.toml").write_text(league_toml(labels=False), encoding="utf-8")
    result = runner.invoke(list_normals, [str(GP_OFFENSE), "-", "--sort", "category"])
    assert result.exit_code == 0
    lines = result.output.splitlines()
    assert lines[0] == ":: Run Left"
    assert ":: Goal Line Pass" in lines
    assert ":: RL" not in lines


def test_normals_league_option_picks_league(runner, make_league: MakeLeague) -> None:
    make_league(OTHER_LEAGUE, league_toml(labels=False))
    result = runner.invoke(
        list_normals,
        [str(GP_OFFENSE), "-", "--sort", "category", "--league", OTHER_LEAGUE],
    )
    assert result.exit_code == 0
    assert result.output.splitlines()[0] == ":: Run Left"


def test_normals_no_league_exit_1(runner, write_config: WriteConfig, caplog) -> None:
    write_config("[athc]\n")
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(list_normals, [str(GP_OFFENSE), "-"])
    assert result.exit_code == 1
    assert "no league selected" in caplog.text


def test_normals_bad_league_toml_exit_1(runner, league: Path, caplog) -> None:
    (league / "league.toml").write_text("[league\n", encoding="utf-8")
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(list_normals, [str(GP_OFFENSE), "-"])
    assert result.exit_code == 1
    assert "league.toml" in caplog.text


def test_normals_file_sort_category(runner, tmp_path: Path) -> None:
    out = tmp_path / "plays.txt"
    result = runner.invoke(
        list_normals, [str(GP_OFFENSE), str(out), "--sort", "category"]
    )
    assert result.exit_code == 0
    assert out.read_text(encoding="utf-8").splitlines()[1:] == _expected(
        "offense_normals_category.txt"
    )


def test_normals_file_sort_category_counts_plays_not_headers(
    runner, tmp_path: Path
) -> None:
    out = tmp_path / "plays.txt"
    result = runner.invoke(
        list_normals, [str(GP_OFFENSE), str(out), "--sort", "category"]
    )
    assert result.exit_code == 0
    assert f"Wrote 64 normal play(s) to {out}" in result.output


def test_normals_file_writes_header_and_plays(runner, tmp_path: Path) -> None:
    out = tmp_path / "plays.txt"
    result = runner.invoke(list_normals, [str(GP_OFFENSE), str(out)])
    assert result.exit_code == 0
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith(":: ") and str(GP_OFFENSE.resolve()) in lines[0]
    assert lines[1:] == _expected("offense_normals_slot.txt")


def test_normals_file_sort_name(runner, tmp_path: Path) -> None:
    out = tmp_path / "plays.txt"
    result = runner.invoke(list_normals, [str(GP_OFFENSE), str(out), "--sort", "name"])
    assert result.exit_code == 0
    assert out.read_text(encoding="utf-8").splitlines()[1:] == _expected(
        "offense_normals_name.txt"
    )


def test_normals_file_logs_count(runner, tmp_path: Path) -> None:
    out = tmp_path / "plays.txt"
    result = runner.invoke(list_normals, [str(GP_OFFENSE), str(out)])
    assert result.exit_code == 0
    assert f"Wrote 64 normal play(s) to {out}" in result.output


def test_normals_missing_gameplan(runner, tmp_path: Path, caplog) -> None:
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(list_normals, [str(tmp_path / "nope.pln")])
    assert result.exit_code == 1
    assert any(r.levelname == "ERROR" for r in caplog.records)


def test_normals_malformed_file_mode_no_output(runner, tmp_path: Path, caplog) -> None:
    bad = tmp_path / "bad.pln"
    bad.write_bytes(b"\x00\x01\x02")
    out = tmp_path / "plays.txt"
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(list_normals, [str(bad), str(out)])
    assert result.exit_code == 1
    assert not out.exists()


# ── list-specials ─────────────────────────────────────────────────────────────


def test_specials_requires_path(runner) -> None:
    assert runner.invoke(list_specials, []).exit_code == 2


def test_specials_help_uses_lowercase_names(runner) -> None:
    result = runner.invoke(list_specials, ["--help"])
    assert result.exit_code == 0
    assert "] gameplan [output_file]" in result.output
    assert "GAMEPLAN" not in result.output and "OUTPUT_PATH" not in result.output


@pytest.mark.parametrize("option", ["--force", "--output"])
def test_specials_removed_options_rejected(runner, tmp_path: Path, option: str) -> None:
    out = tmp_path / "spec.txt"
    result = runner.invoke(list_specials, [str(GP_OFFENSE), option, str(out)])
    assert result.exit_code == 2
    assert "No such option" in result.output


def test_specials_default_writes_next_to_gameplan(runner, tmp_path: Path) -> None:
    gp = tmp_path / "OFF.pln"
    shutil.copy2(GP_OFFENSE, gp)
    result = runner.invoke(list_specials, [str(gp)])
    assert result.exit_code == 0
    out = tmp_path / "OFF.specials.txt"
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith(":: ") and str(gp.resolve()) in lines[0]
    assert lines[1:] == _expected("offense_specials.txt")


def test_specials_creates_missing_folder(runner, tmp_path: Path) -> None:
    out = tmp_path / "lists" / "spec.txt"
    result = runner.invoke(list_specials, [str(GP_OFFENSE), str(out)])
    assert result.exit_code == 0
    assert out.is_file()


def test_specials_creates_missing_folders_in_full(runner, tmp_path: Path) -> None:
    out = tmp_path / "lists" / "2049" / "spec.txt"
    result = runner.invoke(list_specials, [str(GP_OFFENSE), str(out)])
    assert result.exit_code == 0
    assert out.is_file()


def test_specials_overwrites_existing_file(runner, tmp_path: Path) -> None:
    out = tmp_path / "spec.txt"
    out.write_text("existing\n", encoding="utf-8")
    result = runner.invoke(list_specials, [str(GP_OFFENSE), str(out)])
    assert result.exit_code == 0
    assert out.read_text(encoding="utf-8").splitlines()[1:] == _expected(
        "offense_specials.txt"
    )


def test_specials_dash_offense(runner) -> None:
    result = runner.invoke(list_specials, [str(GP_OFFENSE), "-"])
    assert result.exit_code == 0
    assert result.output.splitlines() == _expected("offense_specials.txt")


def test_specials_dash_defense(runner) -> None:
    result = runner.invoke(list_specials, [str(GP_DEFENSE), "-"])
    assert result.exit_code == 0
    assert result.output.splitlines() == _expected("defense_specials.txt")


def test_specials_file_writes_header_and_plays(runner, tmp_path: Path) -> None:
    out = tmp_path / "spec.txt"
    result = runner.invoke(list_specials, [str(GP_OFFENSE), str(out)])
    assert result.exit_code == 0
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith(":: ") and str(GP_OFFENSE.resolve()) in lines[0]
    assert lines[1:] == _expected("offense_specials.txt")


def test_specials_file_logs_count(runner, tmp_path: Path) -> None:
    out = tmp_path / "spec.txt"
    result = runner.invoke(list_specials, [str(GP_OFFENSE), str(out)])
    assert result.exit_code == 0
    assert f"Wrote 6 special play(s) to {out}" in result.output


def test_specials_malformed_file_mode_no_output(runner, tmp_path: Path, caplog) -> None:
    bad = tmp_path / "bad.pln"
    bad.write_bytes(b"\x00\x01\x02")
    out = tmp_path / "spec.txt"
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(list_specials, [str(bad), str(out)])
    assert result.exit_code == 1
    assert not out.exists()
