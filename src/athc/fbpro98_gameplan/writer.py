"""Serialize GamePlan objects back to FbPro98 .pln file bytes.

Builds the three on-disk blocks (G95 plays + offsets, J95 plan metadata,
S98 stock-map filename) and pads the file to the parity expected by the
gameplan's profile type (offense even, defense odd).
"""

from __future__ import annotations

from os import PathLike

from athc.fbpro98_gameplan.model import (
    CustomPlayRef,
    GamePlan,
    PlayRef,
    ProfileType,
    StockPlayRef,
)
from athc.fbpro98_gameplan.schema import (
    G95_AUDIBLE,
    G95_HEADER,
    G95_OFFSETS_TABLE,
    G95_PLAY_HEADER,
    G95_STOCK_PLAY_BODY,
    ID_G95,
    ID_J95,
    ID_S98,
    J95_HEADER,
    J95_PLAN_DATA,
    S98_HEADER,
)
from athc.fileio import atomic_write

StrPath = str | PathLike[str]


def write_gameplan(gameplan: GamePlan, path: StrPath) -> None:
    """Serialize a GamePlan and write it to a .pln file.

    Args:
        gameplan: The GamePlan to serialize; `validate()` runs first.
        path: Filesystem path to write the .pln file to. Any existing file at
            this path is replaced whole: the bytes go to a temp file beside
            it, swapped in once complete.

    Raises:
        ValueError: If the GamePlan fails `validate()`; nothing is written.
        OSError: If the file cannot be written (subclasses include
            PermissionError, IsADirectoryError, FileNotFoundError for the
            parent directory), naming `path`.
    """
    atomic_write(path, build_gameplan(gameplan))


def build_gameplan(gameplan: GamePlan) -> bytes:
    """Serialize a GamePlan to .pln file bytes.

    Runs `validate()` first, then builds the three on-disk blocks (G95 plays +
    offsets, J95 plan metadata, S98 stock-map filename) and pads the file to
    the parity expected by the gameplan's profile type (offense even, defense
    odd).

    Args:
        gameplan: The GamePlan to serialize.

    Returns:
        Bytes of the resulting .pln file, ready to write.

    Raises:
        ValueError: If the GamePlan fails `validate()`.
    """
    gameplan.validate()
    output = _build_g95(gameplan) + _build_j95(gameplan) + _build_s98(gameplan)
    needs_odd = gameplan.profile_type == ProfileType.DEFENSE
    if len(output) % 2 != needs_odd:
        output += b"\x00"
    return output


def _special_records(gameplan: GamePlan) -> list[PlayRef | None]:
    """The 22 special offsets in file order: (custom, stock) for each category
    with a custom slot, then the stock play of each clock category."""
    records: list[PlayRef | None] = []
    for category, slot in enumerate(gameplan.special_plays, start=1):
        if category in GamePlan.CUSTOM_SPECIAL_CATEGORIES:
            records.append(slot.custom)
        records.append(slot.stock)
    return records


def _build_g95(gameplan: GamePlan) -> bytes:
    all_plays: list[PlayRef | None] = [
        *gameplan.normal_plays,
        *_special_records(gameplan),
    ]
    offsets_table_start = G95_HEADER.size + G95_AUDIBLE.size
    records_base = offsets_table_start + G95_OFFSETS_TABLE.size

    offsets = [0] * GamePlan.NUMBER_PLAY_SLOTS
    records = bytearray()
    for slot, play in enumerate(all_plays):
        if play is None:
            continue
        offsets[slot] = records_base + len(records) - offsets_table_start
        records += _build_play(play)

    g95_data_size = G95_AUDIBLE.size + G95_OFFSETS_TABLE.size + len(records)
    return (
        G95_HEADER.pack(ID_G95, g95_data_size)
        + G95_AUDIBLE.pack(gameplan.audible)
        + G95_OFFSETS_TABLE.pack(*offsets)
        + bytes(records)
    )


def _build_play(play: PlayRef) -> bytes:
    header = G95_PLAY_HEADER.pack(
        0 if isinstance(play, CustomPlayRef) else 1,
        play.play_category,
        play.special_category,
        play.user_category,
    )
    if isinstance(play, CustomPlayRef):
        return header + play.filename.encode("ascii") + b"\x00"
    # validate() keeps the name to 8 ASCII characters; the pack pads it.
    return header + G95_STOCK_PLAY_BODY.pack(
        play.play_name.encode("ascii"), play.map_offset, play.map_size
    )


def _build_j95(gameplan: GamePlan) -> bytes:
    num_custom = sum(1 for p in gameplan.normal_plays if isinstance(p, CustomPlayRef))
    num_stock = sum(1 for p in gameplan.normal_plays if isinstance(p, StockPlayRef))
    num_special = sum(1 for s in gameplan.special_plays if s.custom is not None)
    return J95_HEADER.pack(ID_J95, J95_PLAN_DATA.size) + J95_PLAN_DATA.pack(
        gameplan.profile_type, num_custom, num_stock, num_special
    )


def _build_s98(gameplan: GamePlan) -> bytes:
    data = gameplan.map_filename.encode("ascii") + b"\x00"
    return S98_HEADER.pack(ID_S98, len(data)) + data
