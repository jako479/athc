"""Binary block schema for the FbPro98 .ply file format.

Defines the `struct.Struct` layouts and block identifier (P95) shared by the
reader. See specs/ply.md for full .ply format documentation.
"""

from struct import Struct

PLY_HEADER = Struct("<4si")
PLY_PLAYER_OFFSETS = Struct("<11H")
PLY_METADATA = Struct("<BBB")
PLY_PLAYER_HEADER = Struct("<BBH")

PLY_PLAYER_OFFSETS_OFFSET = PLY_HEADER.size
PLY_METADATA_OFFSET = PLY_PLAYER_OFFSETS_OFFSET + PLY_PLAYER_OFFSETS.size
PLY_PLAYER_DATA_BASE = PLY_HEADER.size

ID_P95 = b"P95:"
