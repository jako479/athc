"""In-memory data model for FbPro98 .ply play files.

Defines the types the reader produces (PlayerHeader, PlayFile) and the
canonical category-code -> category-name lookup tables for offense, defense,
and special teams.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

OFFENSIVE_CATEGORIES = {
    0x01: "Run Right",
    0x03: "Pass Short Right",
    0x05: "Run Left",
    0x07: "Pass Short Left",
    0x09: "Run Middle",
    0x0B: "Pass Short Middle",
    0x0D: "Razzle Dazzle Run",
    0x0F: "Razzle Dazzle Pass",
    0x13: "Pass Medium Right",
    0x17: "Pass Medium Left",
    0x1B: "Pass Medium Middle",
    0x23: "Pass Long Right",
    0x27: "Pass Long Left",
    0x2B: "Pass Long Middle",
    0x31: "Goal Line Run",
    0x33: "Goal Line Pass",
    0xFF: "User Specific",
}

DEFENSIVE_CATEGORIES = {
    0x00: "Run Right",
    0x02: "Pass Short",
    0x04: "Run Left",
    0x08: "Run Middle",
    0x0C: "Run Dazzle",
    0x0E: "Pass Dazzle",
    0x12: "Pass Medium",
    0x22: "Pass Long",
    0x30: "Goal Line Run",
    0x32: "Goal Line Pass",
    0xFE: "User Specific",
}

SPECIAL_TEAMS_OFFENSIVE_CATEGORIES = {
    0x01: "Field Goal/PAT",
    0x02: "Kickoff",
    0x03: "Punt",
    0x04: "Onside Kick",
    0x05: "Fake FG Run",
    0x06: "Fake FG Pass",
    0x07: "Fake Punt Run",
    0x08: "Fake Punt Pass",
    0x09: "Free Kick",
    0x0A: "Squib Kick",
}

SPECIAL_TEAMS_DEFENSIVE_CATEGORIES = {
    0x01: "Field Goal/PAT Defense",
    0x02: "Kick Return",
    0x03: "Punt Return",
    0x04: "Onside Return",
    0x05: "Fake FG Run Defense",
    0x06: "Fake FG Pass Defense",
    0x07: "Fake Punt Run Defense",
    0x08: "Fake Punt Pass Defense",
    0x09: "Free Kick Return",
    0x0A: "Squib Return",
}


@dataclass(frozen=True, slots=True)
class PlayerHeader:
    """One player's header within a .ply play file.

    Parsed from the leading bytes of each player record. See specs/ply.md
    section 2.4 for the on-disk layout.
    """

    offset: int
    """Record offset relative to 0x08 (end of the P95 header)."""

    rank: int
    """Depth-chart rank (u8 at +0x00)."""

    player_type: int
    """Record type (u8 at +0x01). Observed: 0x01 pre-snap, 0x02 after-snap,
    0x04 kicking."""

    position: int
    """Position code (u16 at +0x02). Observed: 0x20 QB, 0x12 C, 0x11 T,
    0x10 G, 0x81 TE, 0x80 WR, 0x42 HB."""


@dataclass(frozen=True, slots=True)
class PlayFile:
    """Parsed FbPro98 .ply play file.

    See specs/ply.md for the on-disk binary format these attributes correspond to.
    """

    file_path: Path
    """Path the play was read from; Path("<buffer>") when parsed from raw
    bytes with no path."""

    stream_length: int
    """P95 data-stream size in bytes (file size minus the 8-byte header)."""

    play_category: int
    """Category byte at 0x1E; bit 0 = side of ball
    (odd = offense/kicking, even = defense/receiving)."""

    special_category: int
    """Special-teams category at 0x1F; 0 = not special teams."""

    user_category: int
    """User category byte at 0x20; bits 5-0 = play category, bits 7-6 vary."""

    player_offsets: tuple[int, ...]
    """u16 player-record offsets from 0x08, in slot order:
    QB, C, LT, LG, RG, RT, TE, RWR, LWR, LHB, RHB."""

    player_headers: tuple[PlayerHeader, ...]
    """One PlayerHeader per slot, same order as player_offsets."""

    @property
    def is_offensive(self) -> bool:
        """True if this is an offensive (or kicking-side) play."""
        return self.play_category % 2 == 1

    @property
    def is_defensive(self) -> bool:
        """True if this is a defensive (or receiving-side) play."""
        return self.play_category % 2 == 0

    @property
    def is_special_teams(self) -> bool:
        """True if this is a special-teams play (any non-zero special_category)."""
        return self.special_category != 0

    @property
    def category_name(self) -> str | None:
        """Resolve this play's human-readable category name.

        Special-teams plays (special_category != 0) map via the special-teams
        offensive or defensive table by special_category. Normal plays look up
        the full user_category, falling back to the masked base
        (user_category & 0x3F, dropping the varying high bits) — so the full-byte
        User Specific marker (0xFF/0xFE) resolves and ordinary codes still match.

        Returns:
            The category name, or None if the code is unrecognized.
        """
        if self.is_special_teams:
            mapping = (
                SPECIAL_TEAMS_OFFENSIVE_CATEGORIES
                if self.is_offensive
                else SPECIAL_TEAMS_DEFENSIVE_CATEGORIES
            )
            return mapping.get(self.special_category)
        table = OFFENSIVE_CATEGORIES if self.is_offensive else DEFENSIVE_CATEGORIES
        return table.get(self.user_category, table.get(self.user_category & 0x3F))
