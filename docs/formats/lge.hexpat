// FBPro98 .lge league file, ImHex pattern. Layout: lge.md.
// Team (T03) and roster (R03) chunks are masked on disk; their fields show
// the unmasked values, while the hex view highlights the bytes on disk.

#pragma description "Front Page Sports Football Pro '98 league (.lge)"
#pragma magic [ 4C 30 33 3A ] @ 0x00
#pragma endian little

import std.io;
import std.mem;
import std.sys;

// ---- Plain text ----

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

fn hex_bytes(u128 address, u128 size, u32 team, u128 start) {
    str s;
    for (u128 i = 0, i < size, i += 1) {
        if (i > 0)
            s += " ";
        s += std::format("{:02X}", unmask(team, start, address + i));
    }
    return s;
};

// ---- Mask (lge.md section 8) ----

// Byte i of a masked chunk is XORed with (0x69 * team + i) mod 256. Team is the
// chunk's clear team number; Start is the address of its first masked byte.
fn unmask(u32 team, u128 start, u128 address) {
    return std::mem::read_unsigned(address, 1) ^ ((0x69 * team + (address - start)) & 0xFF);
};

struct MU8<auto Team, auto Start> {
    u8 raw;
} [[sealed, format("mu8_format")]];

fn mu8_value(ref auto v) {
    return unmask(v.Team, v.Start, addressof(v));
};

fn mu8_format(ref auto v) {
    return mu8_value(v);
};

struct MU16<auto Team, auto Start> {
    u8 raw[2];
} [[sealed, format("mu16_format")]];

fn mu16_format(ref auto v) {
    u128 a = addressof(v);
    return unmask(v.Team, v.Start, a) | (unmask(v.Team, v.Start, a + 1) << 8);
};

struct MText<auto Team, auto Start, auto Size> {
    u8 raw[Size];
} [[sealed, format("mtext_format")]];

fn mtext_format(ref auto v) {
    str s;
    u128 a = addressof(v);
    for (u128 i = 0, i < sizeof(v), i += 1) {
        u8 c = unmask(v.Team, v.Start, a + i);
        if (c == 0)
            break;
        s += char(c);
    }
    return s;
};

struct MBytes<auto Team, auto Start, auto Size> {
    u8 raw[Size];
} [[sealed, format("mbytes_format")]];

fn mbytes_format(ref auto v) {
    return hex_bytes(addressof(v), sizeof(v), v.Team, v.Start);
};

// One color: red, green, blue, each 0-63.
struct MRGB<auto Team, auto Start> {
    u8 raw[3];
} [[sealed, format("mrgb_format")]];

fn mrgb_format(ref auto v) {
    u128 a = addressof(v);
    return std::format("{}, {}, {}",
        unmask(v.Team, v.Start, a),
        unmask(v.Team, v.Start, a + 1),
        unmask(v.Team, v.Start, a + 2));
};

fn stadium_type_format(ref auto v) {
    u8 x = mu8_value(v);
    match (x) {
        (0): return "0 (outdoor/grass)";
        (1): return "1 (other outdoor)";
        (2): return "2 (dome)";
        (_): return std::format("{}", x);
    }
};

fn computer_human_format(ref auto v) {
    u8 x = mu8_value(v);
    match (x) {
        (0): return "0 (Computer)";
        (1): return "1 (Human)";
        (_): return std::format("{}", x);
    }
};

fn mode_format(ref auto v) {
    u8 x = mu8_value(v);
    match (x) {
        (0): return "0 (Basic)";
        (1): return "1 (Standard)";
        (2): return "2 (Advanced)";
        (_): return std::format("{}", x);
    }
};

// ---- L03: league ----

struct League {
    char tag[4];
    u32 size;
    u8 unknown0;
    u8 conferences;
    u8 unknown2[6];
    u16 nextPlayerId;
    u16 baseYear;
    u8 unknownC[3];
    Text<25> name;
    Text<25> championship;
    u8 zero[17];
    u8 conferenceIds[conferences];
    u8 unknownTail[7];
    std::assert(tag == "L03:", "L03 chunk expected");
} [[format("league_format")]];

fn league_format(ref auto l) {
    return std::format("{} ({})", text_format(l.name), l.baseYear);
};

// ---- C03: conference ----

struct ConferenceChunk {
    char tag[4];
    u32 size;
    u8 id;
    u8 index;
    u8 divisions;
    u8 unknown3;
    Text<25> name;
    u8 divisionIds[divisions];
    std::assert(tag == "C03:", "C03 chunk expected");
};

// ---- D03: division ----

struct DivisionChunk {
    char tag[4];
    u32 size;
    u8 id;
    u8 conference;
    u8 index;
    u8 teams;
    Text<25> name;
    u8 teamNumbers[teams];
    std::assert(tag == "D03:", "D03 chunk expected");
};

// ---- T03: team, masked ----

struct Colors<auto Team, auto Start> {
    MRGB<Team, Start> helmet;
    MRGB<Team, Start> lightJersey [[comment("Also the shoes")]];
    MRGB<Team, Start> darkJersey;
    MRGB<Team, Start> lightPants [[comment("Also the helmet trim")]];
    MRGB<Team, Start> darkPants;
    MRGB<Team, Start> lightJerseyStripe;
    MRGB<Team, Start> darkJerseyStripe;
    MRGB<Team, Start> lightPantsStripe [[comment("Also the helmet stripe and facemask")]];
    MRGB<Team, Start> darkPantsStripe;
    MRGB<Team, Start> lightSockStripe;
    MRGB<Team, Start> darkSockStripe;
};

// Team Profile weights.
struct Profile<auto Team, auto Start> {
    MU8<Team, Start> passAggressive;
    MU8<Team, Start> passBalanced;
    MU8<Team, Start> passConservative;
    MU8<Team, Start> rushAggressive;
    MU8<Team, Start> rushBalanced;
    MU8<Team, Start> rushConservative;
};

struct TeamFields<auto Team, auto Start> {
    MU8<Team, Start> conference;
    MU8<Team, Start> division;
    MU8<Team, Start> slot;
    MU8<Team, Start> cityId [[comment("CITIES.DAT city id")]];
    MU8<Team, Start> stadiumType [[format("stadium_type_format")]];
    MU8<Team, Start> ownership [[format("computer_human_format")]];
    MU8<Team, Start> playcallMode [[format("mode_format")]];
    MU8<Team, Start> actionMode [[format("mode_format")]];
    MU8<Team, Start> management [[format("computer_human_format")]];
    Colors<Team, Start> colors;
    Profile<Team, Start> offenseProfile;
    Profile<Team, Start> defenseProfile;
    MText<Team, Start, 17> teamName;
    MText<Team, Start, 17> nickname;
    MText<Team, Start, 5> abbreviation;
    MText<Team, Start, 17> stadium;
    MText<Team, Start, 17> headCoach;
    MBytes<Team, Start, 19> unknown7F;
    MBytes<Team, Start, 15> zero;
    MText<Team, Start, 9> draftProfile;
};

struct TeamChunk {
    char tag[4];
    u32 size;
    u8 team;
    TeamFields<team, $> fields [[inline]];
    std::assert(tag == "T03:", "T03 chunk expected");
} [[format("team_chunk_format")]];

fn team_chunk_format(ref auto t) {
    return std::format("{} {} {}", t.team,
        mtext_format(t.fields.teamName), mtext_format(t.fields.nickname));
};

// ---- R03: roster, masked ----

struct RosterFields<auto Team, auto Start> {
    MU16<Team, Start> players[63] [[comment("Player ids (.pyr), 0 = empty. Slots 0-33 Assigned, 34-45 Open Active, 46-52 Open Inactive, 53-62 Injured Reserve")]];
    MU8<Team, Start> numbers[63] [[comment("Jersey number per slot")]];
    MBytes<Team, Start, 9> permutation;
    MBytes<Team, Start, 65> zero;
    MBytes<Team, Start, 60> table;
};

struct RosterChunk {
    char tag[4];
    u32 size;
    u16 team;
    RosterFields<team, $> fields [[inline]];
    std::assert(tag == "R03:", "R03 chunk expected");
};

// ---- Tree ----

struct Team {
    TeamChunk team;
    RosterChunk roster;
} [[format("team_format")]];

fn team_format(ref auto t) {
    return team_chunk_format(t.team);
};

struct Division {
    DivisionChunk division;
    Team teams[division.teams];
} [[format("division_format")]];

fn division_format(ref auto d) {
    return text_format(d.division.name);
};

struct Conference {
    ConferenceChunk conference;
    Division divisions[conference.divisions];
};

// ---- S03: schedule ----

struct Game {
    u8 teamA [[comment("Home team number; 0xFF when not yet known")]];
    u8 scoreA [[comment("0xFF when not played")]];
    u8 teamB [[comment("Away team number")]];
    u8 scoreB;
    u8 overtime;
    u8 status [[comment("0 played, 2 not played")]];
} [[format("game_format")]];

fn game_format(ref auto g) {
    str s = std::format("{} vs {}", g.teamA, g.teamB);
    if (g.status == 0)
        s += std::format(": {}-{}", g.scoreA, g.scoreB);
    if (g.overtime != 0)
        s += " OT";
    return s;
};

struct Week {
    u8 gameCount;
    Game games[gameCount];
} [[format("week_format")]];

fn week_format(ref auto w) {
    return std::format("{} games", w.gameCount);
};

struct Schedule {
    char tag[4];
    u32 size;
    u8 regularWeeks;
    u8 playoffRounds;
    u8 weeksPlayed;
    Week weeks[regularWeeks + playoffRounds];
    if ($ < addressof(this) + 8 + size)
        u8 leftover[addressof(this) + 8 + size - $];
    std::assert(tag == "S03:", "S03 chunk expected");
};

// ---- File ----

struct LeagueFile {
    League league;
    Conference conferences[league.conferences];
    Schedule schedule;
    if (!std::mem::eof())
        u8 trailing[std::mem::size() - $];
};

LeagueFile lge @ 0x00;
