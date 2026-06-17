// FBPro98 .ply — ImHex pattern for play files
// Source of truth: ply.md
// Notes:
// - Hex Workshop's fbpro_ply.hsl exists but goes far beyond what is currently
//   understood; this pattern matches the documented scope in ply.md only.
// - The full player-record / logic-box / command layouts are not yet
//   reverse-engineered, so player records here are surfaced as their starting
//   PlayerHeader and a raw byte tail.

#pragma endian little
#pragma pattern_limit 200000

#include <std/sys.pat>

// ---- 4-byte block tag (little-endian) ----
enum BlockType : u32 {
    P95 = 0x3A353950   // "P95:"
};

// ---- play_category odd/even rule: bit 0 = side ----
//   Odd  = offense (or kicking side for special teams)
//   Even = defense (or receiving side for special teams)

// ---- special_category (0 = not special teams); see ply.md section 2.3 ----
enum SpecialCategoryOffense : u8 {
    NOT_SPECIAL     = 0,
    FIELD_GOAL_PAT  = 1,
    KICKOFF         = 2,
    PUNT            = 3,
    ONSIDE_KICK     = 4,
    FAKE_FG_RUN     = 5,
    FAKE_FG_PASS    = 6,
    FAKE_PUNT_RUN   = 7,
    FAKE_PUNT_PASS  = 8,
    FREE_KICK       = 9,
    SQUIB_KICK      = 10
};

enum SpecialCategoryDefense : u8 {
    NOT_SPECIAL             = 0,
    FIELD_GOAL_PAT_DEFENSE  = 1,
    KICK_RETURN             = 2,
    PUNT_RETURN             = 3,
    ONSIDE_RETURN           = 4,
    FAKE_FG_RUN_DEFENSE     = 5,
    FAKE_FG_PASS_DEFENSE    = 6,
    FAKE_PUNT_RUN_DEFENSE   = 7,
    FAKE_PUNT_PASS_DEFENSE  = 8,
    FREE_KICK_RETURN        = 9,
    SQUIB_RETURN            = 10
};

union SpecialCategory {
    SpecialCategoryOffense offense;
    SpecialCategoryDefense defense;
};

// ---- Player record header (first 4 bytes of each player record) ----
//
// type values observed: 0x01 = pre-snap, 0x02 = after-snap, 0x04 = kicking
// position values observed:
//   0x20 = QB, 0x12 = C, 0x11 = T, 0x10 = G,
//   0x81 = TE, 0x80 = WR, 0x42 = HB
//
// The remainder of the record (logic boxes / commands) is variable length
// and not yet fully documented — surfaced here as raw bytes only.
struct PlayerHeader {
    u8  rank;       // depth / rank
    u8  type;       // 0x01 pre-snap, 0x02 after-snap, 0x04 kicking
    u16 position;   // position code
};

// ---- Player record (variable length, only the header is documented) ----
//
// Slot order observed in real files:
//   0=QB, 1=C, 2=LT, 3=LG, 4=RG, 5=RT, 6=TE, 7=RWR, 8=LWR, 9=LHB, 10=RHB
struct PlayerRecord {
    PlayerHeader header;
    // Trailing logic-box / command data is not modeled yet.
};

// ---- P95: header + offsets table + 3 metadata bytes + player records ----
//
// playOffsets are relative to the end of the 8-byte block header (i.e.
// relative to byte 0x08 of the file). The first entry is observed as
// 0x0019 in every sampled real file — pointing to the first byte after
// the 3 metadata bytes.
struct P95 {
    BlockType id;            // "P95:"
    u32       size;          // data length (excludes id+size)

    u16       playOffsets[11];    // offsets to each of the 11 player records

    u8        playCategory;       // raw category byte (bit 0 = side: odd=offense, even=defense)
    SpecialCategory specialCategory;   // 0 = not special teams; otherwise 1-10
    u8        userCategory;       // user-supplied category

    // Player records start here. Each PlayerHeader is 4 bytes; the rest of
    // each record is variable-length and not modeled.
    PlayerRecord players[11] @ addressof(this) + 8 + playOffsets[0];

    std::assert(id == BlockType::P95, "Invalid block ID");
};

// ---- Top-level file ----
struct PlyFile {
    P95 p95;    // 0x00

    std::assert(addressof(p95) + 8 + p95.size == std::mem::size(),
                "File length must equal 8 + P95 size");
};


PlyFile plyfile_at_0x00 @ 0x00;
