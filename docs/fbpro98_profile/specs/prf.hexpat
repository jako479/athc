// FBPro98 .prf — ImHex pattern converted from Hex Workshop .hsl
// Source: fbpro_prf.hsl + PrfToExcel.py
// Notes:
// - Hex Workshop had: #pragma byteorder(little_endian)
//   ImHex equivalent: #pragma endian little
// - Enum BLOCK_TYPE values in the .hsl were string literals ("F95:", etc.)
//   ImHex doesn't support enum string literals
// - A profile saved without game plans is F95 + I95 + trailer.
//   A profile saved with game plans appends one G95 + S98 before the trailer
//   I95.numGamePlanBlocks is believed to be the count.
// - Trailer is always 1 byte (offense) or 2 bytes (defense) so that the total
//   file size is even (offense) or odd (defense). Trailer bytes are 0x00 in
//   player-saved profiles and 0x69 ('i') in the game's stock profiles.

#pragma endian little
#pragma pattern_limit 200000

#include <std/sys.pat>

// ---- 4-byte tags (little-endian) ----
enum BlockType : u32 {
    F95 = 0x3A353946,  // "F95:"
    G95 = 0x3A353947,  // "G95:"
    I95 = 0x3A353949,  // "I95:"
    S98 = 0x3A383953   // "S98:"
};

// ---- Profile type ----
enum ProfileType : u8 {
    DEFENSE = 0,
    OFFENSE = 1
};

// ---- Play category (used in F95 category-weights records); see prf.md section 2.3.2 ----
enum PlayCategoryOffense : u8 {
    GOAL_LINE_RUN        = 0x00,
    RAZZLE_DAZZLE_RUN    = 0x01,
    RUN_LEFT             = 0x02,
    RUN_MIDDLE           = 0x03,
    RUN_RIGHT            = 0x04,
    GOAL_LINE_PASS       = 0x05,
    RAZZLE_DAZZLE_PASS   = 0x06,
    PASS_LONG_LEFT       = 0x07,
    PASS_LONG_MIDDLE     = 0x08,
    PASS_LONG_RIGHT      = 0x09,
    PASS_MEDIUM_LEFT     = 0x0A,
    PASS_MEDIUM_MIDDLE   = 0x0B,
    PASS_MEDIUM_RIGHT    = 0x0C,
    PASS_SHORT_LEFT      = 0x0D,
    PASS_SHORT_MIDDLE    = 0x0E,
    PASS_SHORT_RIGHT     = 0x0F,
    FIELD_GOAL_PAT       = 0x10,
    FAKE_FIELD_GOAL_RUN  = 0x11,
    FAKE_FIELD_GOAL_PASS = 0x12,
    PUNT                 = 0x13,
    FAKE_PUNT_RUN        = 0x14,
    FAKE_PUNT_PASS       = 0x15,
    RUN_CLOCK            = 0x16,
    RUN_RANDOM           = 0x17,
    PASS_LONG_RANDOM     = 0x18,
    PASS_MEDIUM_RANDOM   = 0x19,
    PASS_SHORT_RANDOM    = 0x1A
};

// Defense collapses the offense's directional pass codes (0x07-0x0F) into
// three labels — left/middle/right are treated as a single defensive call.
enum PlayCategoryDefense : u8 {
    GOAL_LINE_RUN        = 0x00,
    RAZZLE_DAZZLE_RUN    = 0x01,
    RUN_LEFT             = 0x02,
    RUN_MIDDLE           = 0x03,
    RUN_RIGHT            = 0x04,
    GOAL_LINE_PASS       = 0x05,
    RAZZLE_DAZZLE_PASS   = 0x06,
    PASS_LONG            = 0x07 ... 0x09,
    PASS_MEDIUM          = 0x0A ... 0x0C,
    PASS_SHORT           = 0x0D ... 0x0F,
    FIELD_GOAL_PAT       = 0x10,
    FAKE_FIELD_GOAL_RUN  = 0x11,
    FAKE_FIELD_GOAL_PASS = 0x12,
    PUNT                 = 0x13,
    FAKE_PUNT_RUN        = 0x14,
    FAKE_PUNT_PASS       = 0x15
};

union PlayCategory {
    PlayCategoryOffense offense;
    PlayCategoryDefense defense;
};

// ---- Substitution percentages for one position group ----
struct SubstitutionSettings {
    u16 outPercent;     // 0x00; 0-100
    u16 inPercent;      // 0x02; 0-100, must be >= outPercent
};

// ---- All position group substitution settings ----
struct SubstitutionData {
    SubstitutionSettings offensiveLinemen;  // 0x00
    SubstitutionSettings quarterbacks;      // 0x04
    SubstitutionSettings runningBacks;      // 0x08
    SubstitutionSettings receivers;         // 0x0C
    SubstitutionSettings defensiveLinemen;  // 0x10
    SubstitutionSettings linebackers;       // 0x14
    SubstitutionSettings defensiveBacks;    // 0x18
    SubstitutionSettings kickers;           // 0x1C
                                            // 0x20
};

// ---- One category-weights entry: 3 weighted play category picks for a situation ----
// Used in both the 2520-entry regular situations array and the 60-entry PAT array.
// For regular situations, bit 7 (0x80) of weight1 is the Stop-Clock flag.
// For PAT situations, weight1 is a plain weight in [0x00, 0x0A]; bit 7 is not used.
struct CategoryWeights {
    PlayCategory playCategory1; // 0x00
    u8           weight1;       // 0x01; regular: 0x00-0x0A | 0x80-0x8A; PAT: 0x00-0x0A
    PlayCategory playCategory2; // 0x02
    u8           weight2;       // 0x03; 0x00-0x0A
    PlayCategory playCategory3; // 0x04
    u8           weight3;       // 0x05; 0x00-0x0A
                                // 0x06
};

// ---- F95: substitutions, 2520 category-weights records, FG range, 60 PAT records, audibles ----
//
// Regular situations array (2520 entries) is indexed by situation number, with
// the position determined by the 5-bucket game-state cross-product and one
// structural gap. See prf.md section 2.3.4 for the layout.
//   minutes_remaining (5) x down (4) x yards_to_go (4) x field_position (5) x point_spread (7)
//   = 5*4*4*5*7 = 2800 dense, minus 280 invalid combos (INSIDE_DEF_5 x yards >= 6) = 2520.
//
// PAT situations array (60 entries) varies only by minutes_remaining (4) and point_spread (15).
// See prf.md section 2.5.1.
//   minutes_remaining (4) x point_spread (15) = 60. No gaps.
struct F95 {
    BlockType id;       // 0x00; "F95:"
    u32       len;      // 0x04; data length (excludes id+len) // 0x3C9D

    SubstitutionData substitutions;             // 0x08
    CategoryWeights  categoryWeights[2520];     // 0x28; situation number = index
    u8               fieldGoalRange;            // 0x3B38; 5-50
    CategoryWeights  patCategoryWeights[60];    // 0x3B39; PAT situation number = index
    u32              useAudibles;               // 0x3CA1; 0 or 1
                                                // 0x3CA5

    std::assert(id == BlockType::F95, "Invalid block ID");
    std::assert(len == 0x3C9D, "Invalid data length");
};

// ---- I95: profile type, FG range, embedded-plan count, audibles ----
struct I95 {
    BlockType   id;                 // 0x00; "I95:"
    u32         len;                // 0x04; data length (excludes id+len) // 0x0A

    ProfileType profileType;        // 0x08; 0=DEFENSE, 1=OFFENSE
    u16         reserved;           // 0x09; always 0x0000
    u8          fieldGoalRange;     // 0x0B; 5-50
    u16         numGamePlanBlocks;  // 0x0C; number of embedded game plans (best guess)
    u32         useAudibles;        // 0x0E; 0 or 1
                                    // 0x12

    std::assert(id == BlockType::I95, "Invalid block ID");
    std::assert(len == 0x0A, "Invalid data length");
};

// ---- Stock/custom flag (G95 play entries) ----
enum StockFlag : u8 {
    NOT_STOCK = 0x00,
    STOCK     = 0x01
};

// ---- One play entry inside an embedded G95 (variable-length if not stock) ----
struct PlayInPlan {
    StockFlag stockFlag;   // 0x00 not stock, 0x01 stock
    if (stockFlag != StockFlag::NOT_STOCK && stockFlag != StockFlag::STOCK)
        continue;
    u8        playCategory;
    u8        specialCategory;
    u8        userCategory;

    if (stockFlag == StockFlag::NOT_STOCK) {
        char playName[];
    } else {
        char  playName[8];
        u32   offset;      // Unknown offset (unrelated to the game plan file)
        u16   size;        // Unknown size (unrelated to the game plan file)
    }
};

// ---- G95: embedded game plan (header + four ordered offset arrays + play data) ----
struct G95 {
    BlockType id;   // "G95:"
    u32       len;  // data length (excludes id+len)

    u8  audible[4];       // 00|01|02|03
    u16 playOffsets[86];  // 64 Normal, 20 Special, 2 Clock
                          // Offset from 0x0C to the start of each play in the
                          // plan; Any empty slots have an offset of 0.
                          // Normal plays have specialCategory of 0.
                          // Special teams plays go in order of specialCategory,
                          // 1-10, alternating between non-stock and stock
                          // versions of each. Each special teams play has
                          // playCategory of 1 and userCategory of 1.

    // Plays continue until the end of the G95 block (id+len header is 8 bytes,
    // then `len` bytes of data).
    PlayInPlan plays[while($ < addressof(this) + 8 + len)];

    std::assert(id == BlockType::G95, "Invalid block ID");
};

// ---- S98: embedded game plan map filename (length-prefixed) ----
struct S98 {
    BlockType id;   // "S98:"
    u32       len;  // data length (excludes id+len)

    char      mapFilename[len];   // STOCK98.MAP (null-terminated)

    std::assert(id == BlockType::S98, "Invalid block ID");
};

// ---- One embedded game plan trio ----
struct GamePlan {
    G95 g95;
    S98 s98;
};

// ---- Top-level file ----
struct PrfFile {
    F95 f95;    // 0x0000

    BlockType nextBlock @ $;   // peek next 4 bytes without consuming
    if (nextBlock == BlockType::G95) {
        GamePlan gamePlan;
    }

    I95 i95;    // 0x3CA5
};


PrfFile prffile_at_0x00 @ 0x00;
