"""FbPro98 WinLogStats PDB binary format.

ctypes structures for parsing .pdb files: per-team per-play stats (PLAY_DATA),
down-and-distance tendencies (TENDENCY_DATA / DOWN_DATA), and the wrapper class
(PDB) that loads and normalizes the file. See specs/pdb.md for the byte layout.
"""

from __future__ import annotations

import ctypes
import logging
from enum import IntEnum
from pathlib import Path
from typing import ClassVar

logger = logging.getLogger(__name__)

# WinLogStats records a few plays under the wrong name; rewrite on load.
RENAMED_PLAYS = {
    "WR47PT01": "WR27PT01",
    "WR48PT01": "WR28PT01",
}


class PLAY_DATA(ctypes.LittleEndianStructure):
    """One per-team per-play stats record from the PDB file.

    Counts plays, yards, completions, fumbles, interceptions, sacks, TDs, and
    yards-allowed totals for a single (team, play) pair. Supports `+=` to merge
    two records (combine duplicates and build Total Stats across teams).
    """

    class PLAY_TYPE(IntEnum):
        RUN = 0
        PASS = 1
        SPECIAL = 2
        DEFENSE = 3
        ONSIDE = 5

    # Annotations mirror _fields_ so type checkers see the ctypes-generated attrs.
    play_type: PLAY_TYPE
    team_name: bytes
    play_name: bytes
    total_yards: int
    play_count: int
    completions: int
    sacks: int
    fumbles: int
    interceptions: int
    touchdowns_offense: int
    touchdowns_defense: int
    unknown1: int
    unknown2: int
    points_scored: int
    run_plays_against: int
    pass_plays_against: int
    rush_yards_allowed: int
    pass_yards_allowed: int

    _fields_: ClassVar = [
        ("play_type", ctypes.c_uint32),
        ("team_name", ctypes.c_char * 64),
        ("play_name", ctypes.c_char * 128),
        ("total_yards", ctypes.c_int32),
        # Inaccurate for defensive plays; appears to include special-teams snaps.
        ("play_count", ctypes.c_uint32),
        ("completions", ctypes.c_uint32),
        ("sacks", ctypes.c_uint32),
        ("fumbles", ctypes.c_uint32),
        ("interceptions", ctypes.c_uint32),
        ("touchdowns_offense", ctypes.c_uint32),
        ("touchdowns_defense", ctypes.c_uint32),
        ("unknown1", ctypes.c_int32),
        ("unknown2", ctypes.c_int32),
        ("points_scored", ctypes.c_uint32),
        ("run_plays_against", ctypes.c_uint32),
        ("pass_plays_against", ctypes.c_uint32),
        ("rush_yards_allowed", ctypes.c_int32),
        ("pass_yards_allowed", ctypes.c_int32),
    ]

    def is_valid(self) -> bool:
        return (
            self.play_type in tuple(self.PLAY_TYPE)
            and len(self.team_name) > 0
            and len(self.play_name) > 0
        )

    def __iadd__(self, other: PLAY_DATA) -> PLAY_DATA:
        self.total_yards += other.total_yards
        self.play_count += other.play_count
        self.completions += other.completions
        self.sacks += other.sacks
        self.fumbles += other.fumbles
        self.interceptions += other.interceptions
        self.touchdowns_offense += other.touchdowns_offense
        self.touchdowns_defense += other.touchdowns_defense
        self.unknown1 += other.unknown1
        self.unknown2 += other.unknown2
        self.points_scored += other.points_scored
        self.run_plays_against += other.run_plays_against
        self.pass_plays_against += other.pass_plays_against
        self.rush_yards_allowed += other.rush_yards_allowed
        self.pass_yards_allowed += other.pass_yards_allowed
        return self


class DOWN_DATA(ctypes.LittleEndianStructure):
    """Play counts split by down (1st/2nd/3rd/4th). Building block for TENDENCY_DATA."""

    _fields_: ClassVar = [
        ("first_down", ctypes.c_uint32),
        ("second_down", ctypes.c_uint32),
        ("third_down", ctypes.c_uint32),
        ("fourth_down", ctypes.c_uint32),
    ]


class TENDENCY_DATA(ctypes.LittleEndianStructure):
    """Run/pass tendencies by down and yards-to-go bucket (0-1, 2-5, 6-10, 10+)."""

    _fields_: ClassVar = [
        ("team_name", ctypes.c_char * 64),
        ("run_zero_to_one", DOWN_DATA),
        ("pass_zero_to_one", DOWN_DATA),
        ("run_two_to_five", DOWN_DATA),
        ("pass_two_to_five", DOWN_DATA),
        ("run_six_to_ten", DOWN_DATA),
        ("pass_six_to_ten", DOWN_DATA),
        ("run_ten_plus", DOWN_DATA),
        ("pass_ten_plus", DOWN_DATA),
    ]

    def is_valid(self) -> bool:
        return len(self.team_name) > 0


class InvalidPDBError(ValueError):
    """Raised when a `.pdb` file has a structurally invalid record."""


class PDB:
    """Loads a .pdb; exposes plays (by play_type and (team, play)) and tendencies."""

    class DATA_TYPE(IntEnum):
        PLAY = 0
        TENDENCY = 1

    def __init__(self, filename: str) -> None:
        """Parse the PDB file.

        Populates `self.plays` (PLAY_TYPE → {(team, play): PLAY_DATA}) and
        `self.tendencies` (list, sorted by team). Duplicate (team, play) records
        merge via `+=`; names in RENAMED_PLAYS are rewritten. Raises
        InvalidPDBError on a bad record-type byte.
        """
        self.filename = filename
        self.plays: dict[PLAY_DATA.PLAY_TYPE, dict[tuple[str, str], PLAY_DATA]] = {
            play_type: {} for play_type in PLAY_DATA.PLAY_TYPE
        }
        self.tendencies: list[TENDENCY_DATA] = []
        file_path = Path(filename)

        with open(file_path, "rb") as pdb:
            while True:
                data = pdb.read(1)
                if not data:
                    self.tendencies.sort(key=lambda x: x.team_name)
                    break
                data_type = int.from_bytes(data, byteorder="little")
                if (
                    data_type < self.DATA_TYPE.PLAY
                    or data_type > self.DATA_TYPE.TENDENCY
                ):
                    raise InvalidPDBError(
                        f"invalid data type {data!r} "
                        f"at {pdb.tell() - 1:#x} in {file_path}"
                    )
                if data_type == self.DATA_TYPE.PLAY:
                    self._read_play(pdb)
                else:
                    self._read_tendency(pdb)

    def _read_play(self, pdb) -> None:
        play_in_pdb = PLAY_DATA.from_buffer_copy(pdb.read(ctypes.sizeof(PLAY_DATA)))
        if not play_in_pdb.is_valid():
            logger.warning(
                "Skipping invalid play data at %#x",
                pdb.tell() - ctypes.sizeof(PLAY_DATA),
            )
            return
        play_name = play_in_pdb.play_name.decode("ASCII")
        if play_name in ("RUNCLOCK", "STOPCLOK"):
            return
        team_name = play_in_pdb.team_name.decode("ASCII")
        if play_name in RENAMED_PLAYS:
            play_name = RENAMED_PLAYS[play_name]
            play_in_pdb.play_name = play_name.encode("ASCII")
        play_type = PLAY_DATA.PLAY_TYPE(play_in_pdb.play_type)
        play_key = (team_name, play_name)
        if play_key in self.plays[play_type]:
            play_in_pdb += self.plays[play_type][play_key]
        self.plays[play_type][play_key] = play_in_pdb

    def _read_tendency(self, pdb) -> None:
        tendency = TENDENCY_DATA.from_buffer_copy(
            pdb.read(ctypes.sizeof(TENDENCY_DATA))
        )
        if tendency.is_valid():
            self.tendencies.append(tendency)
        else:
            logger.warning(
                "Skipping invalid tendency data at %#x",
                pdb.tell() - ctypes.sizeof(TENDENCY_DATA),
            )

    def convert_invalid_play_data(self, play_pool) -> None:
        """Reclassify offensive plays the engine logged under the wrong play_type.

        FbPro98's stat collector sometimes records a pass under PLAY_TYPE.RUN (or
        vice versa) — e.g. a sacked QB on a timed pass shows up in run stats. This
        walks RUN/PASS plays, looks up the play in `play_pool`, and moves the
        record to the correct bucket when the pool's run/pass class disagrees.
        Stats are reattributed: yards lost on a misclassified run become sacks;
        misclassified pass interceptions fold back into run fumbles.
        """
        swap = {
            PLAY_DATA.PLAY_TYPE.RUN: PLAY_DATA.PLAY_TYPE.PASS,
            PLAY_DATA.PLAY_TYPE.PASS: PLAY_DATA.PLAY_TYPE.RUN,
        }
        for original_type in (PLAY_DATA.PLAY_TYPE.RUN, PLAY_DATA.PLAY_TYPE.PASS):
            for play_key in list(self.plays[original_type].keys()):
                record = play_pool.find_by_name(play_key[1])
                if record is None or not record.play_file.is_offensive:
                    continue
                category = record.category
                mismatched = (
                    original_type == PLAY_DATA.PLAY_TYPE.RUN and category.is_pass
                ) or (original_type == PLAY_DATA.PLAY_TYPE.PASS and category.is_run)
                if mismatched:
                    self._move_play(play_key, original_type, swap[original_type])

    def _move_play(
        self,
        play_key: tuple[str, str],
        original_type: PLAY_DATA.PLAY_TYPE,
        new_type: PLAY_DATA.PLAY_TYPE,
    ) -> None:
        original_play = self.plays[original_type][play_key]
        original_count = int(original_play.play_count)
        if play_key in self.plays[new_type]:
            new_play = self.plays[new_type][play_key]
        else:
            new_play = PLAY_DATA()
            new_play.play_type = new_type
            new_play.team_name = original_play.team_name
            new_play.play_name = original_play.play_name
        new_play.total_yards += original_play.total_yards
        new_play.play_count += original_play.play_count
        if new_type == PLAY_DATA.PLAY_TYPE.PASS and original_play.total_yards < 0:
            if original_play.total_yards <= -original_count:
                new_play.sacks += original_count
            else:
                new_play.sacks += round(original_count * (2 / 3))
        if new_type == PLAY_DATA.PLAY_TYPE.RUN:
            new_play.fumbles += original_play.fumbles + original_play.interceptions
        else:
            new_play.fumbles += original_play.fumbles
            new_play.interceptions += original_play.interceptions
        new_play.touchdowns_offense += original_play.touchdowns_offense
        new_play.touchdowns_defense += original_play.touchdowns_defense
        new_play.unknown1 += original_play.unknown1
        new_play.unknown2 += original_play.unknown2
        new_play.points_scored += original_play.points_scored
        self.plays[new_type][play_key] = new_play
        self.plays[original_type].pop(play_key)
