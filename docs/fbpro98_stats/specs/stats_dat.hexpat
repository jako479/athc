// FBPro98 .dat statistics file and its .idx index, ImHex pattern. Layout: stats_dat.md.
// One pattern for both files: the header tells them apart.

#pragma description "Front Page Sports Football Pro '98 statistics (.dat) and index (.idx)"
#pragma endian little
#pragma array_limit 0x100000
#pragma pattern_limit 0x1000000

import std.io;
import std.mem;

// ---- Record types (stats_dat.md sections 4 and 5) ----

fn block_base(u16 type) {
    if (type >= 198) return 198;
    if (type >= 164) return 164;
    if (type >= 130) return 130;
    if (type >= 96) return 96;
    if (type >= 64) return 64;
    if (type >= 32) return 32;
    return 0;
};

fn block_name(u16 base) {
    match (base) {
        (0): return "player last game";
        (32): return "player season";
        (64): return "player career";
        (96): return "team last game";
        (130): return "team season";
        (164): return "opponents last game";
        (198): return "opponents season";
    }
};

fn category_name(u16 category) {
    match (category) {
        (0): return "extra points";
        (1): return "field goals";
        (2): return "rushing";
        (3): return "passing";
        (4): return "receiving";
        (5): return "interceptions";
        (6): return "punting";
        (7): return "punt returns";
        (8): return "kick returns";
        (9): return "fumbles";
        (10): return "fumble recoveries";
        (11): return "sacks";
        (12): return "unknown 12";
        (13): return "tackles";
        (14): return "unknown 14";
        (15): return "unknown 15";
        (16): return "unknown 16";
        (17): return "two-point conversions";
        (_): return std::format("category {}", category);
    }
};

fn type_name(u16 type) {
    u16 base = block_base(type);
    return std::format("{}, {}", block_name(base), category_name(type - base));
};

fn type_format(u16 type) {
    return std::format("{} ({})", type, type_name(type));
};

// ---- Values by category; values past the last one hold leftover memory ----

struct ExtraPoints {
    s16 attempts;
    s16 made;
    s16 leftover[6];
};

// Low byte made, high byte attempts.
struct FieldGoalRange {
    u8 made;
    u8 attempts;
} [[format("field_goal_range_format")]];

fn field_goal_range_format(ref auto r) {
    return std::format("{} of {}", r.made, r.attempts);
};

struct FieldGoals {
    s16 long;
    FieldGoalRange under20;
    FieldGoalRange from20to29;
    FieldGoalRange from30to39;
    FieldGoalRange from40to49;
    FieldGoalRange from50;
    s16 leftover[2];
};

// Rushing, receiving, interceptions, kick returns and fumble recoveries.
struct YardsAndTouchdowns {
    s16 count;
    s16 yards;
    s16 long;
    s16 touchdowns;
    s16 leftover[4];
};

struct Passing {
    s16 attempts;
    s16 yards;
    s16 long;
    s16 touchdowns;
    s16 completions;
    s16 interceptions;
    s16 sacked;
    s16 sackYards;
};

struct Punting {
    s16 punts;
    s16 yards;
    s16 long;
    s16 unknown3;
    s16 unknown4;
    s16 unknown5;
    s16 returnYards;
    s16 touchbacks;
};

struct PuntReturns {
    s16 returns;
    s16 yards;
    s16 long;
    s16 touchdowns;
    s16 unknown4;
    s16 leftover[3];
};

struct OneCount {
    s16 count;
    s16 leftover[7];
};

struct TwoPoint {
    s16 attempts;
    s16 made;
    s16 leftover[6];
};

struct Unmapped {
    s16 values[8];
};

// ---- .dat ----

struct DatHeader {
    u32 fileEnd [[comment("File size - 1")]];
    u32 deletedList [[comment("Offset of the first deleted slot; 0 when none")]];
    u32 slotsEnd [[comment("Offset of the last byte of the last slot")]];
    u8 zero0C[8];
    u32 unknown14;
    u32 records [[comment("Records in use")]];
    u8 zero1C[12];
    u16 unknown28;
    u16 zero2A;
    u16 recordSize;
    u16 unknown2E;
    u16 unknown30;
    u8 zero32[8];
    u16 unknown3A;
    u16 unknown3C;
    u16 unknown3E;
    u8 zero40[32];
    u8 unknown60;
    u8 zero61[3];
    u8 unknown64;
    u8 zero65[27];
    u8 fill[12];
};

// A slot holds a record, or is deleted: a deleted slot starts with 0xFF,
// which no record type uses.
struct Slot {
    if (std::mem::read_unsigned($, 1) == 0xFF) {
        u8 mark;
        u32 next [[comment("Offset of the next deleted slot; 0 ends the list")]];
        u8 leftover[15];
    } else {
        u16 type [[format("type_format")]];
        u16 id [[comment("Player id in player blocks, team number in team blocks")]];
        match (type - block_base(type)) {
            (0): ExtraPoints values;
            (1): FieldGoals values;
            (2): YardsAndTouchdowns values;
            (3): Passing values;
            (4): YardsAndTouchdowns values;
            (5): YardsAndTouchdowns values;
            (6): Punting values;
            (7): PuntReturns values;
            (8): YardsAndTouchdowns values;
            (9): OneCount values;
            (10): YardsAndTouchdowns values;
            (11): OneCount values;
            (12): OneCount values;
            (13): OneCount values;
            (17): TwoPoint values;
            (_): Unmapped values;
        }
    }
} [[format("slot_format")]];

fn slot_format(ref auto s) {
    if (std::mem::read_unsigned(addressof(s), 1) == 0xFF)
        return "deleted";
    return std::format("{} {}", s.id, type_name(s.type));
};

struct Dat {
    DatHeader header;
    Slot slots[(header.slotsEnd - 139) / 20];
    if (!std::mem::eof())
        u8 unused[std::mem::size() - $] [[comment("All 0xFF")]];
};

// ---- .idx ----

struct IdxHeader {
    u32 fileEnd [[comment("File size - 1")]];
    u32 unknown04;
    u32 blocksEnd [[comment("Offset of the last byte of the last block in use")]];
    u8 zero0C[12];
    u32 entries [[comment("Leaf entries; the .dat record count")]];
    u32 root [[comment("Offset of the root node; 0 when empty")]];
    u8 zero20[8];
    u16 unknown28;
    u16 blockSize;
    u16 zero2C;
    u16 unknown2E;
    u16 unknown30;
    u16 zero32;
    u16 unknown34;
    u16 unknown36;
    u8 zero38[4];
    u16 unknown3C;
    u16 unknown3E;
    u16 unknown40;
    u16 keySize;
    u8 zero44[4];
    u32 firstLeaf [[comment("Offset of the leftmost leaf; 0 when empty")]];
    u8 zero4C[18];
    u16 unknown5E;
    u8 unknown60;
    u8 zero61[31];
    u8 fill[384];
};

// The key is type then id, big-endian, so entries sort by type, then id.
struct Entry {
    u32 pointer [[comment("Leaf: .dat offset of the record. Non-leaf: .idx offset of the child")]];
    be u16 type;
    be u16 id;
} [[format("entry_format")]];

fn entry_format(ref auto e) {
    if (e.type == 0xFFFF && e.id == 0xFFFF)
        return std::format("last -> 0x{:X}", e.pointer);
    return std::format("{} {} -> 0x{:X}", e.id, type_name(e.type), e.pointer);
};

struct Node {
    u32 next [[comment("Next node on the same level; 0 on the last")]];
    u32 previous [[comment("Previous leaf; 0 on the first leaf and every non-leaf node")]];
    u16 entryCount;
    u16 bytes [[comment("8 x entries")]];
    u8 zero[5];
    u8 leaf [[comment("1 leaf, 0 non-leaf")]];
    Entry entries[entryCount];
    u8 leftover[494 - 8 * entryCount];
} [[format("node_format")]];

fn node_format(ref auto n) {
    str kind = "non-leaf";
    if (n.leaf == 1)
        kind = "leaf";
    return std::format("{}, {} entries", kind, n.entryCount);
};

struct Idx {
    IdxHeader header;
    Node nodes[(header.blocksEnd + 1) / 512 - 1];
    if (!std::mem::eof())
        u8 unused[std::mem::size() - $] [[comment("All 0xFF")]];
};

// ---- File ----

// A .dat header holds the record size (20) at 0x2C; an .idx header holds the
// block size (512) at 0x2A.
struct StatsFile {
    if (std::mem::read_unsigned(0x2A, 2) == 512)
        Idx idx [[inline]];
    else
        Dat dat [[inline]];
};

StatsFile file @ 0x00;
