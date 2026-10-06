"""Binary layout constants for the FbPro98 .lg2 league file format.

Shared by the reader and its tests. See specs/lg2.md for the full format.
"""

FOLDER_SIZE = 0x105
FILENAME_SIZE = 0x106
FILE_ENTRY_SIZE = FOLDER_SIZE + FILENAME_SIZE  # 0x20B
FILES_PER_TEAM = 8
TEAM_TRAILER_SIZE = 9  # not reverse engineered; ignored
TEAM_RECORD_SIZE = FILE_ENTRY_SIZE * FILES_PER_TEAM + TEAM_TRAILER_SIZE  # 0x1061

# How a stock league's first folder field starts; see specs/lg2.md 2.3 and 3.3.
MODERN_STOCK_FOLDER = b"STOCK\x00A\\FBPRO97\\STOCK\x00"
OLD_STOCK_FOLDER = b"\x00"
