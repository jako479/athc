"""Tests for athc.fbpro98_lg2.reader.

Real fixtures in data/ (custom, modern stock, old stock) cover whole-file
parsing; built bytes cover the limits and edge cases no real file holds.
"""

from __future__ import annotations

from pathlib import Path, PureWindowsPath

import pytest

from athc.fbpro98_lg2 import (
    FilePair,
    HalfFiles,
    InvalidLg2Error,
    LeagueType,
    Lg2File,
    TeamFiles,
    parse_lg2,
    read_lg2,
)
from athc.fbpro98_lg2.schema import FILENAME_SIZE, FOLDER_SIZE, TEAM_RECORD_SIZE
from athc.fbpro98_lge import read_lge

FIXTURE_DIR = Path(__file__).resolve().parent / "data"
# The same league's .lge, for the team order.
LGE_DIR = FIXTURE_DIR.parents[1] / "fbpro98_lge" / "data"
LEAGUE = "PNFL"
CUSTOM = FIXTURE_DIR / "PNFL.lg2"
MODERN_STOCK = FIXTURE_DIR / "NFLPI97.LG2"
OLD_STOCK = FIXTURE_DIR / "08_TEAMS.LG2"


def _team(folder: str, names: tuple[str, ...]) -> TeamFiles:
    # An empty folder leaves just the filename, as in an old stock league.
    paths = [f"{folder}\\{name}" if folder else name for name in names]
    return TeamFiles(
        first_half=HalfFiles(
            offense=FilePair(profile=paths[0], gameplan=paths[1]),
            defense=FilePair(profile=paths[2], gameplan=paths[3]),
        ),
        second_half=HalfFiles(
            offense=FilePair(profile=paths[4], gameplan=paths[5]),
            defense=FilePair(profile=paths[6], gameplan=paths[7]),
        ),
    )


# --- real files ---


def test_custom_league_teams_follow_the_lge_order():
    # Each coach's folder is named after the team: `PNFL\2049\Plans\Denver
    # (Brian)`. The 18 folders match the .lge's 18 teams in order.
    folders = [
        PureWindowsPath(team.first_half.offense.profile).parent.name
        for team in read_lg2(LEAGUE, FIXTURE_DIR).teams
    ]
    names = [team.name for team in read_lge(LEAGUE, LGE_DIR).teams]
    assert [folder.split(" (")[0] for folder in folders] == names


@pytest.mark.parametrize(
    ("index", "expected"),
    [
        # Folder and filename fields both hold leftover text after the NUL.
        (
            0,
            _team(
                "PNFL\\2049\\Plans\\Jacksonville (Matt)",
                (
                    "JAGS-O1.prf",
                    "JAGS-O1.pln",
                    "JAGS-D1.prf",
                    "JAGS-D1.pln",
                    "JAGS-O2.prf",
                    "JAGS-O2.pln",
                    "JAGS-D2.prf",
                    "JAGS-D2.pln",
                ),
            ),
        ),
        # Same game plan in both halves.
        (
            5,
            _team(
                "PNFL\\2049\\Plans\\Las Vegas (Neil)",
                (
                    "LVOFF1.prf",
                    "RAIDEROFF.pln",
                    "LVDEF1.prf",
                    "RAIDERDEF.pln",
                    "LVOFF2.prf",
                    "RAIDEROFF.pln",
                    "LVDEF2.prf",
                    "RAIDERDEF.pln",
                ),
            ),
        ),
        # Last team.
        (
            17,
            _team(
                "PNFL\\2049\\Plans\\San Francisco (Charlie)",
                (
                    "49-49-O1.prf",
                    "49-49-O1.pln",
                    "49-49-D1.prf",
                    "49-49-D1.pln",
                    "49-49-O2.prf",
                    "49-49-O2.pln",
                    "49-49-D2.prf",
                    "49-49-D2.pln",
                ),
            ),
        ),
    ],
)
def test_custom_league_team_files(index: int, expected: TeamFiles):
    assert read_lg2(LEAGUE, FIXTURE_DIR).teams[index] == expected


def test_read_returns_lg2_file_and_matches_parse():
    lg2 = read_lg2(LEAGUE, FIXTURE_DIR)
    assert isinstance(lg2, Lg2File)
    assert parse_lg2(CUSTOM.read_bytes()) == lg2


def test_read_accepts_str_league_dir():
    assert read_lg2(LEAGUE, str(FIXTURE_DIR)) == read_lg2(LEAGUE, FIXTURE_DIR)


def test_custom_league_type():
    assert read_lg2(LEAGUE, FIXTURE_DIR).league_type is LeagueType.CUSTOM


# Parsed from bytes: the stock fixtures keep the game's upper-case `.LG2` name.


def test_modern_stock_league_type_and_team_count():
    lg2 = parse_lg2(MODERN_STOCK.read_bytes())
    assert lg2.league_type is LeagueType.MODERN_STOCK
    assert len(lg2.teams) == 30


@pytest.mark.parametrize(
    ("index", "prefix"),
    [(0, "BILLS"), (1, "COLTS"), (29, "RAMS")],
)
def test_modern_stock_league_team_files(index: int, prefix: str):
    # These teams' game plans end in a zero, not an O: BILLS0.PLN.
    names = ("O1.PRF", "0.PLN", "D1.PRF", "D.PLN", "O2.PRF", "0.PLN", "D2.PRF", "D.PLN")
    expected = _team("STOCK", tuple(prefix + name for name in names))
    assert parse_lg2(MODERN_STOCK.read_bytes()).teams[index] == expected


def test_old_stock_league():
    # Every team uses the same files, with no folder.
    lg2 = parse_lg2(OLD_STOCK.read_bytes())
    names = (
        "OFF1.PRF",
        "OFF.PLN",
        "DEF1.PRF",
        "DEF.PLN",
        "OFF2.PRF",
        "OFF.PLN",
        "DEF2.PRF",
        "DEF.PLN",
    )
    assert lg2.league_type is LeagueType.OLD_STOCK
    assert lg2.teams == (_team("", names),) * 8


def test_missing_file_raises_oserror_for_built_path(tmp_path: Path):
    with pytest.raises(OSError) as info:
        read_lg2("missing", tmp_path)
    assert Path(info.value.filename) == tmp_path / "missing.lg2"


# --- league type: the first entry's folder field decides ---


@pytest.mark.parametrize(
    ("folder", "league_type", "profile"),
    [
        (b"STOCK\x00A\\FBPRO97\\STOCK", LeagueType.MODERN_STOCK, "STOCK\\O1.prf"),
        (b"", LeagueType.OLD_STOCK, "O1.prf"),
    ],
)
def test_first_entry_decides_league_type(
    make_entry,
    make_team,
    make_entries,
    folder: bytes,
    league_type: LeagueType,
    profile: str,
):
    lg2 = parse_lg2(make_team(make_entries(0, make_entry(folder=folder))))
    assert lg2.league_type is league_type
    assert lg2.teams[0].first_half.offense.profile == profile
    assert lg2.teams[0].first_half.offense.gameplan == "Plans\\Team\\O1.pln"


@pytest.mark.parametrize(
    ("folder", "expected"),
    [
        (b"STOCK\x00A\\FBPRO97\\STOCK", "STOCK\\O1.pln"),
        (b"\x00SIERRA\\FBPRO97", "O1.pln"),
        (b"", "O1.pln"),
    ],
)
def test_stock_folder_on_later_entry_is_read(
    make_entry, make_team, make_entries, folder: bytes, expected: str
):
    entries = make_entries(1, make_entry(folder=folder, filename=b"O1.pln"))
    lg2 = parse_lg2(make_team(entries))
    assert lg2.teams[0].first_half.offense.gameplan == expected
    assert lg2.league_type is LeagueType.CUSTOM


def test_stock_folder_on_second_team_is_read(make_entry, make_team, make_entries):
    stock = make_entries(0, make_entry(folder=b"STOCK\x00A\\FBPRO97\\STOCK"))
    lg2 = parse_lg2(make_team() + make_team(stock))
    assert lg2.teams[1].first_half.offense.profile == "STOCK\\O1.prf"
    assert lg2.league_type is LeagueType.CUSTOM


@pytest.mark.parametrize(
    "folder",
    [b"STOCK", b"STOCK\x00OLD\\PATH", b"STOCK\x00A\\FBPRO97\\STOCKX"],
)
def test_stock_folder_without_full_signature_is_custom(
    make_entry, make_team, make_entries, folder: bytes
):
    entries = make_entries(0, make_entry(folder=folder))
    lg2 = parse_lg2(make_team(entries))
    assert lg2.teams[0].first_half.offense.profile == "STOCK\\O1.prf"
    assert lg2.league_type is LeagueType.CUSTOM


# --- stock leagues get the same checks ---


def test_stock_league_size_checked(make_entry, make_team, make_entries):
    stock = make_entries(0, make_entry(folder=b"STOCK\x00A\\FBPRO97\\STOCK"))
    with pytest.raises(InvalidLg2Error, match="not a whole number"):
        parse_lg2(make_team(stock)[:-1])


@pytest.mark.parametrize("folder", [b"STOCK\x00A\\FBPRO97\\STOCK", b""])
def test_stock_league_fields_checked(
    make_entry, make_team, make_entries, folder: bytes
):
    stock = make_entries(0, make_entry(folder=folder))
    stock[3] = make_entry(filename=b"")
    # Entry 3's filename: three entries in, past the folder.
    with pytest.raises(InvalidLg2Error, match=r"Empty filename at 0x726\.$"):
        parse_lg2(make_team(stock))


# --- limits ---


def test_empty_file_rejected():
    with pytest.raises(InvalidLg2Error, match="Empty file"):
        parse_lg2(b"")


def test_size_checked_before_fields(make_entry, make_team, make_entries):
    # One byte too long and an empty filename: the size is reported.
    entries = make_entries(0, make_entry(filename=b""))
    with pytest.raises(InvalidLg2Error, match="not a whole number"):
        parse_lg2(make_team(entries) + b"\x00")


@pytest.mark.parametrize("size", [TEAM_RECORD_SIZE - 1, TEAM_RECORD_SIZE + 1])
def test_size_not_whole_team_records_rejected(make_team, size: int):
    buffer = (make_team() + bytes(1))[:size]
    with pytest.raises(InvalidLg2Error, match="not a whole number"):
        parse_lg2(buffer)


def test_one_team_record_accepted(make_team):
    assert len(parse_lg2(make_team()).teams) == 1


def test_folder_at_max_length_accepted(make_entry, make_team, make_entries):
    folder = b"A" * (FOLDER_SIZE - 1)
    lg2 = parse_lg2(make_team(make_entries(0, make_entry(folder=folder))))
    assert lg2.teams[0].first_half.offense.profile == f"{'A' * 260}\\O1.prf"


def test_folder_without_nul_rejected(make_entry, make_team, make_entries):
    folder = b"A" * FOLDER_SIZE
    with pytest.raises(InvalidLg2Error, match=r"No NUL in folder field at 0x0\.$"):
        parse_lg2(make_team(make_entries(0, make_entry(folder=folder))))


def test_filename_at_max_length_accepted(make_entry, make_team, make_entries):
    filename = b"B" * (FILENAME_SIZE - 1)
    lg2 = parse_lg2(make_team(make_entries(0, make_entry(filename=filename))))
    assert lg2.teams[0].first_half.offense.profile == f"Plans\\Team\\{'B' * 261}"


def test_filename_without_nul_rejected(make_entry, make_team, make_entries):
    filename = b"B" * FILENAME_SIZE
    with pytest.raises(InvalidLg2Error, match=r"No NUL in filename field at 0x105\.$"):
        parse_lg2(make_team(make_entries(0, make_entry(filename=filename))))


def test_one_character_filename_accepted(make_entry, make_team, make_entries):
    lg2 = parse_lg2(make_team(make_entries(0, make_entry(filename=b"X"))))
    assert lg2.teams[0].first_half.offense.profile == "Plans\\Team\\X"


def test_empty_filename_rejected(make_entry, make_team, make_entries):
    with pytest.raises(InvalidLg2Error, match="Empty filename"):
        parse_lg2(make_team(make_entries(0, make_entry(filename=b""))))


# --- edge ---


def test_team_with_no_files_rejected(make_team):
    # The second team's first filename: one team record in, past the folder.
    with pytest.raises(InvalidLg2Error, match=r"Empty filename at 0x1166\.$"):
        parse_lg2(make_team() + bytes(TEAM_RECORD_SIZE))


def test_non_ascii_byte_decodes_as_replacement(make_entry, make_team, make_entries):
    entries = make_entries(0, make_entry(folder=b"Jos\xe9"))
    lg2 = parse_lg2(make_team(entries))
    assert lg2.teams[0].first_half.offense.profile == "Jos\ufffd\\O1.prf"


def test_error_names_the_path_first(make_team):
    with pytest.raises(InvalidLg2Error, match=r"^league\.lg2: ") as exc:
        parse_lg2(make_team()[:-1], "league.lg2")
    assert exc.value.path == Path("league.lg2")


def test_error_names_buffer_when_no_path_given():
    with pytest.raises(InvalidLg2Error) as exc:
        parse_lg2(b"")
    assert str(exc.value) == "<buffer>: Empty file."
    assert exc.value.path == Path("<buffer>")
