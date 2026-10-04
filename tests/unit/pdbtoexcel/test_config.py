"""Unit tests for convert-pdb config."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from athc.config import ConfigFileError
from athc.pdbtoexcel import default_category_order, load_config
from athc.pdbtoexcel.pdb import PLAY_DATA

MakeLeague = Callable[..., Path]
WriteConfig = Callable[..., Path]

# Every workbook option flipped away from its default.
WORKBOOK_OPTIONS_INI = (
    "[convert-pdb]\ncalculate_total_stats = false\ncalculate_percentages = false\n"
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
    make_league("PNFL")  # league folder with no league.ini and no rules
    cfg = load_config("PNFL")
    assert cfg.play_path == ""
    assert cfg.playpool_rules is None  # no league file, no default next to athc.ini
    assert cfg.calculate_total_stats is True and cfg.calculate_percentages is True


def test_load_config_from_league_folder(make_league: MakeLeague) -> None:
    folder = make_league("PNFL", "[league]\nplay_path = D:\\plays\n")
    (folder / "rules" / "playpool.toml").write_text("", encoding="utf-8")
    cfg = load_config("PNFL")
    assert cfg.play_path == "D:\\plays"
    assert cfg.playpool_rules == folder / "rules" / "playpool.toml"


def test_load_config_cli_overrides_win(make_league: MakeLeague) -> None:
    folder = make_league("PNFL", "[league]\nplay_path = D:\\plays\n")
    (folder / "rules" / "playpool.toml").write_text("", encoding="utf-8")
    cfg = load_config("PNFL", play_path="E:\\other", playpool_rules=Path("E:\\r.toml"))
    assert cfg.play_path == "E:\\other"
    assert cfg.playpool_rules == Path("E:\\r.toml")


# ── playpool rules: --playpool-rules > league rules\playpool.toml > the default
# playpool.toml next to athc.ini > None ──


def _write_default_rules(config_dir: Path) -> Path:
    default = config_dir / "playpool.toml"
    default.write_text("", encoding="utf-8")
    return default


def test_default_playpool_rules_when_league_has_none(
    make_league: MakeLeague, config_dir: Path
) -> None:
    make_league("PNFL")  # no rules\playpool.toml
    default = _write_default_rules(config_dir)
    assert load_config("PNFL").playpool_rules == default


def test_league_playpool_rules_override_default(
    make_league: MakeLeague, config_dir: Path
) -> None:
    folder = make_league("PNFL")
    (folder / "rules" / "playpool.toml").write_text("", encoding="utf-8")
    _write_default_rules(config_dir)
    assert load_config("PNFL").playpool_rules == folder / "rules" / "playpool.toml"


def test_play_path_override_uses_default_rules(config_dir: Path) -> None:
    # --play-path alone reads no league; the default next to athc.ini still applies.
    default = _write_default_rules(config_dir)
    assert load_config(play_path="D:/plays").playpool_rules == default


def test_cli_playpool_rules_wins(make_league: MakeLeague, config_dir: Path) -> None:
    folder = make_league("PNFL")
    (folder / "rules" / "playpool.toml").write_text("", encoding="utf-8")
    _write_default_rules(config_dir)
    cfg = load_config("PNFL", playpool_rules=Path("E:\\r.toml"))
    assert cfg.playpool_rules == Path("E:\\r.toml")


def test_no_playpool_rules_anywhere_is_none(make_league: MakeLeague) -> None:
    make_league("PNFL")
    assert load_config("PNFL").playpool_rules is None


def test_load_config_reads_workbook_options(
    make_league: MakeLeague, write_config: WriteConfig
) -> None:
    make_league("PNFL")
    write_config(WORKBOOK_OPTIONS_INI)
    cfg = load_config("PNFL")
    assert cfg.calculate_total_stats is False
    assert cfg.calculate_percentages is False
    assert cfg.include_category_worksheets is True
    assert cfg.exclude_sacks_from_pass_attempts is False


def test_workbook_options_default_without_section(make_league: MakeLeague) -> None:
    make_league("PNFL")
    cfg = load_config("PNFL")
    assert cfg.calculate_total_stats is True
    assert cfg.calculate_percentages is True
    assert cfg.include_category_worksheets is False
    assert cfg.exclude_sacks_from_pass_attempts is True


def test_workbook_options_need_no_league(write_config: WriteConfig) -> None:
    # --play-path skips league resolution; the athc.ini section is read anyway.
    write_config(WORKBOOK_OPTIONS_INI)
    cfg = load_config(play_path="D:/plays")
    assert cfg.calculate_total_stats is False
    assert cfg.calculate_percentages is False
    assert cfg.include_category_worksheets is True
    assert cfg.exclude_sacks_from_pass_attempts is False


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
    write_config: WriteConfig, raw: str, expected: bool
) -> None:
    write_config(f"[convert-pdb]\ncalculate_total_stats = {raw}\n")
    assert load_config(play_path="D:/plays").calculate_total_stats is expected


def test_workbook_option_rejects_other_values(write_config: WriteConfig) -> None:
    write_config("[convert-pdb]\ncalculate_total_stats = maybe\n")
    with pytest.raises(ConfigFileError, match="calculate_total_stats"):
        load_config(play_path="D:/plays")
