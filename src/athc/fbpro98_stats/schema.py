"""Binary layout constants for the FbPro98 .dat stats file format.

Used by the reader. See docs/formats/stats.md for the full format.
"""

from struct import Struct

HEADER_SIZE = 140
RECORD_SIZE = 20

# Header fields.
FILE_END_OFFSET = 0x00  # u32: file size - 1
SLOTS_END_OFFSET = 0x08  # u32: last byte of the last slot
RECORDS_OFFSET = 0x18  # u32: records in use
RECORD_SIZE_OFFSET = 0x2C  # u16
U32 = Struct("<I")
U16 = Struct("<H")

# A record: type, id, then the values, signed as the game shows them.
RECORD = Struct("<HH8h")
VALUES_PER_RECORD = 8

# A deleted slot's first byte; no type starts with it.
DELETED_MARK = 0xFF

# Block bases: a record's type is its block's base plus its category.
PLAYER_LAST_GAME = 0
PLAYER_SEASON = 32
PLAYER_CAREER = 64
TEAM_LAST_GAME = 96
TEAM_SEASON = 130
OPPONENTS_LAST_GAME = 164
OPPONENTS_SEASON = 198

# Categories every block shares.
EXTRA_POINTS = 0
FIELD_GOALS = 1
RUSHING = 2
PASSING = 3
RECEIVING = 4
INTERCEPTIONS = 5
PUNTING = 6
PUNT_RETURNS = 7
KICK_RETURNS = 8
FUMBLES = 9
FUMBLE_RECOVERIES = 10
SACKS = 11
SAFETIES = 12
TACKLES = 13
TWO_POINT_CONVERSIONS = 17

# Categories 14-16 differ by block.
HALL_OF_FAME_POINTS = 14  # player blocks
FIRST_DOWNS = 14  # team and opponents' blocks
HONORS = 15  # player blocks; ids below
DOWNS = 15  # team and opponents' blocks
PENALTIES = 16  # player last game
HALL_OF_FAME_NOMINEE = 16  # player career; player season has no category 16
GAME_DETAILS = 16  # team and opponents' blocks

# Honor ids. Player of the Game: game number + 1, or the Player of the Week.
PLAYER_OF_THE_WEEK_ID = 99
# All-Pro team: (position + 1) + conference * 16 + pick * 256.
ALL_PRO_PICKS = 5
COACH_OF_THE_YEAR_ID = 4096
# Awards: code + (year mod 100) * 256.
AWARD_MVP = 90
AWARD_OFFENSE_FIRST_CONFERENCE = 91
AWARD_DEFENSE_FIRST_CONFERENCE = 92
AWARD_OFFENSE_SECOND_CONFERENCE = 93
AWARD_DEFENSE_SECOND_CONFERENCE = 94
AWARD_ROOKIE = 99

# Field goals: values 1-5 each pack two counts, made in the low byte.
FIELD_GOAL_RANGES = 5

# Punting value 3 is always 0 and is not read.
PUNTING_UNUSED_VALUE = 3
