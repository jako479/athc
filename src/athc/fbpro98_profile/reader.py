"""Parse FbPro98 .prf files into Profile objects. See specs/prf.md."""

from __future__ import annotations

from os import PathLike
from pathlib import Path

from athc.fbpro98_profile.model import (
    CategoryWeights,
    PatSituation,
    Profile,
    ProfileType,
    Situation,
    SubstitutionPair,
    SubstitutionSettings,
)
from athc.fbpro98_profile.schema import (
    F95_CATEGORY_WEIGHTS,
    F95_DATA_SIZE,
    F95_FIELD_GOAL_RANGE,
    F95_HEADER,
    F95_STOCK_DATA_SIZES,
    F95_SUBSTITUTIONS,
    F95_USE_AUDIBLES,
    I95_DATA,
    I95_DATA_SIZE,
    I95_HEADER,
    ID_F95,
    ID_G95,
    ID_I95,
    ID_J95,
    ID_S98,
    STOP_CLOCK_BIT,
    VALID_TRAILER_BYTES,
    WEIGHT_MASK,
)

StrPath = str | PathLike[str]


class InvalidProfileError(ValueError):
    """Raised when a `.prf` file is structurally invalid."""


class UnsupportedProfileError(ValueError):
    """Raised on a structurally valid `.prf` in an unsupported variant.

    Unsupported variants are the stock layout and profiles with embedded game
    plans. See specs/prf.md section 4.
    """


def read_profile(path: StrPath) -> Profile:
    """Read and parse a .prf coaching profile file from disk.

    Args:
        path: Filesystem path to the .prf file.

    Returns:
        Parsed Profile.

    Raises:
        InvalidProfileError: If the file is not a structurally valid .prf (bad
            block IDs, mismatched sizes, F95/I95 field disagreement, invalid
            substitution / situation / field-goal-range / use-audibles values,
            invalid trailer, or wrong file-size parity for the profile type).
        UnsupportedProfileError: If the file is structurally valid but uses an
            unsupported variant (stock layout, or has embedded game-plan
            blocks). See specs/prf.md section 4.
        OSError: If the file cannot be opened or read (subclasses include
            FileNotFoundError, PermissionError, IsADirectoryError).
    """
    file_path = Path(path)
    return parse_profile(file_path.read_bytes(), file_path)


def parse_profile(buffer: bytes, path: StrPath = "<buffer>") -> Profile:
    """Parse a .prf coaching profile from raw bytes.

    Args:
        buffer: Full contents of a .prf file.
        path: Path used only in error messages. Defaults to "<buffer>" when
            parsing data that did not come from disk.

    Returns:
        Parsed Profile.

    Raises:
        InvalidProfileError: If the buffer does not contain a valid F95+I95
            block sequence with a correct trailer. Triggered by wrong block
            IDs, mismatched sizes, F95/I95 field disagreement, invalid
            substitution / situation / field-goal-range / use-audibles values,
            invalid trailer bytes, or wrong file-size parity for the profile
            type.
        UnsupportedProfileError: If the buffer is structurally valid but uses
            an unsupported variant (stock layout, or has embedded game-plan
            blocks).
    """
    file_path = Path(path)

    (
        f95_substitutions,
        f95_paired_records,
        f95_pat_records,
        f95_fg_range,
        f95_use_audibles,
    ) = _parse_f95(buffer, file_path)
    i95_start = F95_HEADER.size + F95_DATA_SIZE
    profile_type, i95_fg_range, i95_use_audibles, num_game_plan_blocks = _parse_i95(
        buffer, i95_start, file_path
    )

    if f95_fg_range != i95_fg_range:
        raise InvalidProfileError(
            f"F95 field_goal_range ({f95_fg_range}) != I95 field_goal_range "
            f"({i95_fg_range}) in {file_path}"
        )
    if f95_use_audibles != i95_use_audibles:
        raise InvalidProfileError(
            f"F95 use_audibles ({f95_use_audibles}) != I95 use_audibles "
            f"({i95_use_audibles}) in {file_path}"
        )

    body_end = i95_start + I95_HEADER.size + I95_DATA_SIZE
    _check_unsupported_variants(buffer, body_end, num_game_plan_blocks, file_path)
    _validate_trailer(buffer, body_end, profile_type, file_path)

    # enumerate() yields 0-based array indices; the domain situation_number is 1-based.
    situations = tuple(
        Situation.from_situation_number(idx + 1, stop_clock=sc, category_weights=cw)
        for idx, (cw, sc) in enumerate(f95_paired_records)
    )
    pat_situations = tuple(
        PatSituation.from_situation_number(idx + 1, category_weights=cw)
        for idx, cw in enumerate(f95_pat_records)
    )

    return Profile(
        profile_type=profile_type,
        substitutions=f95_substitutions,
        situations=situations,
        pat_situations=pat_situations,
        field_goal_range=f95_fg_range,
        use_audibles=bool(f95_use_audibles),
    )


def _parse_f95(
    buffer: bytes, path: Path
) -> tuple[
    SubstitutionSettings,
    tuple[tuple[CategoryWeights, bool], ...],
    tuple[CategoryWeights, ...],
    int,
    int,
]:
    if len(buffer) < F95_HEADER.size + F95_DATA_SIZE:
        raise InvalidProfileError(f"File too small to contain F95 block in {path}")

    block_id, data_size = F95_HEADER.unpack_from(buffer, 0)
    if block_id != ID_F95:
        block_id_str = block_id.decode("ASCII", errors="replace")
        raise InvalidProfileError(f"Invalid header '{block_id_str}' at 0x0 in {path}")
    if data_size in F95_STOCK_DATA_SIZES:
        raise UnsupportedProfileError(
            f"Stock layout (F95 size {data_size:#x}) not supported in {path}"
        )
    if data_size != F95_DATA_SIZE:
        raise InvalidProfileError(
            f"F95 data size {data_size:#x} != expected {F95_DATA_SIZE:#x} in {path}"
        )

    offset = F95_HEADER.size
    substitutions = _parse_substitutions(buffer, offset, path)

    offset += F95_SUBSTITUTIONS.size
    paired_records = _parse_category_weights_and_stop_clock(
        buffer, offset, Profile.NUMBER_SITUATIONS, "situation", path
    )

    offset += F95_CATEGORY_WEIGHTS.size * Profile.NUMBER_SITUATIONS
    (fg_range,) = F95_FIELD_GOAL_RANGE.unpack_from(buffer, offset)
    if not Profile.FIELD_GOAL_RANGE_MIN <= fg_range <= Profile.FIELD_GOAL_RANGE_MAX:
        raise InvalidProfileError(
            f"F95 field_goal_range {fg_range} outside "
            f"[{Profile.FIELD_GOAL_RANGE_MIN}, {Profile.FIELD_GOAL_RANGE_MAX}] in "
            f"{path}"
        )

    offset += F95_FIELD_GOAL_RANGE.size
    pat_records = _parse_pat_category_weights(
        buffer, offset, Profile.NUMBER_PAT_SITUATIONS, path
    )

    offset += F95_CATEGORY_WEIGHTS.size * Profile.NUMBER_PAT_SITUATIONS
    (use_audibles,) = F95_USE_AUDIBLES.unpack_from(buffer, offset)
    if use_audibles not in (0, 1):
        raise InvalidProfileError(
            f"F95 use_audibles {use_audibles} not in {{0, 1}} in {path}"
        )

    return substitutions, paired_records, pat_records, fg_range, use_audibles


def _parse_substitutions(
    buffer: bytes, offset: int, path: Path
) -> SubstitutionSettings:
    raw = F95_SUBSTITUTIONS.unpack_from(buffer, offset)
    pairs: list[SubstitutionPair] = []
    group_names = (
        "offensive_linemen",
        "quarterbacks",
        "running_backs",
        "receivers",
        "defensive_linemen",
        "linebackers",
        "defensive_backs",
        "kickers",
    )
    for i, group in enumerate(group_names):
        out_percent = raw[i * 2]
        in_percent = raw[i * 2 + 1]
        try:
            pairs.append(
                SubstitutionPair(out_percent=out_percent, in_percent=in_percent)
            )
        except ValueError as exc:
            raise InvalidProfileError(
                f"Invalid substitution pair for {group}: {exc} in {path}"
            ) from exc
    return SubstitutionSettings(
        offensive_linemen=pairs[0],
        quarterbacks=pairs[1],
        running_backs=pairs[2],
        receivers=pairs[3],
        defensive_linemen=pairs[4],
        linebackers=pairs[5],
        defensive_backs=pairs[6],
        kickers=pairs[7],
    )


def _parse_category_weights_and_stop_clock(
    buffer: bytes, offset: int, count: int, label: str, path: Path
) -> tuple[tuple[CategoryWeights, bool], ...]:
    records: list[tuple[CategoryWeights, bool]] = []
    for index in range(count):
        record_offset = offset + index * F95_CATEGORY_WEIGHTS.size
        pc1, w1, pc2, w2, pc3, w3 = F95_CATEGORY_WEIGHTS.unpack_from(
            buffer, record_offset
        )
        stop_clock = bool(w1 & STOP_CLOCK_BIT)
        weight1 = w1 & WEIGHT_MASK
        try:
            weights = CategoryWeights(
                play_category1=pc1,
                weight1=weight1,
                play_category2=pc2,
                weight2=w2,
                play_category3=pc3,
                weight3=w3,
            )
        except ValueError as exc:
            raise InvalidProfileError(
                f"Invalid {label} record at index {index}: {exc} in {path}"
            ) from exc
        records.append((weights, stop_clock))
    return tuple(records)


def _parse_pat_category_weights(
    buffer: bytes, offset: int, count: int, path: Path
) -> tuple[CategoryWeights, ...]:
    records: list[CategoryWeights] = []
    for index in range(count):
        record_offset = offset + index * F95_CATEGORY_WEIGHTS.size
        pc1, w1, pc2, w2, pc3, w3 = F95_CATEGORY_WEIGHTS.unpack_from(
            buffer, record_offset
        )
        try:
            weights = CategoryWeights(
                play_category1=pc1,
                weight1=w1,
                play_category2=pc2,
                weight2=w2,
                play_category3=pc3,
                weight3=w3,
            )
        except ValueError as exc:
            raise InvalidProfileError(
                f"Invalid PAT situation record at index {index}: {exc} in {path}"
            ) from exc
        records.append(weights)
    return tuple(records)


def _parse_i95(
    buffer: bytes, i95_start: int, path: Path
) -> tuple[ProfileType, int, int, int]:
    needed = i95_start + I95_HEADER.size + I95_DATA_SIZE
    if len(buffer) < needed:
        raise InvalidProfileError(f"File too small to contain I95 block in {path}")

    block_id, data_size = I95_HEADER.unpack_from(buffer, i95_start)
    if block_id in (ID_G95, ID_J95, ID_S98):
        raise UnsupportedProfileError(
            f"Embedded game plan block '{block_id.decode('ASCII')}' before I95 not "
            f"supported in {path}"
        )
    if block_id != ID_I95:
        block_id_str = block_id.decode("ASCII", errors="replace")
        raise InvalidProfileError(
            f"Invalid header '{block_id_str}' at {i95_start:#x} in {path}"
        )
    if data_size != I95_DATA_SIZE:
        raise InvalidProfileError(
            f"I95 data size {data_size:#x} != expected {I95_DATA_SIZE:#x} in {path}"
        )

    profile_type_raw, reserved, fg_range, num_game_plan_blocks, use_audibles = (
        I95_DATA.unpack_from(buffer, i95_start + I95_HEADER.size)
    )
    if reserved != 0:
        raise InvalidProfileError(f"I95 reserved field {reserved:#x} != 0 in {path}")
    try:
        profile_type = ProfileType(profile_type_raw)
    except ValueError:
        raise InvalidProfileError(
            f"Invalid I95 profile_type {profile_type_raw} in {path}"
        ) from None
    if not Profile.FIELD_GOAL_RANGE_MIN <= fg_range <= Profile.FIELD_GOAL_RANGE_MAX:
        raise InvalidProfileError(
            f"I95 field_goal_range {fg_range} outside "
            f"[{Profile.FIELD_GOAL_RANGE_MIN}, {Profile.FIELD_GOAL_RANGE_MAX}] in "
            f"{path}"
        )
    if use_audibles not in (0, 1):
        raise InvalidProfileError(
            f"I95 use_audibles {use_audibles} not in {{0, 1}} in {path}"
        )

    return profile_type, fg_range, use_audibles, num_game_plan_blocks


def _check_unsupported_variants(
    buffer: bytes, body_end: int, num_game_plan_blocks: int, path: Path
) -> None:
    if num_game_plan_blocks != 0:
        raise UnsupportedProfileError(
            f"Embedded game plan blocks ({num_game_plan_blocks}) not supported in "
            f"{path}"
        )
    if len(buffer) >= body_end + 4:
        block_peek = bytes(buffer[body_end : body_end + 4])
        if block_peek in (ID_G95, ID_J95, ID_S98):
            raise UnsupportedProfileError(
                f"Embedded game plan block '{block_peek.decode('ASCII')}' after I95 "
                f"not supported in {path}"
            )


def _validate_trailer(
    buffer: bytes, body_end: int, profile_type: ProfileType, path: Path
) -> None:
    expected_length = 1 if profile_type == ProfileType.OFFENSE else 2
    actual_length = len(buffer) - body_end
    if actual_length != expected_length:
        raise InvalidProfileError(
            f"Trailer length {actual_length} != expected {expected_length} for "
            f"{profile_type.name} profile in {path}"
        )
    for offset in range(body_end, len(buffer)):
        byte = buffer[offset]
        if byte not in VALID_TRAILER_BYTES:
            raise InvalidProfileError(
                f"Trailer byte at {offset:#x} is {byte:#04x}; only 0x00 accepted in "
                f"{path}"
            )

    expected_parity = 0 if profile_type == ProfileType.OFFENSE else 1
    if len(buffer) % 2 != expected_parity:
        expected_word = "even" if expected_parity == 0 else "odd"
        raise InvalidProfileError(
            f"File size {len(buffer)} has wrong parity for {profile_type.name.lower()} "
            f"profile (expected {expected_word}) in {path}"
        )
