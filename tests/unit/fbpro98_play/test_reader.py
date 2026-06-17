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
    InvalidPlayFileError,
    PlayerHeader,
    parse_play,
    read_play,
)
from athc.fbpro98_play.schema import ID_P95, PLY_HEADER

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


def test_offensive_special_teams_category_name() -> None:
    play = read_play(FIXTURE_DIR / "AF-KO.ply")
    assert play.is_special_teams and play.is_offensive
    assert play.category_name == "Kickoff"


def test_defensive_special_teams_category_name() -> None:
    play = read_play(FIXTURE_DIR / "BCFGPATD.ply")
    assert play.is_special_teams and play.is_defensive
    assert play.category_name == "Field Goal/PAT Defense"


def test_offensive_normal_category_name() -> None:
    play = read_play(FIXTURE_DIR / "AFGZoutX.ply")
    assert not play.is_special_teams and play.is_offensive
    assert play.category_name == "Goal Line Pass"


def test_defensive_normal_category_name() -> None:
    play = read_play(FIXTURE_DIR / "KCC33rmA.ply")
    assert not play.is_special_teams and play.is_defensive
    assert play.category_name == "Run Middle"


def test_rejects_known_invalid_fixture() -> None:
    with pytest.raises(
        InvalidPlayFileError, match="File too small to contain P95 header"
    ):
        read_play(FIXTURE_DIR / "PS7Xmids.ply")


def test_parses_minimal_valid_buffer(make_ply) -> None:
    play = parse_play(make_ply())
    assert play.stream_length == 69
    assert play.player_offsets == (25, 29, 33, 37, 41, 45, 49, 53, 57, 61, 65)
    assert len(play.player_headers) == 11
    assert play.player_headers[0] == PlayerHeader(
        offset=25, rank=1, player_type=1, position=0x20
    )


def test_default_path_sentinel(make_ply) -> None:
    assert parse_play(make_ply()).file_path == Path("<buffer>")


def test_explicit_path(make_ply) -> None:
    assert parse_play(make_ply(), "plays/x.ply").file_path == Path("plays/x.ply")


def test_read_play_accepts_str_and_pathlike(make_ply, tmp_path) -> None:
    path = tmp_path / "play.ply"
    path.write_bytes(make_ply())
    assert read_play(str(path)).file_path == Path(str(path))
    assert read_play(path).file_path == path


@pytest.mark.parametrize("buffer", [b"", b"P95", b"P95:abc"])
def test_rejects_short_header(buffer: bytes) -> None:
    with pytest.raises(InvalidPlayFileError, match="too small to contain P95 header"):
        parse_play(buffer)


def test_rejects_bad_block_id(make_ply) -> None:
    with pytest.raises(InvalidPlayFileError, match="Invalid header 'XXXX' at 0x0"):
        parse_play(make_ply(block_id=b"XXXX"))


def test_bad_block_id_non_ascii_decodes(make_ply) -> None:
    with pytest.raises(InvalidPlayFileError, match="Invalid header"):
        parse_play(make_ply(block_id=b"\xff\xff\xff\xff"))


@pytest.mark.parametrize("declared", [999, 10])
def test_rejects_size_mismatch(make_ply, declared: int) -> None:
    with pytest.raises(InvalidPlayFileError, match="does not match P95 block size"):
        parse_play(make_ply(stream_length=declared))


def test_rejects_missing_metadata() -> None:
    # valid id, size field matches the length, but too short to hold metadata
    buffer = PLY_HEADER.pack(ID_P95, 20) + b"\x00" * 20
    with pytest.raises(
        InvalidPlayFileError, match="too small to contain play metadata"
    ):
        parse_play(buffer)


def test_rejects_offset_past_eof(make_ply) -> None:
    offsets = (25, 29, 33, 37, 41, 45, 49, 53, 57, 61, 9999)  # last points past EOF
    with pytest.raises(
        InvalidPlayFileError, match="too small to contain player header"
    ):
        parse_play(make_ply(player_offsets=offsets))


def test_read_play_missing_file(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        read_play(tmp_path / "does-not-exist.ply")


def test_zero_offset_parses(make_ply) -> None:
    offsets = (0, *(25 + 4 * i for i in range(1, 11)))
    play = parse_play(make_ply(player_offsets=offsets))
    assert play.player_headers[0].offset == 0
