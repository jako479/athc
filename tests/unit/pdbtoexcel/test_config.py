"""Unit tests for convert-pdb config."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from athc.pdbtoexcel import default_category_order, load_config
from athc.pdbtoexcel.pdb import PLAY_DATA

WriteConfig = Callable[..., Path]


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


def test_load_config_defaults() -> None:
    cfg = load_config()  # autouse config_dir gives an empty dir
    assert cfg.play_path == ""
    assert cfg.playpool_rules is None
    assert cfg.calculate_total_stats is True and cfg.calculate_percentages is True


def test_load_config_from_ini(write_config: WriteConfig) -> None:
    write_config(
        "[convert-pdb]\nplay_path = D:\\plays\n"
        "calculate_percentages = false\nplaypool_rules = D:\\r.toml\n",
    )
    cfg = load_config()
    assert cfg.play_path == "D:\\plays"
    assert cfg.calculate_percentages is False
    assert cfg.playpool_rules == Path("D:\\r.toml")


def test_load_config_cli_overrides_win(write_config: WriteConfig) -> None:
    write_config("[convert-pdb]\nplay_path = D:\\plays\n")
    cfg = load_config(play_path="E:\\other", playpool_rules=Path("E:\\r.toml"))
    assert cfg.play_path == "E:\\other"
    assert cfg.playpool_rules == Path("E:\\r.toml")
