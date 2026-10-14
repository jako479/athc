"""Tests for athc.fbpro98_lge.reader.

Real fixtures in data/ (8, 10, 12, 18, 28 and 30 teams) cover whole-file
parsing; built bytes cover the limits and edge cases no real file holds.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from athc.fbpro98_lge import (
    Conference,
    Division,
    InvalidLgeError,
    LgeFile,
    Record,
    Team,
    parse_lge,
    ranked,
    read_lge,
)
from athc.fbpro98_lge.schema import (
    CHUNK_HEADER,
    DIVISION_BASE_SIZE,
    ID_C03,
    ID_D03,
    ID_L03,
    ID_S03,
    ID_T03,
    NAME_SIZE,
    TEAM_TEXT_SIZE,
)

FIXTURE_DIR = Path(__file__).resolve().parent / "data"
LEAGUE = "PNFL"
# The PNFL's 2047 season: before week 1, after week 16 (the regular season's
# last), after the Super Bowl.
BEFORE_WEEK1 = "PNFL-before-week1.lge"
WEEK16 = "PNFL-after-week16.lge"
SUPER_BOWL = "PNFL-after-super-bowl.lge"
NO_GAMES = Record(0, 0, 0, 0, 0)

# Chunk positions in the default one-team built file.
L03, C03, D03, T03, R03, S03 = range(6)


def _parse_fixture(filename: str) -> LgeFile:
    # Parsed from bytes: the stock fixtures keep the game's upper-case names.
    return parse_lge((FIXTURE_DIR / filename).read_bytes())


def _shape(lge: LgeFile) -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(len(division.teams) for division in conference.divisions)
        for conference in lge.conferences
    )


def _teams(lge: LgeFile) -> list[Team]:
    return [
        team
        for conference in lge.conferences
        for division in conference.divisions
        for team in division.teams
    ]


def _only_team(lge: LgeFile) -> Team:
    return lge.conferences[0].divisions[0].teams[0]


def _names(team: Team) -> tuple[str, str]:
    return team.name, team.nickname


# --- real files ---

# PNFL.lge's tree: conference name, then each division's name and teams in
# file order (standings are checked separately below).
PNFL_TREE = (
    (
        "",
        (
            (
                "East",
                (
                    Team("Jacksonville", "Jaguars", Record(5, 1, 0, 164, 112)),
                    Team("San Diego", "Chargers", Record(4, 2, 0, 145, 105)),
                    Team("New England", "Patriots", Record(2, 4, 0, 114, 155)),
                    Team("Miami", "Dolphins", Record(2, 4, 0, 144, 154)),
                ),
            ),
            (
                "West",
                (
                    Team("Denver", "Broncos", Record(2, 4, 0, 131, 157)),
                    Team("Las Vegas", "Raiders", Record(3, 3, 0, 132, 129)),
                    Team("Cincinnati", "Bengals", Record(2, 4, 0, 138, 149)),
                    Team("Baltimore", "Ravens", Record(4, 2, 0, 166, 137)),
                    Team("Pittsburgh", "Steelers", Record(3, 3, 0, 137, 119)),
                ),
            ),
        ),
    ),
    (
        "",
        (
            (
                "East",
                (
                    Team("Atlanta", "Falcons", Record(4, 2, 0, 130, 122)),
                    Team("New York", "Giants", Record(1, 5, 0, 121, 164)),
                    Team("Philadelphia", "Eagles", Record(3, 3, 0, 138, 149)),
                    Team("Washington", "Redskins", Record(2, 4, 0, 92, 129)),
                ),
            ),
            (
                "West",
                (
                    Team("Green Bay", "Packers", Record(2, 4, 0, 113, 137)),
                    Team("Chicago", "Cardinals", Record(3, 3, 0, 179, 135)),
                    Team("Detroit", "Lions", Record(2, 4, 0, 90, 129)),
                    Team("Minnesota", "Vikings", Record(6, 0, 0, 156, 103)),
                    Team("San Francisco", "49ers", Record(4, 2, 0, 159, 164)),
                ),
            ),
        ),
    ),
)


def _tree(lge: LgeFile):
    return tuple(
        (
            conference.name,
            tuple((division.name, division.teams) for division in conference.divisions),
        )
        for conference in lge.conferences
    )


def test_custom_league():
    # Empty conference names and several team names carry leftover text after
    # the NUL. Records are from six played weeks, as on the game's Week Seven
    # standings screen. The games themselves are checked below.
    assert _tree(read_lge(LEAGUE, FIXTURE_DIR)) == PNFL_TREE


def test_teams_are_in_file_order():
    lge = read_lge(LEAGUE, FIXTURE_DIR)
    assert lge.teams == tuple(_teams(lge))
    assert lge.teams[0].name == "Jacksonville"
    assert lge.teams[17].name == "San Francisco"


@pytest.mark.parametrize(
    ("filename", "shape"),
    [
        ("08_TEAMS.lge", ((4, 4),)),
        ("10_TEAMS.LGE", ((3, 4, 3),)),
        ("12_TEAMS.LGE", ((4, 4, 4),)),
        ("PNFL.lge", ((4, 5), (4, 5))),
        ("NFLPA94.lge", ((5, 4, 5), (5, 5, 4))),
        ("NFLPI97R.LGE", ((5, 5, 5), (5, 5, 5))),
        # Grouped by chunk kind.
        ("NFLPA93E.LGE", ((5, 4, 5), (5, 5, 4))),
        ("_default.lge", ((5, 5, 5), (5, 5, 5))),
    ],
)
def test_league_shape(filename: str, shape: tuple[tuple[int, ...], ...]):
    assert _shape(_parse_fixture(filename)) == shape


@pytest.mark.parametrize(
    ("filename", "conferences", "divisions"),
    [
        ("08_TEAMS.lge", ("",), ("Eastern", "Western")),
        (
            "10_TEAMS.LGE",
            ("",),
            ("North America - West", "North America - East", "Europe"),
        ),
        ("12_TEAMS.LGE", ("",), ("Atlantic", "Central", "Pacific")),
        (
            "NFLPA94.lge",
            ("American", "National"),
            ("Eastern", "Central", "Western") * 2,
        ),
        # Conference names carry leftover text after the NUL.
        (
            "NFLPI97R.LGE",
            ("American", "National"),
            ("Eastern", "Central", "Western") * 2,
        ),
        (
            "_default.lge",
            ("American", "National"),
            ("Eastern", "Central", "Western") * 2,
        ),
    ],
)
def test_stock_league_names(
    filename: str, conferences: tuple[str, ...], divisions: tuple[str, ...]
):
    lge = _parse_fixture(filename)
    assert tuple(conference.name for conference in lge.conferences) == conferences
    assert (
        tuple(
            division.name
            for conference in lge.conferences
            for division in conference.divisions
        )
        == divisions
    )


@pytest.mark.parametrize(
    ("filename", "number", "official_name"),
    [
        ("08_TEAMS.lge", 5, "British Columbia Bobcats"),  # 16-character name
        ("10_TEAMS.LGE", 10, "London Kings"),
        ("12_TEAMS.LGE", 10, "Denver Gold"),
        ("NFLPA94.lge", 12, "Los Angeles (A) Raiders"),
        ("NFLPA93E.LGE", 12, "Los Angeles Raiders"),
        ("NFLPA93E.LGE", 28, "San Francisco 49ers"),
        ("_default.lge", 11, "Denver Stallions"),
        ("_default.lge", 26, "St. Louis Billy Goats"),
        ("NFLPI97R.LGE", 17, "Dallas Cowboys"),  # leftover text after the NUL
        ("NFLPI97R.LGE", 30, "St Louis Rams"),  # last team; leftover text
    ],
)
def test_stock_league_teams(filename: str, number: int, official_name: str):
    assert _teams(_parse_fixture(filename))[number - 1].official_name == official_name


def test_read_returns_lge_file_and_matches_parse():
    lge = read_lge(LEAGUE, FIXTURE_DIR)
    assert isinstance(lge, LgeFile)
    assert _parse_fixture("PNFL.lge") == lge


def test_read_accepts_str_league_dir():
    assert read_lge(LEAGUE, str(FIXTURE_DIR)) == read_lge(LEAGUE, FIXTURE_DIR)


def test_missing_file_raises_oserror_for_built_path(tmp_path: Path):
    with pytest.raises(OSError) as info:
        read_lge("missing", tmp_path)
    assert Path(info.value.filename) == tmp_path / "missing.lge"


# --- built files ---


def test_built_file_parses(make_lge):
    # Every chunk at its exact size: the accepted side of each size limit.
    team = Team("T1", "N1", NO_GAMES)
    division = Division(name="D1", teams=(team,), standings=(team,))
    conference = Conference(name="C1", divisions=(division,), standings=(team,))
    assert parse_lge(make_lge()) == LgeFile(conferences=(conference,))


@pytest.mark.parametrize(
    "shape", [((2,),), ((1,), (2,)), ((2, 1), (1, 3)), ((0, 2), (3,))]
)
def test_grouped_order_reads_like_nested(make_chunks, make_lge, shape):
    # Every C03, then every D03, T03 and R03; the counts nest them.
    grouped = parse_lge(make_lge(make_chunks(shape, grouped=True)))
    assert grouped == parse_lge(make_lge(make_chunks(shape)))
    assert _teams(grouped)[-1].name == f"T{len(_teams(grouped))}"


def test_grouped_order_missing_roster_rejected(make_chunks, make_lge):
    chunks = make_chunks(((2,),), grouped=True)
    del chunks[-2]
    with pytest.raises(InvalidLgeError, match=r"Expected R03 chunk at .*, found S03"):
        parse_lge(make_lge(chunks))


def test_names_read_up_to_nul(
    make_chunks,
    make_chunk,
    make_conference_data,
    make_division_data,
    make_team_data,
    make_lge,
):
    chunks = make_chunks()
    chunks[C03] = make_chunk(ID_C03, make_conference_data(1, b"AFC\x00old"))
    chunks[D03] = make_chunk(ID_D03, make_division_data(1, b"West\x00old"))
    chunks[T03] = make_chunk(ID_T03, make_team_data(1, b"Denver\x00x", b"Broncos\x00y"))
    lge = parse_lge(make_lge(chunks))
    assert lge.conferences[0].name == "AFC"
    assert lge.conferences[0].divisions[0].name == "West"
    assert _names(_only_team(lge)) == ("Denver", "Broncos")


def test_names_filling_their_field_read_whole(
    make_chunks,
    make_chunk,
    make_conference_data,
    make_division_data,
    make_team_data,
    make_lge,
):
    # No NUL: the name is the whole field and stops there, though the next
    # field's bytes follow at once.
    chunks = make_chunks()
    chunks[C03] = make_chunk(ID_C03, make_conference_data(1, b"C" * NAME_SIZE))
    chunks[D03] = make_chunk(ID_D03, make_division_data(1, b"D" * NAME_SIZE))
    team = make_team_data(1, b"N" * TEAM_TEXT_SIZE, b"K" * TEAM_TEXT_SIZE)
    chunks[T03] = make_chunk(ID_T03, team)
    lge = parse_lge(make_lge(chunks))
    assert lge.conferences[0].name == "C" * 25
    assert lge.conferences[0].divisions[0].name == "D" * 25
    assert _names(_only_team(lge)) == ("N" * 17, "K" * 17)


@pytest.mark.parametrize("number", [0, 1, 30, 255])
def test_team_number_in_chunk_keys_the_mask(
    make_chunks, make_chunk, make_team_data, make_lge, number: int
):
    chunks = make_chunks()
    chunks[T03] = make_chunk(ID_T03, make_team_data(number, b"Dallas", b"Cowboys"))
    assert _names(_only_team(parse_lge(make_lge(chunks)))) == ("Dallas", "Cowboys")


def test_non_ascii_byte_decodes_as_replacement(
    make_chunks, make_chunk, make_team_data, make_lge
):
    chunks = make_chunks()
    chunks[T03] = make_chunk(ID_T03, make_team_data(1, b"Montr\xe9al"))
    assert _only_team(parse_lge(make_lge(chunks))).name == "Montr�al"


# --- limits ---


def test_empty_file_rejected():
    with pytest.raises(InvalidLgeError, match="Empty file"):
        parse_lge(b"")


@pytest.mark.parametrize(
    ("index", "size", "expected"),
    [
        (L03, 89, 90),
        (L03, 91, 90),
        (C03, 29, 30),
        (C03, 31, 30),
        (D03, 29, 30),
        (D03, 31, 30),
        (T03, 170, 171),
        (T03, 172, 171),
        (R03, 324, 325),
        (R03, 326, 325),
    ],
)
def test_chunk_one_byte_off_its_size_rejected(
    make_chunks, make_chunk, make_lge, index: int, size: int, expected: int
):
    chunks = make_chunks()
    tag, _ = CHUNK_HEADER.unpack_from(chunks[index])
    data = chunks[index][CHUNK_HEADER.size :]
    chunks[index] = make_chunk(tag, data.ljust(size, b"\x00")[:size])
    with pytest.raises(
        InvalidLgeError, match=rf"is {size} bytes, expected {expected}\.$"
    ):
        parse_lge(make_lge(chunks))


def test_counted_chunk_shorter_than_its_fixed_part_rejected(
    make_chunks, make_chunk, make_lge
):
    chunks = make_chunks()
    chunks[D03] = make_chunk(ID_D03, bytes(DIVISION_BASE_SIZE - 1))
    with pytest.raises(InvalidLgeError, match=r"is 28 bytes, expected at least 29\.$"):
        parse_lge(make_lge(chunks))


def test_counted_chunk_of_just_its_fixed_part_accepted(
    make_chunks, make_chunk, make_division_data, make_lge
):
    # A division with no teams: its D03 chunk is the fixed part alone.
    chunks = make_chunks()
    chunks[D03 : R03 + 1] = [make_chunk(ID_D03, make_division_data(0))]
    assert parse_lge(make_lge(chunks)).conferences[0].divisions[0].teams == ()


@pytest.mark.parametrize("length", [1, CHUNK_HEADER.size - 1])
def test_chunk_header_cut_short_rejected(make_chunks, make_lge, length: int):
    chunks = make_chunks()
    chunks[S03] = chunks[S03][:length]
    with pytest.raises(
        InvalidLgeError, match=r"Chunk header at 0x[0-9a-f]+ is cut short\.$"
    ):
        parse_lge(make_lge(chunks))


def test_bare_chunk_header_passes_framing(make_chunks, make_chunk, make_lge):
    # Eight bytes are a whole header: what fails is the S03 data size.
    chunks = make_chunks()
    chunks[S03] = make_chunk(ID_S03, b"")
    with pytest.raises(InvalidLgeError, match=r"is 0 bytes, expected at least 3\.$"):
        parse_lge(make_lge(chunks))


def test_chunk_running_past_end_rejected(make_chunks, make_lge):
    chunks = make_chunks()
    chunks[S03] = chunks[S03][:-1]
    with pytest.raises(
        InvalidLgeError,
        match=r"S03 chunk at 0x[0-9a-f]+ runs past the end of the file\.$",
    ):
        parse_lge(make_lge(chunks))


def test_huge_chunk_size_rejected():
    with pytest.raises(
        InvalidLgeError, match=r"L03 chunk at 0x0 runs past the end of the file\.$"
    ):
        parse_lge(CHUNK_HEADER.pack(ID_L03, 0xFFFF_FFFF))


def test_data_after_schedule_rejected(make_lge):
    with pytest.raises(
        InvalidLgeError, match=r"Unexpected data at 0x[0-9a-f]+ after the S03 chunk\.$"
    ):
        parse_lge(make_lge() + b"\x00")


# --- chunk order ---


@pytest.mark.parametrize(
    ("drop", "message"),
    [
        (L03, r"Expected L03 chunk at 0x0, found C03\.$"),
        (C03, r"Expected C03 chunk at 0x[0-9a-f]+, found D03\.$"),
        (D03, r"Expected D03 chunk at 0x[0-9a-f]+, found T03\.$"),
        (T03, r"Expected T03 chunk at 0x[0-9a-f]+, found R03\.$"),
        (R03, r"Expected R03 chunk at 0x[0-9a-f]+, found S03\.$"),
        (S03, r"Expected S03 chunk at 0x[0-9a-f]+, found the end of the file\.$"),
    ],
)
def test_missing_chunk_rejected(make_chunks, make_lge, drop: int, message: str):
    chunks = make_chunks()
    del chunks[drop]
    with pytest.raises(InvalidLgeError, match=message):
        parse_lge(make_lge(chunks))


def test_fewer_conferences_than_counted_rejected(
    make_chunks, make_chunk, make_league_data, make_lge
):
    chunks = make_chunks()
    chunks[L03] = make_chunk(ID_L03, make_league_data(2))
    with pytest.raises(
        InvalidLgeError, match=r"Expected C03 chunk at .*, found S03\.$"
    ):
        parse_lge(make_lge(chunks))


def test_more_conferences_than_counted_rejected(
    make_chunks, make_chunk, make_league_data, make_lge
):
    chunks = make_chunks(((1,), (1,)))
    chunks[L03] = make_chunk(ID_L03, make_league_data(1))
    with pytest.raises(
        InvalidLgeError, match=r"Expected S03 chunk at .*, found C03\.$"
    ):
        parse_lge(make_lge(chunks))


def test_fewer_teams_than_counted_rejected(
    make_chunks, make_chunk, make_division_data, make_lge
):
    chunks = make_chunks()
    chunks[D03] = make_chunk(ID_D03, make_division_data(2))
    with pytest.raises(
        InvalidLgeError, match=r"Expected T03 chunk at .*, found S03\.$"
    ):
        parse_lge(make_lge(chunks))


def test_unprintable_tag_shown_as_hex():
    with pytest.raises(
        InvalidLgeError, match=r"Expected L03 chunk at 0x0, found 00 01 02 03\.$"
    ):
        parse_lge(b"\x00\x01\x02\x03" + bytes(4))


def test_error_names_the_path_first():
    with pytest.raises(InvalidLgeError, match=r"^league\.lge: ") as exc:
        parse_lge(b"", "league.lge")
    assert str(exc.value) == "league.lge: Empty file."
    assert exc.value.path == Path("league.lge")


# --- standings ---

# The 2048 season after week 16, as the game's League Standings screen showed
# it: Miami above Buffalo (both 10-6) on the tie-breakers (a split series,
# equal division records, Miami's better conference record), though Buffalo
# scored 97 more points. In season the screen sorts tied teams by points for
# instead; see docs/fbpro98-game-behavior.md.
PNFL_2048_FINAL = (
    ("Miami", "Buffalo", "New England", "Jacksonville"),
    ("Cincinnati", "Pittsburgh", "Las Vegas", "Denver", "Los Angeles"),
    ("Washington", "Atlanta", "New York", "Philadelphia"),
    ("Chicago", "Minnesota", "Green Bay", "San Francisco", "Seattle"),
)


def _division_order(lge: LgeFile) -> tuple[tuple[str, ...], ...]:
    return tuple(
        tuple(team.name for team in division.standings)
        for conference in lge.conferences
        for division in conference.divisions
    )


def test_division_standings_match_the_games_season_end_screen():
    assert _division_order(_parse_fixture("PNFL-2048-after-week16.lge")) == (
        PNFL_2048_FINAL
    )


def test_division_ties_follow_the_manuals_steps():
    # 2043: Indianapolis over New England and Las Vegas over Pittsburgh on
    # division record; 2046: Jacksonville over Denver head-to-head, Chicago
    # over Green Bay on conference record (Green Bay's points were better).
    assert _division_order(_parse_fixture("PNFL-2043-after-super-bowl.lge")) == (
        ("New York A", "Indianapolis", "New England", "Jacksonville"),
        ("Kansas City", "Minnesota", "Los Angeles", "Las Vegas", "Pittsburgh"),
        ("Washington", "Detroit", "New York N", "Atlanta"),
        ("Chicago", "San Francisco", "New Orleans", "Seattle", "Anaheim"),
    )
    assert _division_order(_parse_fixture("PNFL-2046-after-super-bowl.lge")) == (
        ("New York A", "Buffalo", "Indianapolis", "New England"),
        ("Pittsburgh", "Houston", "Las Vegas", "Jacksonville", "Denver"),
        ("Washington", "Philadelphia", "Atlanta", "New York N"),
        ("Minnesota", "Seattle", "San Francisco", "Chicago", "Green Bay"),
    )


def test_ranked_orders_any_teams_of_the_file():
    # 2048's wild cards: Buffalo over Pittsburgh (both 10-6) head-to-head, as
    # the game seeded them.
    lge = _parse_fixture("PNFL-2048-after-week16.lge")
    by_name = {team.name: team for team in lge.teams}
    pair = (by_name["Pittsburgh"], by_name["Buffalo"])
    assert tuple(t.name for t in ranked(lge, pair)) == ("Buffalo", "Pittsburgh")


def test_ranked_default_covers_every_team_of_the_file():
    lge = _parse_fixture("PNFL-2048-after-week16.lge")
    assert sorted(t.name for t in ranked(lge)) == sorted(t.name for t in lge.teams)
    assert len(ranked(lge)) == 18


def test_final_regular_season_records():
    records = {team.name: team.record for team in _teams(_parse_fixture(WEEK16))}
    assert records["New England"] == Record(7, 8, 1, 351, 369)
    assert records["Denver"] == Record(9, 6, 1, 362, 323)
    assert records["Baltimore"] == Record(13, 3, 0, 371, 235)
    assert records["Cincinnati"] == Record(7, 9, 0, 359, 456)
    # 16 weeks of 9 games: every game is one win or two ties.
    wins = sum(record.wins for record in records.values())
    ties = sum(record.ties for record in records.values())
    assert wins + ties // 2 == 16 * 9


def test_conference_standings_break_ties_by_the_manuals_steps():
    afc, nfc = _parse_fixture(WEEK16).conferences
    assert tuple(team.name for team in afc.standings) == (
        "Baltimore",
        "Miami",
        "Denver",
        "Las Vegas",
        "New England",
        "Cincinnati",
        "Jacksonville",
        "Pittsburgh",
        "Buffalo",
    )
    # 7-9: New York beat Green Bay; 6-10: Philadelphia beat San Francisco.
    assert tuple(team.name for team in nfc.standings) == (
        "Chicago",
        "Minnesota",
        "Washington",
        "Atlanta",
        "New York",
        "Green Bay",
        "Philadelphia",
        "San Francisco",
        "Seattle",
    )


def test_grouped_league_season_matches_the_real_1993_results():
    # NFLPA93E holds the 1993 NFL season as played, in grouped chunk order and
    # with bye weeks.
    lge = _parse_fixture("NFLPA93E.LGE")
    records = {team.official_name: team.record for team in _teams(lge)}
    assert records["Dallas Cowboys"] == Record(12, 4, 0, 376, 229)
    assert records["Buffalo Bills"] == Record(12, 4, 0, 329, 242)
    assert records["Houston Oilers"] == Record(12, 4, 0, 368, 238)
    assert records["San Francisco 49ers"] == Record(10, 6, 0, 473, 295)
    assert records["Cincinnati Bengals"] == Record(3, 13, 0, 187, 319)


def test_playoff_games_do_not_count():
    final = [team.record for team in _teams(_parse_fixture(WEEK16))]
    after = [team.record for team in _teams(_parse_fixture(SUPER_BOWL))]
    assert after == final


def test_before_week_one_records_are_zero_and_standings_keep_file_order():
    lge = _parse_fixture(BEFORE_WEEK1)
    assert {team.record for team in _teams(lge)} == {NO_GAMES}
    for conference in lge.conferences:
        teams = tuple(t for division in conference.divisions for t in division.teams)
        assert conference.standings == teams
        for division in conference.divisions:
            assert division.standings == division.teams


def _with_schedule(make_chunks, make_chunk, data: bytes) -> list[bytes]:
    # Two teams in one division, with this S03 data.
    chunks = make_chunks(((2,),))
    chunks[-1] = make_chunk(ID_S03, data)
    return chunks


def test_record_counts_played_regular_season_games(
    make_chunks, make_chunk, make_schedule_data, make_game, make_lge
):
    regular = [[make_game(1, 21, 2, 14)], [make_game(2, 10, 1, 10, overtime=1)]]
    chunks = _with_schedule(make_chunks, make_chunk, make_schedule_data(regular))
    first, second = _teams(parse_lge(make_lge(chunks)))
    assert first.record == Record(1, 0, 1, 31, 24)
    assert second.record == Record(0, 1, 1, 24, 31)


def test_unplayed_games_skipped(
    make_chunks, make_chunk, make_schedule_data, make_game, make_lge
):
    # Unplayed games carry 0xFF scores, and 0xFF teams when not yet known.
    regular = [[make_game(0xFF, 0xFF, 0xFF, 0xFF, status=2)]]
    chunks = _with_schedule(make_chunks, make_chunk, make_schedule_data(regular))
    assert {team.record for team in _teams(parse_lge(make_lge(chunks)))} == {NO_GAMES}


def test_playoff_games_skipped(
    make_chunks, make_chunk, make_schedule_data, make_game, make_lge
):
    data = make_schedule_data(playoffs=[[make_game(1, 30, 2, 3)]])
    chunks = _with_schedule(make_chunks, make_chunk, data)
    assert {team.record for team in _teams(parse_lge(make_lge(chunks)))} == {NO_GAMES}


def test_built_standings_break_a_split_series_on_division_net_points(
    make_chunks, make_chunk, make_schedule_data, make_game, make_lge
):
    # Team 2 won its game by more: it ranks first in the division and the
    # conference though team 1 comes first in the file.
    regular = [[make_game(1, 20, 2, 10)], [make_game(2, 30, 1, 10)]]
    chunks = _with_schedule(make_chunks, make_chunk, make_schedule_data(regular))
    lge = parse_lge(make_lge(chunks))
    first, second = _teams(lge)
    assert lge.conferences[0].divisions[0].standings == (second, first)
    assert lge.conferences[0].standings == (second, first)


@pytest.mark.parametrize(("home", "away"), [(1, 2), (2, 1)])
def test_played_game_with_first_and_last_team_accepted(
    make_chunks, make_chunk, make_schedule_data, make_game, make_lge, home, away
):
    data = make_schedule_data([[make_game(home, 7, away, 3)]])
    chunks = _with_schedule(make_chunks, make_chunk, data)
    assert _teams(parse_lge(make_lge(chunks)))[home - 1].record.wins == 1


@pytest.mark.parametrize(("home", "away", "bad"), [(0, 2, 0), (1, 3, 3)])
def test_played_game_with_unknown_team_rejected(
    make_chunks, make_chunk, make_schedule_data, make_game, make_lge, home, away, bad
):
    data = make_schedule_data([[make_game(home, 7, away, 3)]])
    chunks = _with_schedule(make_chunks, make_chunk, data)
    with pytest.raises(
        InvalidLgeError, match=rf"week 1: No team {bad} \(teams are 1-2\)\.$"
    ):
        parse_lge(make_lge(chunks))


def test_schedule_shorter_than_its_header_rejected(make_chunks, make_chunk, make_lge):
    # The 3-byte header alone, the default built schedule, is accepted.
    chunks = make_chunks()
    chunks[S03] = make_chunk(ID_S03, bytes(2))
    with pytest.raises(InvalidLgeError, match=r"is 2 bytes, expected at least 3\.$"):
        parse_lge(make_lge(chunks))


@pytest.mark.parametrize("cut", [1, 7])
def test_schedule_cut_short_in_a_week_rejected(
    make_chunks, make_chunk, make_schedule_data, make_game, make_lge, cut: int
):
    # 1: the game's last byte is missing; 7: the whole week is. With nothing
    # cut, the same schedule is accepted (test_played_game_with_first_...).
    data = make_schedule_data([[make_game(1, 7, 2, 3)]])[:-cut]
    chunks = _with_schedule(make_chunks, make_chunk, data)
    with pytest.raises(InvalidLgeError, match=r"is cut short in week 1\.$"):
        parse_lge(make_lge(chunks))


def test_schedule_with_data_after_the_last_week_rejected(
    make_chunks, make_chunk, make_schedule_data, make_game, make_lge
):
    data = make_schedule_data([[make_game(1, 7, 2, 3)]]) + b"\x00"
    chunks = _with_schedule(make_chunks, make_chunk, data)
    with pytest.raises(InvalidLgeError, match=r"has data after the last week\.$"):
        parse_lge(make_lge(chunks))


# --- games ---


def test_games_and_playoffs_after_the_super_bowl():
    lge = _parse_fixture(SUPER_BOWL)
    assert [len(week) for week in lge.weeks] == [9] * 16
    assert [len(round_) for round_ in lge.playoffs] == [4, 2, 1]
    final = lge.playoffs[-1][0]
    assert final.winner is not None and final.loser is not None
    assert (final.winner.name, final.loser.name) == ("Miami", "Minnesota")
    assert (final.home_score, final.away_score) == (14, 10)
    assert lge.unplayed_games == 0


def test_no_playoff_game_before_the_playoffs():
    lge = _parse_fixture(WEEK16)
    assert lge.playoffs == ((), (), ())
    assert lge.unplayed_games == 7


def test_no_game_before_week_one():
    lge = _parse_fixture(BEFORE_WEEK1)
    assert lge.weeks == ((),) * 16
    assert lge.unplayed_games == 16 * 9 + 7


def test_games_reference_the_file_teams():
    lge = read_lge(LEAGUE, FIXTURE_DIR)
    teams = _teams(lge)
    games = [game for week in lge.weeks for game in week]
    assert len(games) == 54  # six weeks played
    assert all(
        any(game.home is team for team in teams)
        and any(game.away is team for team in teams)
        for game in games
    )
    assert sum(team.record.games for team in teams) == 2 * len(games)


def test_tied_game_has_no_winner_or_loser(
    make_chunks, make_chunk, make_schedule_data, make_game, make_lge
):
    data = make_schedule_data([[make_game(1, 10, 2, 10)]])
    chunks = _with_schedule(make_chunks, make_chunk, data)
    (game,) = parse_lge(make_lge(chunks)).weeks[0]
    assert game.winner is None
    assert game.loser is None


def test_unplayed_playoff_game_skipped_and_counted(
    make_chunks, make_chunk, make_schedule_data, make_game, make_lge
):
    # Teams may be known (0xFF scores) before the round is played.
    data = make_schedule_data(playoffs=[[make_game(1, 0xFF, 2, 0xFF, status=2)]])
    chunks = _with_schedule(make_chunks, make_chunk, data)
    lge = parse_lge(make_lge(chunks))
    assert lge.playoffs == ((),)
    assert lge.unplayed_games == 1


@pytest.mark.parametrize(("home", "away"), [(1, 2), (2, 1)])
def test_played_playoff_game_with_first_and_last_team_read(
    make_chunks, make_chunk, make_schedule_data, make_game, make_lge, home, away
):
    data = make_schedule_data(playoffs=[[make_game(home, 7, away, 3)]])
    chunks = _with_schedule(make_chunks, make_chunk, data)
    lge = parse_lge(make_lge(chunks))
    (game,) = lge.playoffs[0]
    assert game.winner is _teams(lge)[home - 1]
    assert game.loser is _teams(lge)[away - 1]


@pytest.mark.parametrize(("home", "away", "bad"), [(0, 2, 0), (1, 3, 3)])
def test_played_playoff_game_with_unknown_team_rejected(
    make_chunks, make_chunk, make_schedule_data, make_game, make_lge, home, away, bad
):
    # No regular week here, so the first playoff round is week 1.
    data = make_schedule_data(playoffs=[[make_game(home, 7, away, 3)]])
    chunks = _with_schedule(make_chunks, make_chunk, data)
    with pytest.raises(
        InvalidLgeError, match=rf"week 1: No team {bad} \(teams are 1-2\)\.$"
    ):
        parse_lge(make_lge(chunks))
