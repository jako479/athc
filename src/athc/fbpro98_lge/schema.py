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

# Offsets into the unmasked roster bytes, after the clear team number (u16).
ROSTER_TEAM_SIZE = 2
ROSTER_SLOTS = 63
# The slots by status, in slot order, as the game's roster screen groups them.
ROSTER_ASSIGNED_SLOTS = 34
ROSTER_OPEN_ACTIVE_SLOTS = 12
ROSTER_OPEN_INACTIVE_SLOTS = 7
ROSTER_INJURED_RESERVE_SLOTS = 10
ROSTER_PLAYERS_OFFSET = 0x00
ROSTER_PLAYERS = Struct(f"<{ROSTER_SLOTS}H")  # player ids, 0 = empty slot
ROSTER_NUMBERS_OFFSET = 0x7E  # one jersey number per slot
ROSTER_PERMUTATION_OFFSET = 0xBD
ROSTER_PERMUTATION_SIZE = 10
ROSTER_CAMP_OFFSET = 0xC7
ROSTER_CAMP_GROUPS = ("QB", "RB", "REC", "OL", "DL", "LB", "DB", "P/K")  # one row each
ROSTER_CAMP_ROWS = len(ROSTER_CAMP_GROUPS)
ROSTER_CAMP_RATINGS = (
    "AC",
    "AG",
    "DI",
    "EN",
    "HA",
    "IN",
    "SP",
    "ST",
)  # a row's columns
ROSTER_CAMP_ROW = Struct(f"{len(ROSTER_CAMP_RATINGS)}B")  # percentages
ROSTER_UNKNOWN_OFFSET = 0x107
ROSTER_UNKNOWN_SIZE = 60

# Team byte i is XORed with (MASK_FACTOR * team number + i) & 0xFF.
MASK_FACTOR = 0x69

# S03: a header, then per week a game count and that many games.
SCHEDULE_HEADER_SIZE = 3
SCHEDULE_REGULAR_WEEKS_OFFSET = 0x00
SCHEDULE_PLAYOFF_ROUNDS_OFFSET = 0x01
GAME = Struct("6B")  # home, home score, away, away score, overtime, status
GAME_PLAYED = 0
