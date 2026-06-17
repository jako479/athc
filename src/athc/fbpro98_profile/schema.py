"""Binary block schema for the FbPro98 .prf file format.

Defines the `struct.Struct` layouts and block identifiers (F95, I95) shared
by the reader and writer. See specs/prf.md for full .prf format documentation.
"""

from struct import Struct

F95_HEADER = Struct("<4sI")
F95_SUBSTITUTIONS = Struct("<16H")  # 8 (out, in) pairs = 32 bytes
F95_CATEGORY_WEIGHTS = Struct("<6B")  # 3 x (play_category, weight)
F95_FIELD_GOAL_RANGE = Struct("<B")
F95_USE_AUDIBLES = Struct("<I")
I95_HEADER = Struct("<4sI")
I95_DATA = Struct("<BHBHI")  # profile_type, reserved, fg_range, n_blocks, use_audibles

ID_F95 = b"F95:"
ID_I95 = b"I95:"
ID_G95 = b"G95:"
ID_J95 = b"J95:"
ID_S98 = b"S98:"

F95_DATA_SIZE = 0x3C9D
I95_DATA_SIZE = 0x0A

# F95 sizes for the older "stock" layout (game-shipped profiles); see prf.md section 4.
F95_STOCK_DATA_SIZE_OFFENSE = 0x3F69
F95_STOCK_DATA_SIZE_DEFENSE = 0x4509
F95_STOCK_DATA_SIZES = frozenset(
    {F95_STOCK_DATA_SIZE_OFFENSE, F95_STOCK_DATA_SIZE_DEFENSE}
)

TRAILER_NUL = 0x00
VALID_TRAILER_BYTES = frozenset({TRAILER_NUL})

STOP_CLOCK_BIT = 0x80
WEIGHT_MASK = 0x7F
