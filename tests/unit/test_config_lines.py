"""`not_set_line`: the one sentence pair for a setting that is not set."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from athc.config import not_set_line, resolve_league
from athc.errors import LeagueError


@pytest.mark.parametrize(
    "key,line",
    [
        ("league", "League is not set. Run 'athc config set league NAME'."),
        ("path", "League files folder is not set. Run 'athc config set path FOLDER'."),
        (
            "play_path",
            "Play pool folder is not set. Run 'athc config set play_path FOLDER'.",
        ),
        ("team", "Team is not set. Run 'athc config set team NAME'."),
    ],
)
def test_each_setting_names_itself_and_its_command(key: str, line: str) -> None:
    assert not_set_line(key) == line


def test_a_way_out_ends_the_second_sentence() -> None:
    assert not_set_line("team", "--team or a .prf file") == (
        "Team is not set. Run 'athc config set team NAME' or pass --team or a .prf file."
    )


def test_league_line_keeps_the_available_tail(
    make_league: Callable[..., Path], write_config: Callable[..., Path]
) -> None:
    make_league("PNFL")
    write_config("[athc]\n")
    with pytest.raises(LeagueError) as caught:
        resolve_league(None)
    assert str(caught.value) == (
        "League is not set. Run 'athc config set league NAME' or pass --league. "
        "Available: PNFL."
    )
