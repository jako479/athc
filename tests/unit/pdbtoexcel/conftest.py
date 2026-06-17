"""Shared paths and builders for pdbtoexcel unit tests."""

from __future__ import annotations

from pathlib import Path

from athc.fbpro98_play import PlayFile
from athc.pdbtoexcel.pdb import PLAY_DATA, TENDENCY_DATA
from athc.playpool import (
    DefensiveFront,
    DefensivePlayRecord,
    OffensivePlayRecord,
    PassLogic,
    PlayPool,
    PlayRecord,
    SpecialTeamsPlayRecord,
)

DATA = Path(__file__).resolve().parent / "data"
REAL_PDB = DATA / "2045-2047.pdb"
PLAYS_SNAPSHOT = DATA / "2045-2047.plays.json"


def make_play_data(
    play_type: PLAY_DATA.PLAY_TYPE, team: str, name: str, **stats: int
) -> PLAY_DATA:
    play = PLAY_DATA()
    play.play_type = play_type
    play.team_name = team.encode("ASCII")
    play.play_name = name.encode("ASCII")
    for key, value in stats.items():
        setattr(play, key, value)
    return play


def write_pdb(path: Path, plays=(), tendencies=()) -> Path:
    """Write a minimal .pdb: each play prefixed with a 0 byte, each tendency with 1."""
    with open(path, "wb") as f:
        for play in plays:
            f.write(b"\x00" + bytes(play))  # data-type 0 = PLAY
        for tendency in tendencies:
            f.write(b"\x01" + bytes(tendency))  # data-type 1 = TENDENCY
    return path


def make_tendency(team: str) -> TENDENCY_DATA:
    t = TENDENCY_DATA()
    t.team_name = team.encode("ASCII")
    return t


def make_record(
    name: str,
    *,
    play_category: int = 0x01,
    user_category: int = 0x03,
    special_category: int = 0,
    pool_category: str = "",
    screen: bool = False,
    qb_draw: bool = False,
    rollout: bool = False,
    pass_logic: PassLogic | None = None,
    defensive_front: DefensiveFront | None = None,
) -> PlayRecord:
    play_file = PlayFile(
        Path(f"{name}.ply"), 0, play_category, special_category, user_category, (), ()
    )
    if special_category:
        return SpecialTeamsPlayRecord(name, play_file)
    if play_category % 2 == 1:  # odd → offense
        return OffensivePlayRecord(
            name,
            play_file,
            pool_category=pool_category,
            screen=screen,
            qb_draw=qb_draw,
            rollout=rollout,
            pass_logic=pass_logic,
        )
    return DefensivePlayRecord(
        name, play_file, pool_category=pool_category, defensive_front=defensive_front
    )


def make_pool(records) -> PlayPool:
    pool = PlayPool("root")
    for record in records:
        pool._register(record)
        if isinstance(record, OffensivePlayRecord):
            pool.offensive_plays.append(record)
        elif isinstance(record, DefensivePlayRecord):
            pool.defensive_plays.append(record)
        elif isinstance(record, SpecialTeamsPlayRecord):
            pool.special_teams_plays.append(record)
    return pool
