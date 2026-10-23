"""Binary block schema for the FbPro98 .ply file format.

Defines the `struct.Struct` layouts, block identifier (P95) and the command and
position codes shared by the reader and model. See docs/formats/ply.md for full .ply
format documentation.
"""

from struct import Struct

PLY_HEADER = Struct("<4si")
PLY_PLAYER_OFFSETS = Struct("<11H")
PLY_METADATA = Struct("<BBB")
PLY_PLAYER_HEADER = Struct("<BBH")
PLY_BOX_COUNT = Struct("<H")
PLY_BOX = Struct("<hhH")  # x, y, command count
PLY_COMMAND = Struct("<BB")  # code, argument count
PLY_ARGUMENT = Struct("<h")

PLY_PLAYER_OFFSETS_OFFSET = PLY_HEADER.size
PLY_METADATA_OFFSET = PLY_PLAYER_OFFSETS_OFFSET + PLY_PLAYER_OFFSETS.size
PLY_PLAYER_DATA_BASE = PLY_HEADER.size
# The lowest player offset: a record starts after the category bytes (25).
PLY_FIRST_PLAYER_OFFSET = PLY_METADATA_OFFSET + PLY_METADATA.size - PLY_PLAYER_DATA_BASE

ID_P95 = b"P95:"

# Command codes the play attributes read; docs/formats/ply.md section 2.5.
COMMAND_MOVE_TO = 0x02
COMMAND_TIMED_PASS = 0x06
COMMAND_CHECK_RECEIVERS = 0x08
COMMAND_RUN = 0x0C

# Position codes the play attributes read; docs/formats/ply.md section 4.1.
POSITION_G = 0x0010
POSITION_T = 0x0011
POSITION_C = 0x0012
POSITION_QB = 0x0020
POSITION_DT = 0x0101
POSITION_DE = 0x0102
