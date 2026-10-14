"""Binary layout constants for the FbPro98 .lge league file format.

Shared by the reader and its tests. See docs/formats/lge.md for the full format.
"""

from struct import Struct

CHUNK_HEADER = Struct("<4sI")  # tag, data size

ID_L03 = b"L03:"  # league
ID_C03 = b"C03:"  # conference
ID_D03 = b"D03:"  # division
ID_T03 = b"T03:"  # team, masked
ID_R03 = b"R03:"  # roster, masked
ID_S03 = b"S03:"  # schedule

# L03, C03 and D03 are a fixed part plus one id byte per conference, division
# or team; the count sits in the fixed part.
LEAGUE_BASE_SIZE = 89
LEAGUE_CONFERENCES_OFFSET = 0x01
CONFERENCE_BASE_SIZE = 29
CONFERENCE_DIVISIONS_OFFSET = 0x02
CONFERENCE_NAME_OFFSET = 0x04
DIVISION_BASE_SIZE = 29
DIVISION_TEAMS_OFFSET = 0x03
DIVISION_NAME_OFFSET = 0x04
NAME_SIZE = 25  # conference and division names

TEAM_CHUNK_SIZE = 171
ROSTER_CHUNK_SIZE = 325

# Offsets into the unmasked team bytes, after the clear team number.
TEAM_NAME_OFFSET = 0x36
NICKNAME_OFFSET = 0x47
TEAM_TEXT_SIZE = 17

# Team byte i is XORed with (MASK_FACTOR * team number + i) & 0xFF.
MASK_FACTOR = 0x69

# S03: a header, then per week a game count and that many games.
SCHEDULE_HEADER_SIZE = 3
SCHEDULE_REGULAR_WEEKS_OFFSET = 0x00
SCHEDULE_PLAYOFF_ROUNDS_OFFSET = 0x01
GAME = Struct("6B")  # home, home score, away, away score, overtime, status
GAME_PLAYED = 0
