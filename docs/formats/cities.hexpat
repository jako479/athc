// FBPro98 CITIES.DAT city table, ImHex pattern. Layout: cities.md.

#pragma description "Front Page Sports Football Pro '98 city table (CITIES.DAT)"
#pragma magic [ 43 54 4C 3A ] @ 0x00
#pragma endian little

import std.io;
import std.mem;
import std.sys;

// Fixed-size text; bytes after the first NUL are leftovers.
struct Text<auto Size> {
    char raw[Size];
} [[sealed, format("text_format")]];

fn text_format(ref auto t) {
    str s;
    for (u32 i = 0, i < sizeof(t), i += 1) {
        if (t.raw[i] == 0)
            break;
        s += t.raw[i];
    }
    return s;
};

// An inclusive percentage range; 0 0 is an outcome that never happens.
struct Range {
    u8 low;
    u8 high;
} [[format("range_format")]];

fn range_format(ref auto r) {
    if (r.low == 0 && r.high == 0)
        return "never";
    return std::format("{}-{}", r.low, r.high);
};

// ---- Header tables; their meaning is not mapped ----

struct RangeRow {
    Range pairs[5];
};

struct CTL {
    char tag[4];
    u32 size;
    RangeRow rows[7];
    std::assert(tag == "CTL:", "CTL chunk expected");
};

struct CTR {
    char tag[4];
    u32 size;
    Range pairs[5];
    std::assert(tag == "CTR:", "CTR chunk expected");
};

struct CHI {
    char tag[4];
    u32 size;
    s8 values[66];
    std::assert(tag == "CHI:", "CHI chunk expected");
};

struct ValueRow {
    u8 values[10];
};

struct CWC {
    char tag[4];
    u32 size;
    ValueRow rows[7];
    std::assert(tag == "CWC:", "CWC chunk expected");
};

// ---- CTY: city ----

// Odds of each outcome the game's weather screen shows.
struct Weather {
    Range clear;
    Range partlyCloudy;
    Range cloudy;
    Range rainSnow;
    u8 unknown8;
    u8 unknown9;
};

fn stadium_type_format(u8 v) {
    match (v) {
        (0): return "0 (outdoor/grass)";
        (1): return "1 (other outdoor)";
        (2): return "2 (dome)";
        (_): return std::format("{}", v);
    }
};

struct City {
    char tag[4];
    u32 size;
    u8 id [[comment("The value a .lge team chunk stores")]];
    Text<16> name;
    u8 unknown11;
    Weather augSept;
    Weather october;
    Weather november;
    Weather december;
    Weather january;
    u8 unknown44;
    u8 stadiumType [[format("stadium_type_format")]];
    Text<32> stadium;
    std::assert(tag == "CTY:", "CTY chunk expected");
} [[format("city_format")]];

fn city_format(ref auto c) {
    return std::format("{} {}", c.id, text_format(c.name));
};

// ---- File ----

struct CitiesFile {
    CTL ctl;
    CTR ctr;
    CHI chi;
    CWC cwc;
    City cities[while(!std::mem::eof())];
};

CitiesFile cities @ 0x00;
