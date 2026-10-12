// FBPro98 .ply play file, ImHex pattern. Layout: ply.md.

#pragma description "Front Page Sports Football Pro '98 play (.ply)"
#pragma magic [ 50 39 35 3A ] @ 0x00
#pragma endian little

import std.core;
import std.io;
import std.mem;
import std.sys;

// ---- Names (ply.md sections 2, 3 and 4) ----

fn slot_name(s16 slot) {
    match (slot) {
        (0): return "QB";
        (1): return "C";
        (2): return "LT";
        (3): return "LG";
        (4): return "RG";
        (5): return "RT";
        (6): return "TE";
        (7): return "RWR";
        (8): return "LWR";
        (9): return "LHB";
        (10): return "RHB";
        (_): return "?";
    }
};

fn position_name(u16 position) {
    match (position) {
        (0x0010): return "G";
        (0x0011): return "T";
        (0x0012): return "C";
        (0x0020): return "QB";
        (0x0041): return "FB";
        (0x0042): return "HB";
        (0x0080): return "WR";
        (0x0081): return "TE";
        (0x0101): return "DT";
        (0x0102): return "DE";
        (0x0200): return "LB";
        (0x0400): return "CB";
        (0x0401): return "S";
        (0x0800): return "K";
        (0x1000): return "P";
        (_): return std::format("0x{:04X}", position);
    }
};

fn offense_category_name(u8 code) {
    match (code) {
        (0x01): return "Run Right";
        (0x03): return "Pass Short Right";
        (0x05): return "Run Left";
        (0x07): return "Pass Short Left";
        (0x09): return "Run Middle";
        (0x0B): return "Pass Short Middle";
        (0x0D): return "Razzle Dazzle Run";
        (0x0F): return "Razzle Dazzle Pass";
        (0x13): return "Pass Medium Right";
        (0x17): return "Pass Medium Left";
        (0x1B): return "Pass Medium Middle";
        (0x23): return "Pass Long Right";
        (0x27): return "Pass Long Left";
        (0x2B): return "Pass Long Middle";
        (0x31): return "Goal Line Run";
        (0x33): return "Goal Line Pass";
        (_): return "unknown";
    }
};

fn defense_category_name(u8 code) {
    match (code) {
        (0x00): return "Run Right";
        (0x02): return "Pass Short";
        (0x04): return "Run Left";
        (0x08): return "Run Middle";
        (0x0C): return "Razzle Dazzle Run";
        (0x0E): return "Razzle Dazzle Pass";
        (0x12): return "Pass Medium";
        (0x22): return "Pass Long";
        (0x30): return "Goal Line Run";
        (0x32): return "Goal Line Pass";
        (_): return "unknown";
    }
};

fn special_name(u8 special, bool offense) {
    if (offense) {
        match (special) {
            (0x01): return "FG/PAT";
            (0x02): return "Kickoff";
            (0x03): return "Punt";
            (0x04): return "Onside Kick";
            (0x05): return "Fake FG Run";
            (0x06): return "Fake FG Pass";
            (0x07): return "Fake Punt Run";
            (0x08): return "Fake Punt Pass";
            (0x09): return "Free Kick";
            (0x0A): return "Squib Kick";
            (0x0B): return "Run Clock";
            (0x0C): return "Stop Clock";
            (_): return "unknown";
        }
    }
    match (special) {
        (0x01): return "FG/PAT Defense";
        (0x02): return "Kick Return";
        (0x03): return "Punt Return";
        (0x04): return "Onside Return";
        (0x05): return "Fake FG Run Defense";
        (0x06): return "Fake FG Pass Defense";
        (0x07): return "Fake Punt Run Defense";
        (0x08): return "Fake Punt Pass Defense";
        (0x09): return "Free Kick Return";
        (0x0A): return "Squib Return";
        (_): return "unknown";
    }
};

// Only the codes ply.md section 2.5 lists; any other code shows as a number.
fn command_name(u8 code) {
    match (code) {
        (0x02): return "Move to";
        (0x06): return "Timed pass";
        (0x08): return "Check receivers";
        (0x0C): return "Run";
        (_): return std::format("Code 0x{:02X}", code);
    }
};

fn count_text(u32 n, str one, str many) {
    if (n == 1)
        return std::format("1 {}", one);
    return std::format("{} {}", n, many);
};

// ---- Categories (ply.md section 3) ----

enum Side : u8 {
    Defense = 0,
    Offense = 1
};

enum RunPass : u8 {
    Run = 0,
    Pass = 1
};

enum Direction : u8 {
    Right = 0,
    Left = 1,
    Middle = 2,
    RazzleDazzle = 3
};

enum Distance : u8 {
    Short = 0,
    Medium = 1,
    Long = 2,
    GoalLine = 3
};

// Bits 5-0 are the category code; bits 7-6 hold the same pair in the play
// and user category bytes.
bitfield Category {
    Side side : 1;
    RunPass runPass : 1;
    Direction direction : 2;
    Distance distance : 2;
    high : 2 [[comment("Bits 7-6: not part of the category code")]];
} [[format("category_format")]];

fn category_format(ref auto c) {
    u8 value = std::mem::read_unsigned(addressof(c), 1);
    str name;
    if (value == 0xFF || value == 0xFE)
        name = "User Specific";
    else if (std::mem::read_unsigned(0x1F, 1) != 0)
        name = "special play";
    else if ((value & 0x01) == 1)
        name = offense_category_name(value & 0x3F);
    else
        name = defense_category_name(value & 0x3F);
    return std::format("0x{:02X} {}", value, name);
};

fn special_format(u8 v) {
    if (v == 0)
        return "0x00 normal play";
    bool offense = (std::mem::read_unsigned(0x1E, 1) & 0x01) == 1;
    return std::format("0x{:02X} {}", v, special_name(v, offense));
};

// ---- Commands (ply.md sections 2.4 and 2.5) ----

fn tenths_format(s16 v) {
    return std::format("{}.{} s", v / 10, v % 10);
};

struct Command {
    u8 code [[format("command_code_format")]];
    u8 argumentCount;
    if (argumentCount == 2 && code == 0x02) {
        s16 x;
        s16 y;
    } else if (argumentCount == 1 && code == 0x06) {
        s16 tenths [[format("tenths_format")]];
    } else if (argumentCount == 1 && code == 0x08) {
        s16 receivers;
    } else if (argumentCount == 1 && code == 0x0C) {
        s16 direction;
    } else if (argumentCount > 0) {
        s16 arguments[argumentCount];
    }
} [[format("command_format")]];

fn command_code_format(u8 code) {
    return std::format("0x{:02X} {}", code, command_name(code));
};

fn command_format(ref auto c) {
    u128 a = addressof(c);
    u8 code = std::mem::read_unsigned(a, 1);
    u8 count = std::mem::read_unsigned(a + 1, 1);
    str name = command_name(code);
    if (count == 0)
        return name;
    s16 arg0 = std::mem::read_signed(a + 2, 2);
    if (count == 2 && code == 0x02)
        return std::format("{} ({}, {})", name, arg0, std::mem::read_signed(a + 4, 2));
    if (count == 1 && code == 0x06)
        return std::format("{} {}", name, tenths_format(arg0));
    return std::format("{} ({})", name, count_text(count, "argument", "arguments"));
};

// ---- Logic boxes (ply.md sections 2.2, 2.3 and 2.6) ----

// (0, 0) is the ball on the line of scrimmage; 90 units = 1 yard.
struct LogicBox {
    s16 x [[comment("Sideways, positive to the offense's right")]];
    s16 y [[comment("Downfield, positive toward the defense")]];
    u16 commandCount;
    Command commands[commandCount];
} [[format("logic_box_format")]];

fn logic_box_format(ref auto b) {
    return std::format("({}, {}), {}", b.x, b.y, count_text(b.commandCount, "command", "commands"));
};

struct BoxList {
    u16 boxCount;
    LogicBox boxes[boxCount];
} [[format("box_list_format")]];

fn box_list_format(ref auto l) {
    return count_text(l.boxCount, "box", "boxes");
};

// ---- Player records (ply.md sections 2.1 and 4) ----

bitfield Role {
    snapper : 1 [[comment("Offense and kicking: snaps the ball. Defense: Preferred Player")]];
    snapReceiver : 1 [[comment("The default snap receiver, slot 0")]];
    kicker : 1;
    unknown : 5;
};

fn position_format(u16 v) {
    return std::format("0x{:04X} {}", v, position_name(v));
};

struct PlayerRecord {
    u8 rank [[comment("Depth chart number at the position")]];
    Role role;
    u16 position [[format("position_format")]];
    BoxList preSnap;
    BoxList afterSnap;
};

// Record k starts at 0x0008 + offset k; the records are back to back.
struct PlayerSlot {
    u16 offset;
    PlayerRecord record @ 0x08 + offset;
} [[format("player_slot_format")]];

fn player_slot_format(ref auto s) {
    u128 a = addressof(s);
    s16 slot = (a - 0x08) / 2;
    u128 r = 0x08 + std::mem::read_unsigned(a, 2);
    u8 rank = std::mem::read_unsigned(r, 1);
    u16 position = std::mem::read_unsigned(r + 2, 2);
    return std::format("{} slot: {}{}", slot_name(slot), position_name(position), rank);
};

// ---- File ----

struct P95 {
    char id[4];
    u32 size [[comment("Data size: everything after this field")]];
    PlayerSlot players[11];
    Category playCategory [[comment("Assigned by the game")]];
    u8 specialCategory [[format("special_format")]];
    Category userCategory [[comment("Chosen by the coach")]];
    std::assert(id == "P95:", "P95 block expected");
    std::assert(8 + size == std::mem::size(), "File length must equal 8 + size");
};

P95 play @ 0x00;
