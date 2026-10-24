"""`parse_play_list`: a play list's lines with their file line numbers; a blank
line is an empty entry, and comment lines and the blanks after the last play
are dropped."""

from __future__ import annotations

from athc.cli.gameplan._common import parse_play_list
from athc.gameplan.writer import PlayLine


def test_parse_play_list_keeps_the_file_line_numbers() -> None:
    text = "\r\n:: comment\r\nPlay A\r\n\r\nPlay B :: note\r\n"
    assert parse_play_list(text) == [
        PlayLine(1, ""),
        PlayLine(3, "Play A"),
        PlayLine(4, ""),
        PlayLine(5, "Play B"),
    ]


def test_parse_play_list_keeps_blank_lines_as_empty_entries() -> None:
    text = "Play A\n   \n\t\nPlay B\n"
    assert parse_play_list(text) == [
        PlayLine(1, "Play A"),
        PlayLine(2, ""),
        PlayLine(3, ""),
        PlayLine(4, "Play B"),
    ]


def test_parse_play_list_drops_blank_lines_after_the_last_play() -> None:
    assert parse_play_list("Play A\n\n:: end\n  \n\n") == [PlayLine(1, "Play A")]


def test_parse_play_list_of_only_blank_lines_is_empty() -> None:
    assert parse_play_list("\n  \n:: only a comment\n") == []
