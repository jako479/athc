"""Serialize Profile objects back to FbPro98 .prf file bytes.

Builds the two on-disk blocks (F95 coaching profile data, I95 metadata) and
appends the NUL trailer required for the profile's type (1 byte offense, 2
bytes defense). Never emits embedded game-plan blocks; never emits the stock
on-disk layout — both are rejected at the reader and unreachable through
Profile.
"""

from __future__ import annotations

from os import PathLike

from athc.fbpro98_profile.model import Profile, ProfileType
from athc.fbpro98_profile.schema import (
    F95_CATEGORY_WEIGHTS,
    F95_DATA_SIZE,
    F95_FIELD_GOAL_RANGE,
    F95_HEADER,
    F95_SUBSTITUTIONS,
    F95_USE_AUDIBLES,
    I95_DATA,
    I95_DATA_SIZE,
    I95_HEADER,
    ID_F95,
    ID_I95,
    STOP_CLOCK_BIT,
    TRAILER_NUL,
)
from athc.fileio import atomic_write

StrPath = str | PathLike[str]


def write_profile(profile: Profile, path: StrPath) -> None:
    """Serialize a Profile and write it to a .prf file.

    Args:
        profile: The Profile to serialize; `validate()` runs first.
        path: Filesystem path to write the .prf file to. Any existing file at
            this path is replaced whole: the bytes go to a temp file beside
            it, swapped in once complete.

    Raises:
        ValueError: If the Profile fails `validate()`; nothing is written.
        OSError: If the file cannot be written (subclasses include
            PermissionError, IsADirectoryError, FileNotFoundError for the
            parent directory), naming `path`.
    """
    atomic_write(path, build_profile(profile))


def build_profile(profile: Profile) -> bytes:
    """Serialize a Profile to .prf file bytes.

    Runs `validate()` first, then builds the F95 and I95 blocks and appends
    the NUL trailer for the profile's type (1 byte for offense → even total
    size, 2 bytes for defense → odd total size).

    Args:
        profile: The Profile to serialize.

    Returns:
        Bytes of the resulting .prf file, ready to write.

    Raises:
        ValueError: If the Profile fails `validate()`.
    """
    profile.validate()
    return _build_f95(profile) + _build_i95(profile) + _build_trailer(profile)


def _build_f95(profile: Profile) -> bytes:
    data = bytearray()

    sub_values: list[int] = []
    for _, pair in profile.substitutions.pairs():
        sub_values.append(pair.out_percent)
        sub_values.append(pair.in_percent)
    data += F95_SUBSTITUTIONS.pack(*sub_values)

    for situation in profile.situations:
        cw = situation.category_weights
        w1 = (cw.weight1 & 0x7F) | (STOP_CLOCK_BIT if situation.stop_clock else 0)
        data += F95_CATEGORY_WEIGHTS.pack(
            cw.play_category1,
            w1,
            cw.play_category2,
            cw.weight2 & 0x7F,
            cw.play_category3,
            cw.weight3 & 0x7F,
        )

    data += F95_FIELD_GOAL_RANGE.pack(profile.field_goal_range)

    for pat in profile.pat_situations:
        cw = pat.category_weights
        data += F95_CATEGORY_WEIGHTS.pack(
            cw.play_category1,
            cw.weight1,
            cw.play_category2,
            cw.weight2,
            cw.play_category3,
            cw.weight3,
        )

    data += F95_USE_AUDIBLES.pack(1 if profile.use_audibles else 0)

    assert len(data) == F95_DATA_SIZE, f"F95 data size {len(data)} != {F95_DATA_SIZE}"
    return F95_HEADER.pack(ID_F95, F95_DATA_SIZE) + bytes(data)


def _build_i95(profile: Profile) -> bytes:
    data = I95_DATA.pack(
        int(profile.profile_type),
        0,
        profile.field_goal_range,
        0,
        1 if profile.use_audibles else 0,
    )
    assert len(data) == I95_DATA_SIZE, f"I95 data size {len(data)} != {I95_DATA_SIZE}"
    return I95_HEADER.pack(ID_I95, I95_DATA_SIZE) + data


def _build_trailer(profile: Profile) -> bytes:
    length = 1 if profile.profile_type == ProfileType.OFFENSE else 2
    return bytes([TRAILER_NUL]) * length
