"""Shared fixtures for fbpro98_lge tests.

`build_chunks` builds a valid .lge as a list of chunks; replace, drop or add
one to get the malformed and edge buffers no real file holds, then join them
with `build_lge`. `mask` is the tests' own copy of the game's mask.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from athc.fbpro98_lge.schema import (
    CHUNK_HEADER,
    CONFERENCE_BASE_SIZE,
    CONFERENCE_DIVISIONS_OFFSET,
    CONFERENCE_NAME_OFFSET,
    DIVISION_BASE_SIZE,
    DIVISION_NAME_OFFSET,
    DIVISION_TEAMS_OFFSET,
    GAME,
    GAME_PLAYED,
    ID_C03,
    ID_D03,
    ID_L03,
    ID_R03,
    ID_S03,
    ID_T03,
    LEAGUE_BASE_SIZE,
    LEAGUE_CONFERENCES_OFFSET,
    MASK_FACTOR,
    NICKNAME_OFFSET,
    ROSTER_CHUNK_SIZE,
    TEAM_CHUNK_SIZE,
    TEAM_NAME_OFFSET,
)


def build_chunk(tag: bytes, data: bytes) -> bytes:
    """One chunk: tag, data size, data."""
    return CHUNK_HEADER.pack(tag, len(data)) + data


def build_league_data(conferences: int) -> bytes:
    """L03 data: the conference count; everything else zero."""
    data = bytearray(LEAGUE_BASE_SIZE + conferences)
    data[LEAGUE_CONFERENCES_OFFSET] = conferences
    return bytes(data)


def _counted(
    base_size: int, count_offset: int, name_offset: int, count: int, name: bytes
) -> bytes:
    # Ids 1..count fill the tail, as in real files, so a name that fills its
    # field has text right after it.
    data = bytearray(base_size) + bytes(range(1, count + 1))
    data[count_offset] = count
    data[name_offset : name_offset + len(name)] = name
    return bytes(data)


def build_conference_data(divisions: int, name: bytes = b"") -> bytes:
    """C03 data: division count and name."""
    return _counted(
        CONFERENCE_BASE_SIZE,
        CONFERENCE_DIVISIONS_OFFSET,
        CONFERENCE_NAME_OFFSET,
        divisions,
        name,
    )


def build_division_data(teams: int, name: bytes = b"") -> bytes:
    """D03 data: team count and name."""
    return _counted(
        DIVISION_BASE_SIZE, DIVISION_TEAMS_OFFSET, DIVISION_NAME_OFFSET, teams, name
    )


def mask(team: int, data: bytes) -> bytes:
    """The game's XOR mask; applying it twice gives the data back."""
    return bytes(
        byte ^ ((MASK_FACTOR * team + index) & 0xFF) for index, byte in enumerate(data)
    )


def build_team_data(
    number: int, name: bytes = b"Denver", nickname: bytes = b"Broncos"
) -> bytes:
    """T03 data: the clear team number, then the masked fields."""
    fields = bytearray(TEAM_CHUNK_SIZE - 1)
    fields[TEAM_NAME_OFFSET : TEAM_NAME_OFFSET + len(name)] = name
    fields[NICKNAME_OFFSET : NICKNAME_OFFSET + len(nickname)] = nickname
    return bytes([number]) + mask(number, bytes(fields))


def build_roster_data(number: int) -> bytes:
    """R03 data: the clear team number (u16), then zeros; not read."""
    return number.to_bytes(2, "little") + bytes(ROSTER_CHUNK_SIZE - 2)


def build_game(
    home: int,
    home_score: int,
    away: int,
    away_score: int,
    status: int = GAME_PLAYED,
    overtime: int = 0,
) -> bytes:
    """One S03 game."""
    return GAME.pack(home, home_score, away, away_score, overtime, status)


def build_schedule_data(
    regular: Sequence[Sequence[bytes]] = (), playoffs: Sequence[Sequence[bytes]] = ()
) -> bytes:
    """S03 data: the header, then each week's game count and games."""
    data = bytearray([len(regular), len(playoffs), 0])
    for games in [*regular, *playoffs]:
        data.append(len(games))
        data += b"".join(games)
    return bytes(data)


def build_chunks(
    shape: Sequence[Sequence[int]] = ((1,),), grouped: bool = False
) -> list[bytes]:
    """A valid file's chunks. `shape` lists, per conference, each division's
    team count. Conferences, divisions and teams are numbered from 1 in file
    order and named after it: `C1`, `D1`, team `T1` nicknamed `N1`.
    `grouped` writes every C03, then every D03, T03 and R03, as some stock
    leagues do, instead of nesting them."""
    conferences: list[bytes] = []
    divisions: list[bytes] = []
    teams: list[bytes] = []
    rosters: list[bytes] = []
    nested: list[bytes] = []
    for division_counts in shape:
        name = b"C%d" % (len(conferences) + 1)
        conference = build_chunk(
            ID_C03, build_conference_data(len(division_counts), name)
        )
        conferences.append(conference)
        nested.append(conference)
        for team_count in division_counts:
            name = b"D%d" % (len(divisions) + 1)
            division = build_chunk(ID_D03, build_division_data(team_count, name))
            divisions.append(division)
            nested.append(division)
            for _ in range(team_count):
                number = len(teams) + 1
                data = build_team_data(number, b"T%d" % number, b"N%d" % number)
                team = build_chunk(ID_T03, data)
                roster = build_chunk(ID_R03, build_roster_data(number))
                teams.append(team)
                rosters.append(roster)
                nested += [team, roster]
    body = conferences + divisions + teams + rosters if grouped else nested
    league = build_chunk(ID_L03, build_league_data(len(shape)))
    return [league, *body, build_chunk(ID_S03, build_schedule_data())]


def build_lge(chunks: Sequence[bytes] | None = None) -> bytes:
    """A whole file from its chunks (default: one team)."""
    return b"".join(build_chunks() if chunks is None else chunks)


@pytest.fixture
def make_chunk():
    """Factory that builds one chunk (see build_chunk)."""
    return build_chunk


@pytest.fixture
def make_chunks():
    """Factory that builds a valid file's chunks (see build_chunks)."""
    return build_chunks


@pytest.fixture
def make_lge():
    """Factory that joins chunks into a file (see build_lge)."""
    return build_lge


@pytest.fixture
def make_league_data():
    """Factory for L03 data (see build_league_data)."""
    return build_league_data


@pytest.fixture
def make_conference_data():
    """Factory for C03 data (see build_conference_data)."""
    return build_conference_data


@pytest.fixture
def make_division_data():
    """Factory for D03 data (see build_division_data)."""
    return build_division_data


@pytest.fixture
def make_team_data():
    """Factory for T03 data (see build_team_data)."""
    return build_team_data


@pytest.fixture
def make_game():
    """Factory for one S03 game (see build_game)."""
    return build_game


@pytest.fixture
def make_schedule_data():
    """Factory for S03 data (see build_schedule_data)."""
    return build_schedule_data
