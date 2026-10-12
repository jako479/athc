// FBPro98 .pyr player file, ImHex pattern. Layout: pyr.md.
// Every byte after the header is coded on disk; the fields show the decoded
// values, while the hex view highlights the bytes on disk.

#pragma description "Front Page Sports Football Pro '98 players (.pyr)"
#pragma endian little
#pragma array_limit 0x100000
#pragma pattern_limit 0x1000000
#pragma loop_limit 0x100000

import std.io;
import std.mem;
import std.sys;

// ---- Coding (pyr.md section 3) ----

// Each file has its own byte-for-byte table, not stored in the file. Record i
// starts with player id 100 + i, so the coded first two bytes of every record
// show what those plain bytes are written as. decodeTable maps a byte on disk
// to its plain value; 0xFFFF marks a byte no record revealed.
std::mem::Section decodeSection = std::mem::create_section("pyr decode table");
std::mem::set_section_size(decodeSection, 512);
u16 decodeTable[256] @ 0x00 in decodeSection;

fn build_decode_table() {
    for (u32 i = 0, i < 256, i += 1)
        decodeTable[i] = 0xFFFF;
    u32 records = (std::mem::size() - 60) / 60;
    for (u32 r = 0, r < records, r += 1) {
        u32 id = 100 + r;
        u128 a = 0x3C + 60 * r;
        decodeTable[std::mem::read_unsigned(a, 1)] = id & 0xFF;
        decodeTable[std::mem::read_unsigned(a + 1, 1)] = (id >> 8) & 0xFF;
    }
};

build_decode_table();

fn decode(u128 address) {
    return decodeTable[std::mem::read_unsigned(address, 1)];
};

fn decoded_format(u16 v) {
    if (v == 0xFFFF)
        return "?";
    return std::format("{}", v);
};

struct CU8 {
    u8 raw;
} [[sealed, format("cu8_format")]];

fn cu8_format(ref auto v) {
    return decoded_format(decode(addressof(v)));
};

struct CU16 {
    u8 raw[2];
} [[sealed, format("cu16_format")]];

fn cu16_value(ref auto v) {
    u128 a = addressof(v);
    u16 lo = decode(a);
    u16 hi = decode(a + 1);
    if (lo == 0xFFFF || hi == 0xFFFF)
        return 0xFFFFFFFF;
    return lo | (hi << 8);
};

fn cu16_format(ref auto v) {
    u32 x = cu16_value(v);
    if (x == 0xFFFFFFFF)
        return "?";
    return std::format("{}", x);
};

// NUL-padded text.
struct CText<auto Size> {
    u8 raw[Size];
} [[sealed, format("ctext_format")]];

fn ctext_format(ref auto v) {
    str s;
    u128 a = addressof(v);
    for (u128 i = 0, i < sizeof(v), i += 1) {
        u16 c = decode(a + i);
        if (c == 0)
            break;
        if (c == 0xFFFF)
            s += "?";
        else
            s += char(c);
    }
    return s;
};

struct CBytes<auto Size> {
    u8 raw[Size];
} [[sealed, format("cbytes_format")]];

fn cbytes_format(ref auto v) {
    str s;
    u128 a = addressof(v);
    for (u128 i = 0, i < sizeof(v), i += 1) {
        if (i > 0)
            s += " ";
        u16 c = decode(a + i);
        if (c == 0xFFFF)
            s += "??";
        else
            s += std::format("{:02X}", c);
    }
    return s;
};

// ---- Codes (pyr.md section 5) ----

fn position_name(u16 p) {
    match (p) {
        (0): return "QB";
        (1): return "FB";
        (2): return "HB";
        (3): return "TE";
        (4): return "WR";
        (5): return "C";
        (6): return "G";
        (7): return "T";
        (8): return "DE";
        (9): return "DT";
        (10): return "LB";
        (11): return "CB";
        (12): return "S";
        (13): return "K";
        (14): return "P";
        (_): return "";
    }
};

fn position_format(ref auto v) {
    u16 p = decode(addressof(v));
    str name = position_name(p);
    if (name == "")
        return decoded_format(p);
    return std::format("{} ({})", p, name);
};

// Ratings 0-99, in file order.
struct Ratings {
    CU8 acceleration;
    CU8 agility;
    CU8 discipline;
    CU8 endurance;
    CU8 hands;
    CU8 intelligence;
    CU8 speed;
    CU8 strength;
};

// All 0 when healthy.
struct Injury {
    CU16 unknown0;
    CU8 injury [[comment("Injury name index into injury.dat")]];
    CU8 unknown3;
};

// ---- Records ----

struct Header {
    u16 key;
    u8 zero[58];
};

struct Player {
    CU16 id;
    CText<13> firstName;
    CText<13> lastName;
    Ratings potential [[comment("Not shown in the game")]];
    Injury injury;
    CU8 group [[comment("Position group")]];
    CU8 position [[format("position_format")]];
    Ratings actual [[comment("The ratings the game shows")]];
    CU8 years [[comment("Years in the league")]];
    CU8 height [[comment("Inches; filled only for the newest draft class")]];
    CU16 weight [[comment("Pounds; filled only for the newest draft class")]];
    CBytes<6> unknown36;
} [[format("player_format")]];

fn player_format(ref auto p) {
    str position = position_name(decode(addressof(p.position)));
    return std::format("{} {} {} {}", cu16_format(p.id),
        ctext_format(p.firstName), ctext_format(p.lastName), position);
};

Header header @ 0x00;
Player players[(std::mem::size() - 60) / 60] @ 0x3C;
