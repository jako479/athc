"""Tests for athc.fbpro98_play.reader.

Real golden fixtures (curated .ply files in data/) verify whole-file parsing
and structural invariants; constructed make_ply() buffers cover the error and
edge paths no real file can express.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from athc.fbpro98_play import (
    Command,
    DefensiveFront,
    InvalidPlayFileError,
    LogicBox,
    PlayerHeader,
    PlayerLogic,
    parse_play,
    read_play,
)
from athc.fbpro98_play.schema import ID_P95, PLY_HEADER
from tests.unit.fbpro98_play.conftest import build_ply, build_record

FIXTURE_DIR = Path(__file__).resolve().parent / "data"


@dataclass(frozen=True, slots=True)
class FixtureExpectation:
    fixture_name: str
    stream_length: int
    play_category: int
    special_category: int
    user_category: int
    player_offsets: tuple[int, ...]
    player_headers: tuple[tuple[int, int, int], ...]


VALID_FIXTURES = [
    FixtureExpectation(
        fixture_name="AFGZoutX.ply",
        stream_length=441,
        play_category=0x9B,
        special_category=0x00,
        user_category=0xB3,
        player_offsets=(25, 73, 97, 121, 157, 185, 209, 261, 301, 353, 389),
        player_headers=(
            (1, 2, 32),
            (1, 1, 18),
            (1, 0, 17),
            (2, 0, 16),
            (1, 0, 16),
            (2, 0, 17),
            (3, 0, 128),
            (4, 0, 128),
            (2, 0, 128),
            (1, 0, 66),
            (1, 0, 128),
        ),
    ),
    FixtureExpectation(
        fixture_name="AF-KO.ply",
        stream_length=491,
        play_category=0x01,
        special_category=0x02,
        user_category=0x01,
        player_offsets=(25, 75, 115, 155, 199, 239, 283, 331, 371, 411, 451),
        player_headers=(
            (1, 4, 2048),
            (1, 0, 1025),
            (5, 0, 128),
            (1, 0, 65),
            (4, 0, 128),
            (3, 0, 512),
            (3, 0, 128),
            (3, 0, 1024),
            (6, 0, 128),
            (2, 0, 1025),
            (2, 0, 512),
        ),
    ),
    FixtureExpectation(
        fixture_name="JJ10drw3.ply",
        stream_length=389,
        play_category=0x89,
        special_category=0x00,
        user_category=0x89,
        player_offsets=(25, 49, 85, 121, 157, 193, 229, 261, 293, 325, 357),
        player_headers=(
            (1, 2, 32),
            (1, 1, 18),
            (2, 0, 17),
            (1, 0, 16),
            (2, 0, 16),
            (1, 0, 17),
            (1, 0, 129),
            (3, 0, 128),
            (1, 0, 128),
            (2, 0, 129),
            (2, 0, 128),
        ),
    ),
    FixtureExpectation(
        fixture_name="JJ43rlZB.ply",
        stream_length=379,
        play_category=0x88,
        special_category=0x00,
        user_category=0x84,
        player_offsets=(25, 59, 87, 115, 143, 177, 215, 249, 277, 311, 345),
        player_headers=(
            (3, 0, 512),
            (2, 0, 257),
            (1, 0, 257),
            (2, 0, 258),
            (2, 0, 512),
            (1, 0, 512),
            (2, 0, 1025),
            (1, 0, 258),
            (1, 0, 1024),
            (1, 0, 1025),
            (2, 0, 1024),
        ),
    ),
    FixtureExpectation(
        fixture_name="JJ7XWagR.ply",
        stream_length=517,
        play_category=0xA3,
        special_category=0x00,
        user_category=0x97,
        player_offsets=(25, 97, 121, 149, 177, 205, 241, 275, 333, 387, 469),
        player_headers=(
            (1, 2, 32),
            (1, 1, 18),
            (2, 0, 17),
            (1, 0, 16),
            (2, 0, 16),
            (1, 0, 17),
            (2, 0, 128),
            (1, 0, 128),
            (4, 0, 128),
            (3, 0, 128),
            (1, 0, 129),
        ),
    ),
    FixtureExpectation(
        fixture_name="KCC33rmA.ply",
        stream_length=461,
        play_category=0x82,
        special_category=0x00,
        user_category=0x88,
        player_offsets=(25, 49, 97, 149, 197, 233, 261, 299, 335, 377, 419),
        player_headers=(
            (2, 0, 258),
            (2, 1, 512),
            (1, 0, 258),
            (3, 0, 512),
            (1, 0, 512),
            (1, 0, 257),
            (2, 0, 1025),
            (1, 0, 1025),
            (2, 0, 1024),
            (3, 0, 1024),
            (1, 0, 1024),
        ),
    ),
    FixtureExpectation(
        fixture_name="MN22PLz.ply",
        stream_length=599,
        play_category=0x92,
        special_category=0x00,
        user_category=0xA2,
        player_offsets=(25, 87, 135, 191, 239, 301, 357, 413, 461, 499, 555),
        player_headers=(
            (1, 0, 258),
            (1, 0, 1024),
            (1, 0, 1025),
            (6, 0, 1024),
            (2, 0, 258),
            (5, 0, 1024),
            (2, 0, 512),
            (3, 0, 1024),
            (1, 0, 512),
            (4, 0, 1024),
            (2, 0, 1024),
        ),
    ),
    FixtureExpectation(
        fixture_name="NY26RM00.ply",
        stream_length=473,
        play_category=0x89,
        special_category=0x00,
        user_category=0x89,
        player_offsets=(25, 73, 109, 133, 157, 193, 229, 271, 331, 367, 415),
        player_headers=(
            (1, 2, 32),
            (1, 1, 18),
            (1, 0, 17),
            (2, 0, 16),
            (1, 0, 16),
            (2, 0, 17),
            (4, 0, 128),
            (1, 0, 129),
            (2, 0, 129),
            (1, 0, 65),
            (1, 0, 66),
        ),
    ),
    FixtureExpectation(
        fixture_name="SF1YemTy.ply",
        stream_length=381,
        play_category=0xB3,
        special_category=0x00,
        user_category=0x87,
        player_offsets=(25, 59, 83, 107, 135, 163, 187, 233, 267, 301, 347),
        player_headers=(
            (1, 2, 32),
            (1, 1, 18),
            (1, 0, 17),
            (1, 0, 16),
            (2, 0, 16),
            (2, 0, 17),
            (6, 0, 128),
            (5, 0, 128),
            (1, 0, 129),
            (3, 0, 128),
            (4, 0, 128),
        ),
    ),
]


@pytest.mark.parametrize("expected", VALID_FIXTURES, ids=lambda e: e.fixture_name)
def test_reads_real_fixture_structure(expected: FixtureExpectation) -> None:
    path = FIXTURE_DIR / expected.fixture_name
    play = read_play(path)

    assert play.file_path == path
    assert play.stream_length == expected.stream_length
    assert play.play_category == expected.play_category
    assert play.special_category == expected.special_category
    assert play.user_category == expected.user_category
    assert play.player_offsets == expected.player_offsets
    assert play.player_headers == tuple(
        PlayerHeader(offset=offset, rank=rank, player_type=ptype, position=position)
        for offset, (rank, ptype, position) in zip(
            expected.player_offsets, expected.player_headers, strict=True
        )
    )


@pytest.mark.parametrize("expected", VALID_FIXTURES, ids=lambda e: e.fixture_name)
def test_real_fixture_invariants(expected: FixtureExpectation) -> None:
    path = FIXTURE_DIR / expected.fixture_name
    data = path.read_bytes()
    play = read_play(path)

    assert len(data) == 8 + play.stream_length
    assert len(play.player_offsets) == 11
    assert play.player_offsets[0] == 25
    assert tuple(sorted(play.player_offsets)) == play.player_offsets
    assert all(offset > 0 for offset in play.player_offsets)
    assert all(8 + header.offset + 4 <= len(data) for header in play.player_headers)


def test_offensive_special_category_name() -> None:
    play = read_play(FIXTURE_DIR / "AF-KO.ply")
    assert play.is_special and play.is_offensive
    assert play.category_name == "Kickoff"


def test_defensive_special_category_name() -> None:
    play = read_play(FIXTURE_DIR / "BCFGPATD.ply")
    assert play.is_special and play.is_defensive
    assert play.category_name == "Field Goal/PAT Defense"


def test_offensive_normal_category_name() -> None:
    play = read_play(FIXTURE_DIR / "AFGZoutX.ply")
    assert not play.is_special and play.is_offensive
    assert play.category_name == "Goal Line Pass"


def test_defensive_normal_category_name() -> None:
    play = read_play(FIXTURE_DIR / "KCC33rmA.ply")
    assert not play.is_special and play.is_defensive
    assert play.category_name == "Run Middle"


@pytest.mark.parametrize(
    ("fixture_name", "timed", "rollout", "qb_run"),
    [
        ("SF1YemTy.ply", True, False, False),  # QB stays inside the tackles
        ("JJ7XWagR.ply", False, True, False),  # QB 632 units outside a tackle
        ("AFGZoutX.ply", False, False, False),  # Check receivers from the pocket
        ("JJ10drw3.ply", False, False, True),  # QB run
        ("NY26RM00.ply", False, False, False),  # handoff
    ],
)
def test_offensive_attributes_of_real_plays(
    fixture_name: str, timed: bool, rollout: bool, qb_run: bool
) -> None:
    play = read_play(FIXTURE_DIR / fixture_name)
    assert (play.is_timed_pass, play.is_rollout(100), play.is_qb_run) == (
        timed,
        rollout,
        qb_run,
    )
    assert play.defensive_front is None


@pytest.mark.parametrize(
    ("fixture_name", "front"),
    [
        ("MN22PLz.ply", DefensiveFront.TWO_DL),
        ("KCC33rmA.ply", DefensiveFront.THREE_FOUR),
        ("JJ43rlZB.ply", DefensiveFront.FOUR_THREE),
        ("BCFGPATD.ply", None),  # FG/PAT defense: special plays have no front
    ],
)
def test_defensive_front_of_real_plays(
    fixture_name: str, front: DefensiveFront | None
) -> None:
    play = read_play(FIXTURE_DIR / fixture_name)
    assert play.defensive_front is front
    assert not (play.is_timed_pass or play.is_qb_run or play.is_rollout(100))


INVALID_PLAY = r"The play file is invalid or corrupted\."


def test_rejects_known_invalid_fixture() -> None:
    path = FIXTURE_DIR / "PS7Xmids.ply"
    with pytest.raises(InvalidPlayFileError) as exc:
        read_play(path)
    assert str(exc.value) == f"{path}: The play file is invalid or corrupted."


def test_parses_minimal_valid_buffer(make_ply) -> None:
    # Each minimal record is its 4-byte header plus two empty box lists.
    play = parse_play(make_ply())
    assert play.stream_length == 113
    assert play.player_offsets == (25, 33, 41, 49, 57, 65, 73, 81, 89, 97, 105)
    assert len(play.player_headers) == 11
    assert play.player_headers[0] == PlayerHeader(
        offset=25, rank=1, player_type=1, position=0x20
    )
    assert play.player_logic == (PlayerLogic(),) * 11


def test_decodes_player_logic() -> None:
    """SF1YemTy's QB record (0x0021-0x0042), byte for byte: one pre-snap box at
    his starting spot, then one box at the snap holding a Timed pass and two
    other commands."""
    qb = read_play(FIXTURE_DIR / "SF1YemTy.ply").player_logic[0]
    assert qb == PlayerLogic(
        pre_snap=(LogicBox(20, -500, ()),),
        after_snap=(
            LogicBox(
                20,
                -500,
                (
                    Command(0x06, (0,)),
                    Command(0x05, (602, 830)),
                    Command(0x07, (1,)),
                ),
            ),
        ),
    )


@pytest.mark.parametrize("expected", VALID_FIXTURES, ids=lambda e: e.fixture_name)
def test_every_fixture_player_has_logic(expected: FixtureExpectation) -> None:
    """Every real player has a spot at the snap: an after-snap box."""
    play = read_play(FIXTURE_DIR / expected.fixture_name)
    assert len(play.player_logic) == 11
    assert all(logic.after_snap for logic in play.player_logic)


QB_LOGIC = PlayerLogic(
    pre_snap=(LogicBox(-11, -210, ()),),
    after_snap=(
        LogicBox(-11, -210, (Command(0x02, (-11, -380)),)),
        LogicBox(-11, -380, (Command(0x06, (5,)), Command(0x2D, ()))),
    ),
)


QB_RECORD = build_record(
    0x20, pre_snap=QB_LOGIC.pre_snap, after_snap=QB_LOGIC.after_snap
)


def _play_with_qb(qb_record: bytes) -> bytes:
    return build_ply(player_records=[qb_record, *[build_record(0x12)] * 10])


def test_decodes_built_logic() -> None:
    """Boxes in order, each command with its own argument count (two, one, none)."""
    play = parse_play(_play_with_qb(QB_RECORD))
    assert play.player_logic[0] == QB_LOGIC
    assert play.player_logic[1] == PlayerLogic()


def test_bytes_after_the_logic_are_ignored() -> None:
    play = parse_play(_play_with_qb(QB_RECORD + b"\x00\x00"))
    assert play.player_logic[0] == QB_LOGIC


@pytest.mark.parametrize(
    "record",
    [
        QB_RECORD[:-1],  # the last command one byte short
        build_record(0x20)[:-2],  # no after-snap list
        build_record(0x20)[:4],  # header only
    ],
    ids=["one-byte-short", "no-after-snap-list", "header-only"],
)
def test_rejects_truncated_player_record(record: bytes) -> None:
    with pytest.raises(InvalidPlayFileError, match=INVALID_PLAY):
        parse_play(_play_with_qb(record))


def test_rejects_box_count_past_the_record() -> None:
    """A box count one higher than the record holds runs into the next record."""
    data = bytearray((FIXTURE_DIR / "SF1YemTy.ply").read_bytes())
    data[0x21 + 4] += 1  # the QB's pre-snap box count
    with pytest.raises(InvalidPlayFileError, match=INVALID_PLAY):
        parse_play(bytes(data))


def test_default_path_sentinel(make_ply) -> None:
    assert parse_play(make_ply()).file_path == Path("<buffer>")


def test_explicit_path(make_ply) -> None:
    assert parse_play(make_ply(), "plays/x.ply").file_path == Path("plays/x.ply")


def test_read_play_accepts_str_and_pathlike(make_ply, tmp_path) -> None:
    path = tmp_path / "play.ply"
    path.write_bytes(make_ply())
    assert read_play(str(path)).file_path == Path(str(path))
    assert read_play(path).file_path == path


def test_read_play_rejects_unknown_category(make_ply, tmp_path) -> None:
    path = tmp_path / "weird.ply"
    path.write_bytes(make_ply(user_category=0x3F))  # 0x3F is not a known category
    with pytest.raises(
        InvalidPlayFileError, match=r"weird\.ply: Unrecognized play category"
    ) as exc:
        read_play(path)
    assert exc.value.path == path


@pytest.mark.parametrize("buffer", [b"", b"P95", b"P95:abc"])
def test_rejects_short_header(buffer: bytes) -> None:
    with pytest.raises(InvalidPlayFileError, match=INVALID_PLAY):
        parse_play(buffer)


def test_rejects_bad_block_id(make_ply) -> None:
    with pytest.raises(InvalidPlayFileError, match="Invalid header 'XXXX' at 0x0"):
        parse_play(make_ply(block_id=b"XXXX"))


def test_bad_block_id_non_ascii_decodes(make_ply) -> None:
    with pytest.raises(InvalidPlayFileError, match="Invalid header"):
        parse_play(make_ply(block_id=b"\xff\xff\xff\xff"))


@pytest.mark.parametrize("declared", [999, 10])
def test_rejects_size_mismatch(make_ply, declared: int) -> None:
    with pytest.raises(InvalidPlayFileError, match=INVALID_PLAY):
        parse_play(make_ply(stream_length=declared))


def test_rejects_missing_metadata() -> None:
    # valid id, size field matches the length, but too short to hold metadata
    buffer = PLY_HEADER.pack(ID_P95, 20) + b"\x00" * 20
    with pytest.raises(InvalidPlayFileError, match=INVALID_PLAY):
        parse_play(buffer)


def test_rejects_offset_past_eof(make_ply) -> None:
    offsets = (25, 33, 41, 49, 57, 65, 73, 81, 89, 97, 9999)  # last points past EOF
    with pytest.raises(InvalidPlayFileError, match=INVALID_PLAY):
        parse_play(make_ply(player_offsets=offsets))


def test_read_play_missing_file(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        read_play(tmp_path / "does-not-exist.ply")


def test_zero_offset_is_rejected(make_ply) -> None:
    """Offset 0 puts the first record on top of the offsets table: its header
    reads, but the box counts it then reads run past the record."""
    offsets = (0, *(25 + 8 * i for i in range(1, 11)))
    with pytest.raises(InvalidPlayFileError, match=INVALID_PLAY):
        parse_play(make_ply(player_offsets=offsets))
