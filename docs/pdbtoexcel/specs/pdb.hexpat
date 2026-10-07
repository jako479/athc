// WinLogStats .pdb — ImHex pattern for stats database files
// Source of truth: pdb.md
// Notes:
// - Hex Workshop had: #pragma byteorder(little_endian)
//   ImHex equivalent: #pragma endian little
// - The file has no header. It is a flat stream of tagged records,
//   each beginning with a 1-byte type tag (0 = PLAY, 1 = TENDENCY).
// - Records may appear in any order. EOF terminates the stream.

#pragma endian little
#pragma pattern_limit 200000

#include <std/sys.pat>

// ---- Record tag (first byte of every record) ----
enum RecordTag : u8 {
    PLAY     = 0,
    TENDENCY = 1
};

// ---- play_type (PLAY_DATA, offset 0x00) ----
enum PlayType : u32 {
    RUN     = 0,
    PASS    = 1,
    SPECIAL = 2,
    DEFENSE = 3,
    ONSIDE  = 5
};

// ---- PLAY_DATA body (256 bytes; follows a 0x00 tag byte) ----
//
// Offsets are relative to the start of this body (i.e. one byte after
// the RecordTag in the file).
//
// Notes (see pdb.md section 4):
// - play_count is inaccurate for defensive plays; it exceeds
//   run_plays_against + pass_plays_against, appearing to also count
//   snaps during special-teams plays.
// - QB scrambles are indistinguishable from incomplete passes
//   (0-yard pass play, no completion).
// - A sack on a "timed" pass play is logged as a run with negative yards;
//   the reader rebalances these via convert_invalid_play_data().
struct PlayData {
    PlayType play_type;                 // 0x00
    char     team_name[64];             // 0x04
    char     play_name[128];            // 0x44
    s32      total_yards;               // 0xC4  signed
    u32      play_count;                // 0xC8  see notes
    u32      completions;               // 0xCC  offense passes completed
    u32      sacks;                     // 0xD0
    u32      fumbles;                   // 0xD4
    u32      interceptions;             // 0xD8
    u32      touchdowns_offense;        // 0xDC
    u32      touchdowns_defense;        // 0xE0
    s32      unknown1;                  // 0xE4  observed 0
    s32      unknown2;                  // 0xE8  observed 0
    u32      points_scored;             // 0xEC  ignored by readers
    u32      run_plays_against;         // 0xF0  defense
    u32      pass_plays_against;        // 0xF4  defense (includes sacks)
    s32      rush_yards_allowed;        // 0xF8  defense
    s32      pass_yards_allowed;        // 0xFC  defense
                                        // 0x100 (256 bytes total)
};

// ---- SITUATION (16 bytes; play counts split by down) ----
struct Situation {
    u32 first_down;     // 0x00
    u32 second_down;    // 0x04
    u32 third_down;     // 0x08
    u32 fourth_down;    // 0x0C
                        // 0x10
};

// ---- TENDENCY_DATA body (192 bytes; follows a 0x01 tag byte) ----
//
// Eight Situation blocks: run/pass × four yards-to-go buckets
// (0-1, 2-5, 6-10, >10).
struct TendencyData {
    char      team_name[64];            // 0x00
    Situation run_zero_to_one;          // 0x40
    Situation pass_zero_to_one;         // 0x50
    Situation run_two_to_five;          // 0x60
    Situation pass_two_to_five;         // 0x70
    Situation run_six_to_ten;           // 0x80
    Situation pass_six_to_ten;          // 0x90
    Situation run_ten_plus;             // 0xA0
    Situation pass_ten_plus;            // 0xB0
                                        // 0xC0 (192 bytes total)
};

// ---- One tagged record ----
struct Record {
    RecordTag tag;
    if (tag == RecordTag::PLAY) {
        PlayData play;
    } else if (tag == RecordTag::TENDENCY) {
        TendencyData tendency;
    } else {
        std::assert(false, "Unknown record tag");
    }
};

// ---- Top-level file: stream of records until EOF ----
struct PdbFile {
    Record records[while(!std::mem::eof())];
};


PdbFile pdbfile_at_0x00 @ 0x00;
