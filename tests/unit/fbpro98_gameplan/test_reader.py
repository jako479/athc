from __future__ import annotations

import struct
from pathlib import Path

import pytest

from athc.errors import AthcError
from athc.fbpro98_gameplan import (
    GamePlan,
    InvalidGamePlanError,
    PlayRef,
    ProfileType,
    SpecialSlot,
    StockPlayRef,
    parse_gameplan,
    read_gameplan,
)
from athc.fbpro98_gameplan.schema import (
    G95_AUDIBLE,
    G95_HEADER,
    G95_OFFSETS_TABLE,
    G95_PLAY_HEADER,
    J95_HEADER,
    J95_PLAN_DATA,
    S98_EXPECTED_DATA,
    S98_HEADER,
)
from tests.unit.fbpro98_gameplan.conftest import (
    DATA_DIR,
    DEFENSE_PATH,
    OFFENSE_PATH,
    both_sides,
    g95_end,
    s98_start,
)

EXPECTED_DIR = DATA_DIR / "expected"
OFFSETS_START = G95_HEADER.size + G95_AUDIBLE.size  # play offsets count from here
RECORDS_START = OFFSETS_START + G95_OFFSETS_TABLE.size
LAST_SLOT = GamePlan.NUMBER_PLAY_SLOTS - 1  # Stop Clock: the offense file's last record

# The custom special play of each category 1-10 in the fixtures.
OFFENSE_SPECIALS = (
    "BCFGPAT",
    "LACokick",
    "LAC-PUNT",
    "DBONSIDE",
    None,
    None,
    None,
    None,
    "BCFREEK",
    "BCSQUIB",
)
DEFENSE_SPECIALS = (
    None,
    "CIN-KR",
    "SKINPRW6",
    "BC-ON-R",
    "SFFKFGRD",
    "SFFFGPas",
    "SFFKPTRD",
    "SFFPuntD",
    "BCFREERT",
    "BCSQUIBR",
)


# ---------- helpers ----------


def _load_expected(name: str) -> list[str]:
    return (EXPECTED_DIR / name).read_text(encoding="utf-8").splitlines()


def _slot_names(plays: list[PlayRef | None]) -> list[str]:
    """One name per slot, an empty string for an empty slot: the golden's layout."""
    return [p.name if p is not None else "" for p in plays]


def _record_offset(data: bytes | bytearray, slot: int) -> int:
    """Absolute offset of the play record in `slot`, which must be filled."""
    relative = G95_OFFSETS_TABLE.unpack_from(data, OFFSETS_START)[slot]
    assert relative != 0, f"slot {slot} is empty"
    return OFFSETS_START + relative


def _set_g95_size(data: bytearray, size: int) -> None:
    struct.pack_into("<I", data, 4, size)


# ---------- valid fixtures ----------


@pytest.mark.parametrize(
    "pln_path, profile_type",
    [(OFFENSE_PATH, ProfileType.OFFENSE), (DEFENSE_PATH, ProfileType.DEFENSE)],
    ids=["offense", "defense"],
)
def test_profile_type_matches_fixture(
    pln_path: Path, profile_type: ProfileType
) -> None:
    assert read_gameplan(pln_path).profile_type is profile_type


@both_sides
def test_normal_plays_match_slot_golden(pln_path: Path) -> None:
    plan = read_gameplan(pln_path)
    assert _slot_names(plan.normal_plays) == _load_expected(
        f"{pln_path.stem}_normal_by_slot.txt"
    )


@pytest.mark.parametrize(
    "pln_path, expected",
    [(OFFENSE_PATH, OFFENSE_SPECIALS), (DEFENSE_PATH, DEFENSE_SPECIALS)],
    ids=["offense", "defense"],
)
def test_custom_special_plays_match_fixture(
    pln_path: Path, expected: tuple[str | None, ...]
) -> None:
    plan = read_gameplan(pln_path)
    names = tuple(p.name if p is not None else None for p in plan.custom_special_plays)
    assert names == expected


def test_offense_clock_categories_hold_stock_plays() -> None:
    plan = read_gameplan(OFFENSE_PATH)
    assert plan.special_plays[10:] == [
        SpecialSlot(
            stock=StockPlayRef(
                play_name="RUNCLOCK",
                map_offset=12765,
                map_size=333,
                play_category=1,
                special_category=11,
                user_category=1,
            )
        ),
        SpecialSlot(
            stock=StockPlayRef(
                play_name="STOPCLOK",
                map_offset=13098,
                map_size=333,
                play_category=1,
                special_category=12,
                user_category=1,
            )
        ),
    ]


def test_defense_clock_categories_are_empty() -> None:
    plan = read_gameplan(DEFENSE_PATH)
    assert plan.special_plays[10:] == [SpecialSlot(), SpecialSlot()]


def test_parse_gameplan_matches_read_gameplan() -> None:
    assert parse_gameplan(OFFENSE_PATH.read_bytes()) == read_gameplan(OFFENSE_PATH)


def test_invalid_gameplan_error_is_athc_error_subclass() -> None:
    assert issubclass(InvalidGamePlanError, AthcError)


# ---------- errors: the path in the message ----------


def test_error_names_the_path_first(tmp_path: Path) -> None:
    gameplan_path = tmp_path / "empty.pln"
    gameplan_path.write_bytes(b"")
    with pytest.raises(InvalidGamePlanError) as exc:
        read_gameplan(gameplan_path)
    assert str(exc.value) == (
        f"{gameplan_path}: File too small to contain PLN header and offsets table."
    )
    assert exc.value.path == gameplan_path


def test_bad_audible_bytes_print_as_hex(
    offense_bytes: bytearray, tmp_path: Path
) -> None:
    offense_bytes[G95_HEADER.size : OFFSETS_START] = b"\x09\x08\x07\x06"
    gameplan_path = tmp_path / "bad_audible.pln"
    gameplan_path.write_bytes(offense_bytes)
    with pytest.raises(InvalidGamePlanError) as exc:
        read_gameplan(gameplan_path)
    assert str(exc.value) == (
        f"{gameplan_path}: Audible bytes 09 08 07 06 != expected 00 01 02 03."
    )


def test_nonexistent_path_raises_oserror(tmp_path: Path) -> None:
    with pytest.raises(OSError):
        read_gameplan(tmp_path / "nonexistent.pln")


# ---------- errors: truncation ----------


# Each block check at its limit and one byte short of it: the offense bytes are
# cut `extra` bytes after `anchor`. A block that just fits passes its own check
# and the next block's check fails.
@pytest.mark.parametrize(
    "anchor, extra, match",
    [
        (
            "start",
            RECORDS_START - 1,
            "File too small to contain PLN header and offsets table",
        ),
        ("start", RECORDS_START, "G95 block extends past end of file"),
        (
            "g95_end",
            J95_HEADER.size + J95_PLAN_DATA.size - 1,
            "File too small to contain J95 block",
        ),
        (
            "g95_end",
            J95_HEADER.size + J95_PLAN_DATA.size,
            "File too small to contain S98 block header",
        ),
        (
            "s98_start",
            S98_HEADER.size - 1,
            "File too small to contain S98 block header",
        ),
        ("s98_start", S98_HEADER.size, "S98 block data extends past end of file"),
        (
            "s98_start",
            S98_HEADER.size + len(S98_EXPECTED_DATA) - 1,
            "S98 block data extends past end of file",
        ),
    ],
)
def test_truncated_file_raises(
    offense_bytes: bytearray, anchor: str, extra: int, match: str
) -> None:
    anchors = {
        "start": 0,
        "g95_end": g95_end(offense_bytes),
        "s98_start": s98_start(offense_bytes),
    }
    with pytest.raises(InvalidGamePlanError, match=match):
        parse_gameplan(bytes(offense_bytes[: anchors[anchor] + extra]))


@pytest.mark.parametrize(
    "past_end, match",
    [(1, "G95 block extends past end of file"), (0, "too small to contain J95")],
)
def test_g95_size_past_end_of_file_raises(
    offense_bytes: bytearray, past_end: int, match: str
) -> None:
    """A G95 block ending exactly at EOF fits; the J95 block then has no room."""
    _set_g95_size(offense_bytes, len(offense_bytes) - G95_HEADER.size + past_end)
    with pytest.raises(InvalidGamePlanError, match=match):
        parse_gameplan(bytes(offense_bytes))


def test_truncated_play_header_raises(offense_bytes: bytearray) -> None:
    # End the G95 block two bytes into its last record: too short for a header.
    last = _record_offset(offense_bytes, LAST_SLOT)
    _set_g95_size(offense_bytes, last + 2 - G95_HEADER.size)
    with pytest.raises(
        InvalidGamePlanError, match=f"Truncated play header at {last:#x}"
    ):
        parse_gameplan(bytes(offense_bytes))


def test_truncated_stock_play_record_raises(offense_bytes: bytearray) -> None:
    # The last record's header fits, its 14-byte stock body does not.
    body = _record_offset(offense_bytes, LAST_SLOT) + G95_PLAY_HEADER.size
    _set_g95_size(offense_bytes, body + 1 - G95_HEADER.size)
    with pytest.raises(
        InvalidGamePlanError, match=f"Truncated stock play record at {body:#x}"
    ):
        parse_gameplan(bytes(offense_bytes))


# ---------- errors: block headers ----------


def test_invalid_g95_header_raises(offense_bytes: bytearray) -> None:
    offense_bytes[0:4] = b"BAD!"
    with pytest.raises(InvalidGamePlanError, match="Invalid header 'BAD!' at 0x0"):
        parse_gameplan(bytes(offense_bytes))


def test_invalid_j95_header_raises(offense_bytes: bytearray) -> None:
    j95_pos = g95_end(offense_bytes)
    offense_bytes[j95_pos : j95_pos + 4] = b"BAD!"
    with pytest.raises(
        InvalidGamePlanError, match=f"Invalid header 'BAD!' at {j95_pos:#x}"
    ):
        parse_gameplan(bytes(offense_bytes))


def test_invalid_s98_header_raises(offense_bytes: bytearray) -> None:
    s98_pos = s98_start(offense_bytes)
    offense_bytes[s98_pos : s98_pos + 4] = b"BAD!"
    with pytest.raises(
        InvalidGamePlanError, match=f"Invalid header 'BAD!' at {s98_pos:#x}"
    ):
        parse_gameplan(bytes(offense_bytes))


# ---------- errors: G95 play records ----------


def test_offset_before_the_records_raises(offense_bytes: bytearray) -> None:
    relative = RECORDS_START - OFFSETS_START - 1
    struct.pack_into("<H", offense_bytes, OFFSETS_START, relative)
    with pytest.raises(
        InvalidGamePlanError,
        match=f"Play offset {relative:#x} for slot 0 is out of range",
    ):
        parse_gameplan(bytes(offense_bytes))


def test_offset_at_g95_end_raises(offense_bytes: bytearray) -> None:
    relative = g95_end(offense_bytes) - OFFSETS_START
    struct.pack_into("<H", offense_bytes, OFFSETS_START, relative)
    with pytest.raises(
        InvalidGamePlanError,
        match=f"Play offset {relative:#x} for slot 0 is out of range",
    ):
        parse_gameplan(bytes(offense_bytes))


def test_missing_null_terminator_raises(offense_bytes: bytearray) -> None:
    # Slot 0 holds a custom play; overwrite its filename's NUL.
    body = _record_offset(offense_bytes, 0) + G95_PLAY_HEADER.size
    offense_bytes[offense_bytes.index(0, body)] = ord("X")
    with pytest.raises(
        InvalidGamePlanError,
        match=f"Missing null terminator for play record at {body:#x}",
    ):
        parse_gameplan(bytes(offense_bytes))


def test_non_ascii_byte_in_a_filename_raises(offense_bytes: bytearray) -> None:
    # Slot 0 holds a custom play; its filename's first byte becomes 0xE9 (é in
    # cp1252): the field is ASCII, so the file is invalid on read.
    offense_bytes[_record_offset(offense_bytes, 0) + G95_PLAY_HEADER.size] = 0xE9
    with pytest.raises(InvalidGamePlanError) as exc:
        parse_gameplan(bytes(offense_bytes))
    assert str(exc.value) == "<buffer>: Normal slot 0: filename: Must be ASCII."


def test_nul_inside_a_stock_play_name_raises(offense_bytes: bytearray) -> None:
    # The last record is the Stop Clock stock play: a NUL inside its 8-byte
    # name, with text after it, is not a padded name.
    body = _record_offset(offense_bytes, LAST_SLOT) + G95_PLAY_HEADER.size
    offense_bytes[body + 4] = 0
    with pytest.raises(InvalidGamePlanError) as exc:
        parse_gameplan(bytes(offense_bytes))
    assert str(exc.value) == (
        "<buffer>: Special category 12 stock: play_name: Must not contain NUL."
    )


def test_invalid_stock_flag_raises(offense_bytes: bytearray) -> None:
    offense_bytes[_record_offset(offense_bytes, LAST_SLOT)] = 2
    with pytest.raises(
        InvalidGamePlanError, match=f"Invalid stock flag 0x2 at slot {LAST_SLOT}"
    ):
        parse_gameplan(bytes(offense_bytes))


def test_unrecognized_play_category_raises(offense_bytes: bytearray) -> None:
    # Slot 0 is a normal slot: its category resolves by user_category.
    offense_bytes[_record_offset(offense_bytes, 0) + 3] = 0x3F  # a code no table knows
    with pytest.raises(
        InvalidGamePlanError, match="Unrecognized play category at slot 0"
    ):
        parse_gameplan(bytes(offense_bytes))


def test_custom_play_in_clock_slot_raises(offense_bytes: bytearray) -> None:
    """A clock slot holding a custom record is a model violation, not a crash."""
    # Turn the Stop Clock stock record into a custom record (stock flag 0): its
    # body then reads as a filename up to the first NUL inside map_offset, and
    # its special_category stays 12. Bump the J95 special count so the count
    # check passes and the model gets to judge the slot.
    offense_bytes[_record_offset(offense_bytes, LAST_SLOT)] = 0
    j95_special = g95_end(offense_bytes) + J95_HEADER.size + 5  # type u8 + 2 x u16
    (declared,) = struct.unpack_from("<H", offense_bytes, j95_special)
    struct.pack_into("<H", offense_bytes, j95_special, declared + 1)
    # The reader wraps the model's ValueError: a corrupt file, named first.
    with pytest.raises(InvalidGamePlanError) as exc:
        parse_gameplan(bytes(offense_bytes))
    assert str(exc.value).startswith(
        "<buffer>: Special category 12: stock must be StockPlayRef"
    )
    assert exc.value.path == Path("<buffer>")


# ---------- errors: J95 and S98 data ----------


@pytest.mark.parametrize("size", [J95_PLAN_DATA.size - 1, J95_PLAN_DATA.size + 1])
def test_invalid_j95_data_size_raises(offense_bytes: bytearray, size: int) -> None:
    struct.pack_into("<I", offense_bytes, g95_end(offense_bytes) + 4, size)
    with pytest.raises(InvalidGamePlanError, match=f"J95 data size {size}"):
        parse_gameplan(bytes(offense_bytes))


def test_invalid_profile_type_raises(offense_bytes: bytearray) -> None:
    offense_bytes[g95_end(offense_bytes) + J95_HEADER.size] = 2
    with pytest.raises(InvalidGamePlanError, match="Invalid J95 profile type 2"):
        parse_gameplan(bytes(offense_bytes))


def test_j95_count_mismatch_raises(offense_bytes: bytearray) -> None:
    j95_data = g95_end(offense_bytes) + J95_HEADER.size
    struct.pack_into("<H", offense_bytes, j95_data + 1, 9999)  # the custom count
    with pytest.raises(InvalidGamePlanError, match="J95 counts"):
        parse_gameplan(bytes(offense_bytes))


@pytest.mark.parametrize(
    "size", [len(S98_EXPECTED_DATA) - 1, len(S98_EXPECTED_DATA) + 1]
)
def test_invalid_s98_data_size_raises(offense_bytes: bytearray, size: int) -> None:
    struct.pack_into("<I", offense_bytes, s98_start(offense_bytes) + 4, size)
    with pytest.raises(InvalidGamePlanError, match=f"S98 data size {size}"):
        parse_gameplan(bytes(offense_bytes))


def test_invalid_s98_data_content_raises(offense_bytes: bytearray) -> None:
    offense_bytes[s98_start(offense_bytes) + S98_HEADER.size] = ord("X")
    with pytest.raises(InvalidGamePlanError, match=r"S98 data .* != expected"):
        parse_gameplan(bytes(offense_bytes))


@pytest.mark.parametrize(
    "pln_path, expected",
    [
        (OFFENSE_PATH, r"offense profile \(expected even\)"),
        (DEFENSE_PATH, r"defense profile \(expected odd\)"),
    ],
    ids=["offense", "defense"],
)
def test_wrong_parity_raises(pln_path: Path, expected: str) -> None:
    with pytest.raises(InvalidGamePlanError, match=f"wrong parity for {expected}"):
        parse_gameplan(pln_path.read_bytes() + b"\x00")
