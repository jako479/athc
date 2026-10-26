"""Binary layout constants for the FbPro98 .pyr player file format.

Used by the reader; the tests build files from the spec's own literals, so the
reader tests pin these. See docs/formats/pyr.md for the full format.
"""

from struct import Struct

HEADER_SIZE = 60
RECORD_SIZE = 60
FIRST_ID = 100  # record i holds player id FIRST_ID + i
MAX_PLAYERS = 0x10000 - FIRST_ID  # ids are u16

# Header fields; every other header byte is zero.
KEY_OFFSET = 0x00  # u16
HEADER_NAME_OFFSET = 0x0F  # char[13]
HEADER_UNKNOWN_OFFSET = 0x36  # u8[UNKNOWN_SIZE], kept as read
HEADER_ZERO_FIELDS = ((0x02, 13), (0x1C, 26))  # offset, size

# Player record, decoded: id, first name, last name, potential ratings, injury
# bytes, group, position, actual ratings, years, height, weight, unknown.
RECORD = Struct("<H13s13s8B4sBB8BBBH6s")
INJURY = Struct("<HBB")  # level, injury, week
NAME_SIZE = 13
UNKNOWN_SIZE = 6

U16 = Struct("<H")
