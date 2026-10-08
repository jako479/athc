"""Unit tests for convert-pdb config."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from athc.config import ConfigFileError, LeagueError
from athc.pdbtoexcel import default_category_order, load_config
from athc.pdbtoexcel.pdb import PLAY_DATA
from tests.conftest import LEAGUE

MakeLeague = Callable[..., Path]
WriteConfig = Callable[..., Path]

# Every workbook option flipped away from its default.
WORKBOOK_OPTIONS_INI = (
    "[convert-pdb]\ncalculate_percentages = false\n"
    "include_category_worksheets = true\nexclude_sacks_from_pass_attempts = false\n"
)


def test_default_category_order_uses_game_names() -> None:
    order = default_category_order()
    assert "Run Middle" in order[PLAY_DATA.PLAY_TYPE.RUN]
    assert "Pass Short Left" in order[PLAY_DATA.PLAY_TYPE.PASS]
    assert "Pass Long" in order[PLAY_DATA.PLAY_TYPE.DEFENSE]
    assert "User Specific" not in order[PLAY_DATA.PLAY_TYPE.RUN]
    # run and pass don't overlap
    assert set(order[PLAY_DATA.PLAY_TYPE.RUN]).isdisjoint(
        order[PLAY_DATA.PLAY_TYPE.PASS]
    )


def test_load_config_defaults(make_league: MakeLeague) -> None:
    make_league()  # league folder with no league.ini and no rules
    cfg = load_config(LEAGUE)
    assert cfg.play_path == ""
    assert cfg.playpool_rules is None
    assert cfg.calculate_percentages is True


def test_load_config_from_league_folder(make_league: MakeLeague) -> None:
    folder = make_league(LEAGUE, "[league]\nplay_path = D:\\plays\n")
    (folder / "playpool.toml").write_text("", encoding="utf-8")
    cfg = load_config(LEAGUE)
    assert cfg.play_path == "D:\\plays"
    assert cfg.playpool_rules == folder / "playpool.toml"


def test_load_config_needs_a_league() -> None:
    with pytest.raises(LeagueError, match="no league selected"):
        load_config()


# ── playpool rules: league playpool.toml > None ─────────────────────────


def test_playpool_toml_next_to_athc_ini_is_ignored(
    make_league: MakeLeague, config_dir: Path
) -> None:
    make_league()  # no playpool.toml
    (config_dir / "playpool.toml").write_text("", encoding="utf-8")
    assert load_config(LEAGUE).playpool_rules is None


def test_no_playpool_rules_anywhere_is_none(make_league: MakeLeague) -> None:
    make_league()
    assert load_config(LEAGUE).playpool_rules is None


# ── workbook options from [convert-pdb] in athc.ini ───────────────────────────


def test_load_config_reads_workbook_options(
    make_league: MakeLeague, write_config: WriteConfig
) -> None:
    make_league()
    write_config(WORKBOOK_OPTIONS_INI)
    cfg = load_config(LEAGUE)
    assert cfg.calculate_percentages is False
    assert cfg.include_category_worksheets is True
    assert cfg.exclude_sacks_from_pass_attempts is False


def test_workbook_options_default_without_section(make_league: MakeLeague) -> None:
    make_league()
    cfg = load_config(LEAGUE)
    assert cfg.calculate_percentages is True
    assert cfg.include_category_worksheets is False
    assert cfg.exclude_sacks_from_pass_attempts is True


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1", True),
        ("yes", True),
        ("TRUE", True),
        ("On", True),
        ("0", False),
        ("no", False),
        ("False", False),
        ("OFF", False),
    ],
)
def test_workbook_option_accepts_configparser_booleans(
    make_league: MakeLeague, write_config: WriteConfig, raw: str, expected: bool
) -> None:
    make_league()
    write_config(f"[convert-pdb]\ncalculate_percentages = {raw}\n")
    assert load_config(LEAGUE).calculate_percentages is expected


def test_workbook_option_rejects_other_values(
    make_league: MakeLeague, write_config: WriteConfig
) -> None:
    make_league()
    write_config("[convert-pdb]\ncalculate_percentages = maybe\n")
    with pytest.raises(ConfigFileError, match="calculate_percentages"):
        load_config(LEAGUE)


def test_calculate_total_stats_is_no_longer_read(
    make_league: MakeLeague, write_config: WriteConfig
) -> None:
    # Totals are always on; a leftover key is ignored, even with a bad value.
    make_league()
    write_config("[convert-pdb]\ncalculate_total_stats = maybe\n")
    assert not hasattr(load_config(LEAGUE), "calculate_total_stats")
