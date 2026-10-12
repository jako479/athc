// FBPro98 .lg2 league file, ImHex pattern. Layout: lg2.md.
// One layout covers custom, modern stock and old stock leagues.

#pragma description "Front Page Sports Football Pro '98 league profiles and game plans (.lg2)"
#pragma endian little

import std.io;
import std.mem;

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

// The file is folder\filename under the game folder.
struct FileEntry {
    Text<0x105> folder;
    Text<0x106> filename;
} [[format("file_entry_format")]];

fn file_entry_format(ref auto e) {
    str folder = text_format(e.folder);
    if (folder == "")
        return text_format(e.filename);
    return folder + "\\" + text_format(e.filename);
};

fn home_jersey_format(u8 v) {
    match (v) {
        (0): return "0 (light)";
        (1): return "1 (dark)";
        (_): return std::format("{}", v);
    }
};

// A uniform color from the team's .lge colors; code 1 is never used.
fn number_color_format(u32 v) {
    match (v) {
        (0): return "0 (helmet)";
        (2): return "2 (jersey stripe)";
        (3): return "3 (pants)";
        (4): return "4 (pants stripe)";
        (5): return "5 (sock stripe)";
        (_): return std::format("{}", v);
    }
};

struct Trailer {
    u8 homeJersey [[format("home_jersey_format")]];
    u32 darkNumberColor [[format("number_color_format")]];
    u32 lightNumberColor [[format("number_color_format")]];
};

struct Team {
    FileEntry firstHalfOffenseProfile;
    FileEntry firstHalfOffenseGamePlan;
    FileEntry firstHalfDefenseProfile;
    FileEntry firstHalfDefenseGamePlan;
    FileEntry secondHalfOffenseProfile;
    FileEntry secondHalfOffenseGamePlan;
    FileEntry secondHalfDefenseProfile;
    FileEntry secondHalfDefenseGamePlan;
    Trailer trailer;
} [[format("team_format")]];

fn team_format(ref auto t) {
    return file_entry_format(t.firstHalfOffenseProfile);
};

// Teams in .lge team-number order; the count is not stored.
Team teams[std::mem::size() / 0x1061] @ 0x00;
