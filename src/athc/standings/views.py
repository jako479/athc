"""The standings views as lines of text: the game's standings screen, and
ESPN's League, Conference and Division tabs."""

from __future__ import annotations

from collections.abc import Container, Sequence
from typing import Literal, get_args

from athc.fbpro98_lge import Conference, Division, LgeFile, Team
from athc.fbpro98_standings import Standings
from athc.standings.records import Row, Split, rows_of

View = Literal["game", "league", "conference", "division"]
VIEWS: tuple[View, ...] = get_args(View)

# What the game's standings screen shows for a conference the file leaves
# unnamed, as PNFL's does.
_UNNAMED = ("AFC", "NFC")
_GAME_COLUMNS = ("W", "L", "T", "PF", "PA")
_ESPN_COLUMNS = (
    "W",
    "L",
    "T",
    "PCT",
    "HOME",
    "AWAY",
    "DIV",
    "CONF",
    "PF",
    "PA",
    "DIFF",
    "STRK",
)
_SEP = "  "  # between columns
_GAP = "    "  # between the game view's conference columns

# One line of a view: its cells, or a plain string (a title or a blank line).
_Line = str | list[str]


def render(view: View, lge: LgeFile, standings: Standings, league: str) -> list[str]:
    """The view's lines; `league` is the league's name, the league view's
    title."""
    rows = rows_of(lge)
    names = [
        conference.name or _UNNAMED[index]
        for index, conference in enumerate(lge.conferences)
    ]
    match view:
        case "game":
            return _game(lge, standings, rows, names)
        case "league":
            return _league(standings, rows, league)
        case "conference":
            return _conference(lge, standings, rows, names)
        case "division":
            return _division(lge, standings, rows, names)


def percentage(split: Split) -> str:
    """(W + T / 2) / games to three decimals, no leading zero below one:
    `.800`, `1.000`; `.000` before any game. A half rounds up, as ESPN
    prints it: 13-3 is `.813`."""
    games = split.wins + split.losses + split.ties
    if not games:
        return ".000"
    # Whole numbers, because a float's format rounds 13-3's exact .8125 down.
    thousandths = (1000 * (2 * split.wins + split.ties) + games) // (2 * games)
    return "1.000" if thousandths == 1000 else f".{thousandths:03d}"


def record(split: Split) -> str:
    """`2-1`, or `0-1-1` with ties."""
    text = f"{split.wins}-{split.losses}"
    return f"{text}-{split.ties}" if split.ties else text


def difference(points_for: int, points_against: int) -> str:
    """Points for minus points against, signed: `+23`, `-8`, `0`."""
    value = points_for - points_against
    return f"{value:+d}" if value else "0"


def _game(
    lge: LgeFile, standings: Standings, rows: dict[int, Row], names: list[str]
) -> list[str]:
    columns = [
        _game_column(name, conference, standings, rows)
        for name, conference in zip(names, lge.conferences, strict=True)
    ]
    return _side_by_side(columns)


def _game_column(
    name: str, conference: Conference, standings: Standings, rows: dict[int, Row]
) -> list[list[str]]:
    """One conference's divisions, a block of lines each, aligned together."""
    lines: list[_Line] = []
    sizes: list[int] = []
    for division in conference.divisions:
        teams = standings.division(division)
        lines.append([_header(name, division), *_GAME_COLUMNS])
        for team in teams:
            row = rows[id(team)]
            overall = row.overall
            lines.append(
                [
                    team.name,
                    str(overall.wins),
                    str(overall.losses),
                    str(overall.ties),
                    str(row.points_for),
                    str(row.points_against),
                ]
            )
        sizes.append(len(teams) + 1)
    aligned = _aligned(lines, left={0})
    blocks: list[list[str]] = []
    start = 0
    for size in sizes:
        blocks.append(aligned[start : start + size])
        start += size
    return blocks


def _side_by_side(columns: list[list[list[str]]]) -> list[str]:
    """Each conference's blocks down its own column, block N of every column
    starting on the same line, a blank line between."""
    widths = [
        max(len(line) for block in column for line in block) for column in columns
    ]
    lines: list[str] = []
    for index in range(max(len(column) for column in columns)):
        if index:
            lines.append("")
        blocks = [column[index] if index < len(column) else [] for column in columns]
        for number in range(max(len(block) for block in blocks)):
            cells = [
                (block[number] if number < len(block) else "").ljust(width)
                for block, width in zip(blocks, widths, strict=True)
            ]
            lines.append(_GAP.join(cells).rstrip())
    return lines


def _league(standings: Standings, rows: dict[int, Row], league: str) -> list[str]:
    lines: list[_Line] = [league, ["", "", *_ESPN_COLUMNS]]
    lines += _numbered(standings.league(), rows)
    return _aligned(lines, left={1})


def _conference(
    lge: LgeFile, standings: Standings, rows: dict[int, Row], names: list[str]
) -> list[str]:
    lines: list[_Line] = []
    for index, (name, conference) in enumerate(
        zip(names, lge.conferences, strict=True)
    ):
        if index:
            lines.append("")
        lines += [name, ["", "", *_ESPN_COLUMNS]]
        lines += _numbered(standings.conference(conference), rows)
    return _aligned(lines, left={1})


def _division(
    lge: LgeFile, standings: Standings, rows: dict[int, Row], names: list[str]
) -> list[str]:
    lines: list[_Line] = []
    for index, (name, conference) in enumerate(
        zip(names, lge.conferences, strict=True)
    ):
        if index:
            lines.append("")
        lines.append(name)
        for division in conference.divisions:
            lines.append([_header(name, division), *_ESPN_COLUMNS])
            lines += [
                [team.official_name, *_espn_cells(rows[id(team)])]
                for team in standings.division(division)
            ]
    return _aligned(lines, left={0})


def _numbered(teams: Sequence[Team], rows: dict[int, Row]) -> list[_Line]:
    return [
        [str(number), team.official_name, *_espn_cells(rows[id(team)])]
        for number, team in enumerate(teams, 1)
    ]


def _espn_cells(row: Row) -> list[str]:
    overall = row.overall
    return [
        str(overall.wins),
        str(overall.losses),
        str(overall.ties),
        percentage(overall),
        record(row.home),
        record(row.away),
        record(row.division),
        record(row.conference),
        str(row.points_for),
        str(row.points_against),
        difference(row.points_for, row.points_against),
        row.streak,
    ]


def _header(conference: str, division: Division) -> str:
    """`AFC EAST`: the conference and division names in capitals."""
    return " ".join(part for part in (conference, division.name) if part).upper()


def _aligned(lines: Sequence[_Line], left: Container[int]) -> list[str]:
    """Plain strings as they are; cell lines in columns as wide as their
    widest entry across every cell line, the columns in `left` left-aligned,
    the rest right-aligned."""
    tables = [line for line in lines if isinstance(line, list)]
    widths = [
        max(len(cells[column]) for cells in tables) for column in range(len(tables[0]))
    ]
    out: list[str] = []
    for line in lines:
        if isinstance(line, str):
            out.append(line)
            continue
        cells = [
            cell.ljust(width) if column in left else cell.rjust(width)
            for column, (cell, width) in enumerate(zip(line, widths, strict=True))
        ]
        out.append(_SEP.join(cells).rstrip())
    return out
