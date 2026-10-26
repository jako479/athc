"""Tests for athc.fbpro98_pyr.reader.

Real fixtures in data/ (the PNFL, the smallest stock league, the one the spec
names and one of the old layout) cover whole-file parsing; built bytes cover
each check and limit no real file holds.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from athc.fbpro98_pyr import (
    Injury,
    InvalidPyrError,
    Player,
    Position,
    PyrFile,
    Ratings,
    parse_pyr,
    read_pyr,
)
from tests.unit.fbpro98_pyr.conftest import TABLE

# The position groups of pyr.md section 5.
SPEC_GROUPS = {0, 10, 13, 14, 15, 16, 17, 18, 19}

# PNFL.pyr is the PNFL's 2049 season after week 6 (49PNFL6), the spec's
# sample; the stock files come from the game folder and keep its upper-case
# names, so they are parsed from bytes.
FIXTURE_DIR = Path(__file__).resolve().parent / "data"
LEAGUE = "PNFL"
STOCK = FIXTURE_DIR / "NFLPI97R.PYR"
SMALLEST = FIXTURE_DIR / "08_TEAMS.PYR"
OLD_STOCK = FIXTURE_DIR / "1994.PYR"

# pyr.md's appendix: the PNFL's coding table, row = high digit of the plain
# byte, each cell the byte written to disk.
PNFL_TABLE = dict(
    enumerate(
        bytes.fromhex(
            "d3 73 89 a9 2b 4b 41 e1 da ba 70 90 12 f2 48 28"
            "81 a1 d7 b7 59 f9 2f 0f 68 88 9e be 40 20 56 f6"
            "6f cf 85 65 27 07 5d 3d 96 b6 6c cc ee 4e 04 24"
            "7d 9d b3 93 55 35 eb 0b 64 c4 9a 7a fc 1c 52 32"
            "ab cb c1 61 e3 03 19 39 92 72 a8 c8 2a 4a 00 e0"
            "79 d9 af 8f 11 31 e7 47 c0 a0 d6 76 f8 18 2e 0e"
            "a7 87 bd dd 3f df 15 f5 ce 6e a4 84 26 46 3c 5c"
            "b5 d5 6b 8b 0d ed 23 43 7c 9c d2 b2 f4 54 ea 0a"
            "63 83 b9 99 3b 1b 51 f1 ca aa 80 60 22 02 38 58"
            "91 b1 67 c7 49 e9 ff 1f 78 d8 8e ae 30 50 e6 06"
            "5f bf 75 95 f7 17 4d 2d c6 a6 bc dc 5e fe 34 14"
            "8d 6d a3 c3 45 25 fb 5b 74 d4 8a 6a 0c 2c e2 42"
            "9b bb d1 71 f3 53 09 29 a2 82 b8 98 5a 3a f0 10"
            "c9 69 9f 7f 01 21 37 57 b0 d0 86 66 08 e8 1e 3e"
            "97 77 cd ad ef 4f 05 e5 de 7e b4 94 16 36 4c ec"
            "c5 a5 db 7b 1d fd 33 13 ac 8c 62 c2 44 e4 1a fa"
        )
    )
)

HEALTHY = Injury(level=0, injury=0, week=0)
NEWEST_CLASS = b"\x00\xff\xff\x00\x00\x00"  # the unknown bytes of a rookie
OLD_LAYOUT = b"\xff\xff\x00\x00\x00\x00"  # the unknown bytes of 1994.PYR


def _rejects(buffer: bytes, message: str) -> None:
    with pytest.raises(InvalidPyrError, match=f"{re.escape(message)}$"):
        parse_pyr(buffer)


# --- real files ---


def test_custom_league_header():
    pyr = read_pyr(LEAGUE, FIXTURE_DIR)
    assert (pyr.key, pyr.name, pyr.unknown) == (0xCE5F, "", bytes(6))
    assert len(pyr.players) == 9192
    assert list(pyr.players) == list(range(100, 9292))


def test_custom_league_coding_table_matches_the_spec_appendix():
    assert read_pyr(LEAGUE, FIXTURE_DIR).coding_table == PNFL_TABLE


def test_custom_league_player():
    # The spec's worked example, section 4; the ratings as the game's Player
    # Editor names them, so each rating is tied to its byte.
    ratings = Ratings(
        acceleration=81,
        agility=81,
        discipline=83,
        endurance=86,
        hands=71,
        intelligence=91,
        speed=81,
        strength=95,
    )
    assert read_pyr(LEAGUE, FIXTURE_DIR).players[6283] == Player(
        id=6283,
        first_name="C. J.",
        last_name="Stroud",
        position=Position.QB,
        group=0,
        years=5,
        injury=HEALTHY,
        height=0,
        weight=0,
        potential=ratings,
        actual=Ratings(
            acceleration=81,
            agility=81,
            discipline=83,
            endurance=86,
            hands=71,
            intelligence=91,
            speed=81,
            strength=95,
        ),
        unknown=bytes(6),
    )


def test_actual_above_potential_is_read():
    player = read_pyr(LEAGUE, FIXTURE_DIR).players[7302]
    assert (player.potential.agility, player.actual.agility) == (81, 83)


@pytest.mark.parametrize(
    ("player_id", "injury"),
    [
        # The spec's three, checked against the injury screen.
        (3422, Injury(level=167, injury=25, week=1)),
        (6672, Injury(level=64, injury=20, week=5)),
        (8484, Injury(level=15, injury=22, week=1)),
        # The spec's "other values seen" `202 1 32 3`: a level past one byte.
        (1913, Injury(level=458, injury=32, week=3)),
    ],
)
def test_injuries(player_id: int, injury: Injury):
    assert read_pyr(LEAGUE, FIXTURE_DIR).players[player_id].injury == injury


def test_placeholders():
    players = read_pyr(LEAGUE, FIXTURE_DIR).players.values()
    ones = Ratings(1, 1, 1, 1, 1, 1, 1, 1)
    no_one = [p for p in players if (p.first_name, p.last_name) == ("No", "One")]
    assert len(no_one) == 3258
    assert all(p.potential == ones and p.actual == ones for p in no_one)
    assert sum((p.first_name, p.last_name) == ("Delete", "Me") for p in players) == 191
    assert sum((p.first_name, p.last_name) == ("2043", "Draft") for p in players) == 114


def test_newest_draft_class_has_height_weight_and_marker():
    players = read_pyr(LEAGUE, FIXTURE_DIR).players
    rookies = [p for p in players.values() if p.height]
    assert len(rookies) == 555
    assert all(p.weight and p.unknown == NEWEST_CLASS for p in rookies)
    assert all(p.unknown == bytes(6) for p in players.values() if not p.height)
    assert players[5565] == Player(
        id=5565,
        first_name="Darren",
        last_name="Escudero",
        position=Position.QB,
        group=0,
        years=0,
        injury=HEALTHY,
        height=72,
        weight=204,
        potential=Ratings(50, 47, 59, 36, 40, 43, 49, 57),
        actual=Ratings(36, 32, 37, 19, 21, 36, 30, 49),
        unknown=NEWEST_CLASS,
    )


def test_name_with_leftover_text_after_nul():
    # Spaces follow the NUL in both name fields.
    player = read_pyr(LEAGUE, FIXTURE_DIR).players[145]
    assert (player.first_name, player.last_name) == ("Frank", "Ragnow")


def test_group_not_matching_the_position_is_read():
    player = read_pyr(LEAGUE, FIXTURE_DIR).players[4603]
    assert (player.position, player.group) == (Position.LB, 0)


def test_stock_league_header():
    pyr = parse_pyr(STOCK.read_bytes())
    assert (pyr.key, pyr.name) == (0xEE0F, "SYNERGISTIC1")
    assert pyr.unknown == b"\x00\xff\xff\x00\x00\x00"
    assert len(pyr.players) == 2100
    assert pyr.coding_table[0] == 0x0F


def test_stock_league_first_and_last_player():
    players = parse_pyr(STOCK.read_bytes()).players
    assert players[100] == Player(
        id=100,
        first_name="Todd",
        last_name="Collins",
        position=Position.QB,
        group=0,
        years=3,
        injury=HEALTHY,
        height=76,
        weight=224,
        # Eight distinct values: every rating tied to its byte.
        potential=Ratings(
            acceleration=95,
            agility=92,
            discipline=96,
            endurance=94,
            hands=97,
            intelligence=87,
            speed=98,
            strength=90,
        ),
        actual=Ratings(
            acceleration=69,
            agility=69,
            discipline=66,
            endurance=60,
            hands=73,
            intelligence=77,
            speed=71,
            strength=76,
        ),
        unknown=b"\x00\x01\x0f\x01\x00\x01",
    )
    assert players[2199] == Player(
        id=2199,
        first_name="Mallory",
        last_name="McCoy",
        position=Position.P,
        group=14,
        years=0,
        injury=HEALTHY,
        height=0,
        weight=0,
        potential=Ratings(98, 94, 94, 97, 97, 98, 97, 93),
        actual=Ratings(50, 50, 50, 50, 50, 50, 50, 51),
        unknown=NEWEST_CLASS,
    )


def test_leftover_bytes_after_nul_not_read():
    # Non-ASCII leftovers follow the first name's NUL.
    player = parse_pyr(STOCK.read_bytes()).players[208]
    assert (player.first_name, player.last_name) == ("Karim", "Abdul-Jabbar")


def test_plain_byte_written_as_itself_is_read():
    table = parse_pyr(STOCK.read_bytes()).coding_table
    assert (table[122], table[149]) == (122, 149)


def test_smallest_stock_league():
    pyr = parse_pyr(SMALLEST.read_bytes())
    assert pyr.key == 0xB77D
    assert list(pyr.players) == list(range(100, 507))
    first, last = pyr.players[100], pyr.players[506]
    assert (first.first_name, first.last_name) == ("Cary", "Broughton")
    assert (last.first_name, last.last_name) == ("Tim", "White")
    assert (last.position, last.group) == (Position.P, 14)


def test_every_position_and_group_appears():
    players = parse_pyr(SMALLEST.read_bytes()).players.values()
    assert {p.position for p in players} == set(Position)
    assert {p.group for p in players} == SPEC_GROUPS


def test_old_stock_layout_reads():
    # 1994.PYR holds `FF FF` at 0x36 of the header and of every record, one
    # byte before where the later stock files hold it.
    pyr = parse_pyr(OLD_STOCK.read_bytes())
    assert (pyr.key, pyr.name, pyr.unknown) == (0xACE2, "SYNERGISTIC1", OLD_LAYOUT)
    assert list(pyr.players) == list(range(100, 1581))
    assert all(p.unknown == OLD_LAYOUT for p in pyr.players.values())
    assert not any(p.height or p.weight for p in pyr.players.values())


def test_read_returns_pyr_file_and_matches_parse():
    pyr = read_pyr(LEAGUE, FIXTURE_DIR)
    assert isinstance(pyr, PyrFile)
    assert parse_pyr((FIXTURE_DIR / "PNFL.pyr").read_bytes()) == pyr


def test_read_accepts_str_league_dir():
    assert read_pyr(LEAGUE, str(FIXTURE_DIR)) == read_pyr(LEAGUE, FIXTURE_DIR)


def test_missing_file_raises_oserror_for_built_path(tmp_path: Path):
    with pytest.raises(OSError) as info:
        read_pyr("missing", tmp_path)
    assert Path(info.value.filename) == tmp_path / "missing.pyr"


# --- built files ---


def test_built_file_parses(make_record, make_pyr):
    record = make_record(
        100,
        first=b"C. J.",
        last=b"Stroud",
        potential=(81, 81, 83, 86, 71, 91, 81, 95),
        injury=(662, 7, 3),
        group=16,
        position=4,
        actual=(79, 79, 83, 83, 70, 89, 78, 94),
        years=5,
        height=72,
        weight=204,
        unknown=NEWEST_CLASS,
    )
    pyr = parse_pyr(make_pyr([record]))
    assert (pyr.key, pyr.name, pyr.unknown) == (0xCE5F, "", bytes(6))
    assert pyr.coding_table == dict(enumerate(TABLE))
    assert len(pyr.players) == 256
    assert pyr.players[100] == Player(
        id=100,
        first_name="C. J.",
        last_name="Stroud",
        position=Position.WR,
        group=16,
        years=5,
        injury=Injury(level=662, injury=7, week=3),
        height=72,
        weight=204,
        potential=Ratings(81, 81, 83, 86, 71, 91, 81, 95),
        actual=Ratings(79, 79, 83, 83, 70, 89, 78, 94),
        unknown=NEWEST_CLASS,
    )
    ones = Ratings(1, 1, 1, 1, 1, 1, 1, 1)
    assert pyr.players[355] == Player(
        355, "No", "One", Position.QB, 0, 0, HEALTHY, 0, 0, ones, ones, bytes(6)
    )


def test_header_name_filling_its_field_read_whole(make_header, make_pyr):
    header = make_header(name=b"SYNERGISTIC1O")
    assert parse_pyr(make_pyr(header=header)).name == "SYNERGISTIC1O"


def test_header_name_read_up_to_nul(make_header, make_pyr):
    header = make_header(name=b"SYN\x00ERGISTIC1")
    assert parse_pyr(make_pyr(header=header)).name == "SYN"


@pytest.mark.parametrize("key", [0, 0xFFFF])
def test_header_key_takes_any_value(make_header, make_pyr, key: int):
    assert parse_pyr(make_pyr(header=make_header(key=key))).key == key


@pytest.mark.parametrize(
    "unknown",
    [bytes(6), NEWEST_CLASS, OLD_LAYOUT, b"\x01\x02\x03\x04\x05\x06"],
)
def test_header_unknown_bytes_kept_as_read(make_header, make_pyr, unknown: bytes):
    header = make_header(unknown=unknown)
    assert parse_pyr(make_pyr(header=header)).unknown == unknown


def test_player_name_filling_its_field_read_whole(make_record, make_pyr):
    # No NUL: the name stops at its field, though the next field follows at once.
    record = make_record(100, first=b"A" * 13, last=b"B" * 13)
    player = parse_pyr(make_pyr([record])).players[100]
    assert (player.first_name, player.last_name) == ("A" * 13, "B" * 13)


def test_non_ascii_byte_decodes_as_replacement(make_record, make_pyr):
    record = make_record(100, first=b"Jos\xe9")
    assert parse_pyr(make_pyr([record])).players[100].first_name == "Jos�"


# --- size ---


def test_empty_file_rejected():
    _rejects(b"", "Empty file.")


@pytest.mark.parametrize("size", [1, 59])
def test_file_shorter_than_header_rejected(make_pyr, size: int):
    _rejects(
        make_pyr()[:size], f"File is {size} bytes, shorter than the 60-byte header."
    )


def test_header_alone_parses(make_header):
    pyr = parse_pyr(make_header())
    assert (pyr.players, pyr.coding_table) == ({}, {})


@pytest.mark.parametrize("size", [61, 119, 121])
def test_size_not_whole_records_rejected(make_pyr, size: int):
    _rejects(
        make_pyr()[:size],
        f"File size {size} is not the 60-byte header plus a whole number of "
        "60-byte player records.",
    )


def test_record_limit(make_pyr):
    assert len(parse_pyr(make_pyr(pad_to=65436)).players) == 65436
    _rejects(
        make_pyr(pad_to=65437),
        "File holds 65437 player records; ids are 16-bit, so at most 65436 fit.",
    )


# --- header ---


@pytest.mark.parametrize("offset", [0x02, 0x0E, 0x1C, 0x35])
def test_header_zero_byte_rejected(make_header, make_pyr, offset: int):
    header = bytearray(make_header())
    header[offset] = 0xFF
    _rejects(
        make_pyr(header=bytes(header)),
        f"Header byte at {offset:#04x} is 0xff, expected 0.",
    )


def test_size_checked_before_header(make_header, make_pyr):
    header = bytearray(make_header())
    header[0x02] = 1
    _rejects(
        make_pyr(header=bytes(header))[:61],
        "File size 61 is not the 60-byte header plus a whole number of 60-byte "
        "player records.",
    )


# --- coding table ---


def test_one_record_file_parses(make_record, make_pyr):
    # Id 100 reveals plain 0x64 and 0x00; a record of just those bytes decodes.
    record = make_record(
        100, first=b"dd", last=b"d", potential=(0,) * 8, actual=(0,) * 8
    )
    pyr = parse_pyr(make_pyr([record], pad_to=1))
    assert pyr.coding_table == {0x64: TABLE[0x64], 0x00: TABLE[0x00]}
    player = pyr.players[100]
    assert (player.first_name, player.last_name, player.years) == ("dd", "d", 0)


@pytest.mark.parametrize(
    ("index", "record_offset", "byte_offset"),
    [(0, "0x3c", "0x6e"), (1, "0x78", "0xaa")],
)
def test_byte_the_ids_do_not_reveal_rejected(
    make_record, make_pyr, index: int, record_offset: str, byte_offset: str
):
    # Records of only the revealed bytes, but for one record's years.
    records = [
        make_record(
            100 + i,
            first=b"dd",
            last=b"d",
            potential=(0,) * 8,
            actual=(0,) * 8,
            years=int(i == index),
        )
        for i in range(index + 1)
    ]
    _rejects(
        make_pyr(records, pad_to=1),
        f"Record {index} at {record_offset}: byte {TABLE[1]:#04x} at {byte_offset} is "
        "not in the coding table the ids reveal.",
    )


def test_255_players_cannot_reveal_rating_99(make_record, make_pyr):
    # Ids 100-354 reveal every plain byte but 0x63.
    record = make_record(100, potential=(99,) * 8)
    _rejects(
        make_pyr([record], pad_to=255),
        f"Record 0 at 0x3c: byte {TABLE[99]:#04x} at 0x58 is not in the coding table "
        "the ids reveal.",
    )
    assert parse_pyr(make_pyr([record], pad_to=256)).players[100].potential.speed == 99


@pytest.mark.parametrize(
    ("index", "offset", "plain", "revealed_in"),
    [
        # Ids 100-255 all have the high byte 0x00; record 1's differs.
        (1, 0x78, 0x00, 0),
        # Ids 256-355 have the high byte 0x01, first in record 156; record 157's differs.
        (157, 0x2508, 0x01, 156),
    ],
)
def test_plain_byte_written_two_ways_rejected(
    make_pyr, index: int, offset: int, plain: int, revealed_in: int
):
    buffer = bytearray(make_pyr())
    buffer[offset + 1] = (TABLE[plain] + 1) & 0xFF
    _rejects(
        bytes(buffer),
        f"Record {index} at {offset:#x}: plain {plain:#04x} is written as "
        f"{buffer[offset + 1]:#04x}, but as {TABLE[plain]:#04x} in record {revealed_in}.",
    )


def test_disk_byte_for_two_plain_values_rejected(make_pyr):
    # Record 1's first id byte is record 0's: one disk byte for 0x64 and 0x65.
    buffer = bytearray(make_pyr())
    buffer[0x78] = buffer[0x3C]
    _rejects(
        bytes(buffer),
        f"Record 1 at 0x78: {TABLE[0x64]:#04x} stands for both 0x64 and 0x65.",
    )


def test_header_checked_before_table(make_header, make_pyr):
    header = bytearray(make_header())
    header[0x35] = 1
    buffer = bytearray(make_pyr(header=bytes(header)))
    buffer[0x78] = buffer[0x3C]
    _rejects(bytes(buffer), "Header byte at 0x35 is 0x01, expected 0.")


# --- the model's rules through the parser ---


def test_rating_100_rejected(make_record, make_pyr):
    record = make_record(100, potential=(100, 1, 1, 1, 1, 1, 1, 1))
    _rejects(
        make_pyr([record]), "player 100 potential.acceleration must be 0-99, got 100."
    )


@pytest.mark.parametrize(("index", "offset"), [(0, "0x3c"), (1, "0x78")])
def test_position_15_rejected(make_record, make_pyr, index: int, offset: str):
    records = [make_record(100), make_record(101)]
    records[index] = make_record(100 + index, position=15)
    _rejects(
        make_pyr(records), f"Record {index} at {offset}: 15 is not a valid Position."
    )


@pytest.mark.parametrize(
    ("code", "position"),
    [
        # pyr.md section 5.
        (0, Position.QB),
        (1, Position.FB),
        (2, Position.HB),
        (3, Position.TE),
        (4, Position.WR),
        (5, Position.C),
        (6, Position.G),
        (7, Position.T),
        (8, Position.DE),
        (9, Position.DT),
        (10, Position.LB),
        (11, Position.CB),
        (12, Position.S),
        (13, Position.K),
        (14, Position.P),
    ],
)
def test_every_position_code_decoded(make_record, make_pyr, code: int, position):
    player = parse_pyr(make_pyr([make_record(100, position=code)])).players[100]
    assert player.position is position


def test_group_outside_the_table_rejected(make_record, make_pyr):
    _rejects(
        make_pyr([make_record(100, group=1)]),
        "player 100 group must be one of 0, 10, 13, 14, 15, 16, 17, 18, 19, got 1.",
    )


def test_table_checked_before_the_model(make_record, make_pyr):
    buffer = bytearray(make_pyr([make_record(100, group=1)]))
    buffer[0x78] = buffer[0x3C]
    _rejects(bytes(buffer), "stands for both 0x64 and 0x65.")


# --- errors ---


def test_error_names_the_path_first(make_pyr):
    with pytest.raises(InvalidPyrError, match=r"^league\.pyr: ") as exc:
        parse_pyr(make_pyr()[:-1], "league.pyr")
    assert exc.value.path == Path("league.pyr")


def test_error_names_buffer_when_no_path_given():
    with pytest.raises(InvalidPyrError) as exc:
        parse_pyr(b"")
    assert str(exc.value) == "<buffer>: Empty file."
    assert exc.value.path == Path("<buffer>")
