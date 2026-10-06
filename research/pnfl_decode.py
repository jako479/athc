"""Read-only decoder for FbPro98 league files (PNFL.*). Stdlib only.

usage: python pnfl_decode.py <game folder> <what> [arg]
  what: league | teams | roster <team#> | player <id> | freeagents | schedule |
        champions | draft | tmn | stats <id|team#> | dump

Findings this is based on: docs/design/research/pnfl-formats.md.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

POS = {
    0: "QB",
    1: "FB",
    2: "HB",
    3: "TE",
    4: "WR",
    5: "C",
    6: "G",
    7: "T",
    8: "DE",
    9: "DT",
    10: "LB",
    11: "CB",
    12: "S",
    13: "K",
    14: "P",
}
ATTR = ["AC", "AG", "DI", "EN", "HA", "IN", "SP", "ST"]  # file order (alphabetical)
STAT_CAT = {
    0: "field goals (att, made)",
    1: "kicking detail (unresolved)",
    2: "rushing (att, yds, long, td)",
    3: "passing (att, yds, long, td, comp, int, sacked, sack yds)",
    4: "receiving (rec, yds, long, td)",
    5: "interceptions (int, yds, long, td)",
    6: "punting (punts, yds, long, ?, ?, ?, ?, ?)",
    7: "punt returns (ret, yds, long, td, fc?)",
    8: "kick returns (ret, yds, long, td)",
    9: "fumbles (n)",
    10: "fumble recoveries (n, yds, long, td)",
    11: "sacks (n)",
    12: "unknown defensive count",
    13: "tackles (n)",
    14: "misc/participation (unresolved)",
    15: "unresolved",
    16: "unresolved",
    17: "unresolved (2-pt conv?)",
}
STAT_BLOCK = [
    (0, 32, "player, last game"),
    (32, 32, "player, season"),
    (64, 32, "player, career"),
    (96, 34, "team, last game"),
    (130, 34, "team, season"),
    (164, 34, "team block 3"),
    (198, 34, "team block 4"),
]


def cstr(b: bytes) -> str:
    return b.split(b"\x00")[0].decode("latin1")


def chunks(buf: bytes):
    off = 0
    while off < len(buf):
        tag = buf[off : off + 4].decode("latin1")
        ln = struct.unpack_from("<I", buf, off + 4)[0]
        yield tag, buf[off + 8 : off + 8 + ln]
        off += 8 + ln


def unmask(team: int, data: bytes) -> bytes:
    """Team-numbered chunks (T03/R03): byte i is XORed with (0x69*team + i) & 0xFF."""
    return bytes(x ^ ((0x69 * team + i) & 0xFF) for i, x in enumerate(data))


# ---------------------------------------------------------------- players (.pyr)
def sbox_from_pyr(pyr: bytes) -> dict[int, int]:
    """The .pyr cipher is a fixed byte substitution. Bytes 0-1 of record i hold
    player id i+100, so the file itself yields the whole table."""
    table: dict[int, int] = {}
    n = (len(pyr) - 60) // 60
    for i in range(n):
        r = pyr[60 + i * 60 : 60 + i * 60 + 60]
        pid = i + 100
        table.setdefault(pid & 0xFF, r[0])
        table.setdefault(pid >> 8, r[1])
    return table


def parse_players(pyr: bytes) -> dict[int, dict]:
    inv = {c: p for p, c in sbox_from_pyr(pyr).items()}
    out = {}
    n = (len(pyr) - 60) // 60
    for i in range(n):
        p = bytes(inv[x] for x in pyr[60 + i * 60 : 60 + i * 60 + 60])
        out[i + 100] = {
            "id": struct.unpack_from("<H", p, 0)[0],
            "first": cstr(p[2:15]),
            "last": cstr(p[15:28]),
            "potential": dict(zip(ATTR, p[28:36], strict=True)),
            "injury": tuple(p[36:40]),  # all zero when healthy
            "group": p[40],
            "pos": POS.get(p[41], str(p[41])),
            "actual": dict(zip(ATTR, p[42:50], strict=True)),
            "years": p[50],
            "height_in": p[51],
            "weight_lb": struct.unpack_from("<H", p, 52)[
                0
            ],  # only filled for newest draft class
            "tail": tuple(p[54:60]),
        }
    return out


# ---------------------------------------------------------------- league (.lge)
def parse_lge(lge: bytes) -> dict:
    league = {
        "conferences": [],
        "divisions": [],
        "teams": {},
        "rosters": {},
        "schedule": None,
    }
    for tag, d in chunks(lge):
        if tag == "L03:":
            league["league"] = {
                "raw_head": d[:16].hex(" "),
                "next_player_id": struct.unpack_from("<H", d, 8)[0],
                "base_year": struct.unpack_from("<H", d, 10)[0],
                "name": cstr(d[15:40]),
                "championship": cstr(d[40:65]),
            }
        elif tag == "C03:":
            league["conferences"].append(
                {"id": d[0], "index": d[1], "divisions": list(d[29:])}
            )
        elif tag == "D03:":
            league["divisions"].append(
                {
                    "id": d[0],
                    "conf": d[1],
                    "index": d[2],
                    "name": cstr(d[4:29]),
                    "teams": list(d[29:]),
                }
            )
        elif tag == "T03:":
            n = d[0]
            p = unmask(n, d[1:])
            league["teams"][n] = {
                "conf": p[0],
                "div": p[1],
                "slot": p[2],
                "city_index": p[3],
                "stadium_type": p[4],
                "colors": [
                    tuple(p[9 + 3 * k : 12 + 3 * k]) for k in range(11)
                ],  # RGB 0-63
                "city": cstr(p[54:71]),
                "nickname": cstr(p[71:88]),
                "abbr": cstr(p[88:93]),
                "stadium": cstr(p[93:110]),
                "owner": cstr(p[110:127]),
                "unknown_128_145": p[128:146].hex(" "),
                "uniform": cstr(p[161:170]),
            }
        elif tag == "R03:":
            n = struct.unpack_from("<H", d, 0)[0]
            p = unmask(n, d[2:])
            ids = list(struct.unpack_from("<63H", p, 0))
            nums = list(p[126:189])
            league["rosters"][n] = {
                "slots": [(pid, num) for pid, num in zip(ids, nums, strict=True)],
                "perm9": list(p[189:198]),
                "const60": p[263:323].hex(" "),
            }
        elif tag == "S03:":
            weeks = []
            pos = 3
            while pos < len(d):
                cnt = d[pos]
                pos += 1
                weeks.append(
                    [tuple(d[pos + 6 * g : pos + 6 * g + 6]) for g in range(cnt)]
                )
                pos += 6 * cnt
            league["schedule"] = {
                "regular_weeks": d[0],
                "playoff_rounds": d[1],
                "weeks_played": d[2],
                "weeks": weeks,
            }
    return league


# ---------------------------------------------------------------- small files
def parse_idlist(buf: bytes) -> list[int]:  # PNFL.PYF / PNFL.PYC ("PPD:")
    return list(struct.unpack_from(f"<{(len(buf) - 8) // 2}H", buf, 8))


def parse_dft(buf: bytes) -> list[int]:  # draft order, team numbers
    body = buf[8:]
    return [body[i] for i in range(3, len(body), 2)]


def parse_tmn(buf: bytes) -> list[tuple[int, int]]:  # (team, player id)
    return [
        (buf[i], struct.unpack_from("<H", buf, i + 1)[0]) for i in range(3, len(buf), 3)
    ]


def parse_lgc(buf: bytes) -> list[tuple[str, int, str, int]]:  # championship history
    out = []
    for i in range(0, len(buf), 44):
        r = buf[i + 8 : i + 44]
        out.append((cstr(r[0:17]), r[17], cstr(r[18:35]), r[35]))
    return out


# ---------------------------------------------------------------- stats (.dat)
def parse_stats(dat: bytes) -> list[tuple[int, int, tuple[int, ...]]]:
    """20-byte records at a 20-byte stride: type u16, id u16, 8 x int16.
    Unused trailing fields hold leftover memory, not zeros."""
    out = []
    for off in range(0, len(dat) - 20, 20):
        ty, rid = struct.unpack_from("<HH", dat, off)
        if ty <= 255 and (100 <= rid < 10000 or 1 <= rid <= 18):
            out.append((ty, rid, struct.unpack_from("<8h", dat, off + 4)))
    return out


def stat_label(ty: int) -> str:
    for base, width, name in STAT_BLOCK:
        if base <= ty < base + width:
            return f"{name}: {STAT_CAT.get(ty - base, '?')}"
    return "?"


# ---------------------------------------------------------------- main
def main(argv: list[str]) -> None:
    folder = Path(argv[1])
    what = argv[2] if len(argv) > 2 else "dump"
    arg = argv[3] if len(argv) > 3 else None

    def rd(name: str) -> bytes:
        return (folder / name).read_bytes()

    players = parse_players(rd("PNFL.pyr"))
    lg = parse_lge(rd("PNFL.lge"))

    def name(pid: int) -> str:
        if pid in players:
            return f"{players[pid]['first']} {players[pid]['last']}"
        return f"#{pid}"

    if what == "league":
        print(lg["league"])
        for c in lg["conferences"]:
            print("conference", c)
        for dv in lg["divisions"]:
            print("division", dv)
    elif what == "teams":
        for n, t in lg["teams"].items():
            print(
                n,
                t["city"],
                t["nickname"],
                t["abbr"],
                "|",
                t["stadium"],
                "|",
                t["owner"],
                "|",
                t["uniform"],
                "| colors",
                t["colors"][:3],
                "...",
            )
    elif what == "roster":
        n = int(arg)
        for slot, (pid, num) in enumerate(lg["rosters"][n]["slots"]):
            if pid:
                v = players[pid]
                print(
                    f"slot {slot:2d} #{num:2d} {pid:5d} {v['first']} {v['last']:14s} {v['pos']:2s} yrs={v['years']:2d} act={list(v['actual'].values())} inj={v['injury']}"
                )
    elif what == "player":
        print(players[int(arg)])
    elif what == "freeagents":
        for pid in parse_idlist(rd("PNFL.PYF")):
            print(pid, name(pid), players[pid]["pos"])
    elif what == "schedule":
        s = lg["schedule"]
        print(
            "regular weeks",
            s["regular_weeks"],
            "playoff rounds",
            s["playoff_rounds"],
            "weeks played",
            s["weeks_played"],
        )
        for w, games in enumerate(s["weeks"], start=1):
            print(
                f"week {w}:",
                "  ".join(
                    f"{a}:{sa}-{b}:{sb}" if sa != 255 else f"{a}-{b}"
                    for a, sa, b, sb, _ot, _st in games
                ),
            )
    elif what == "champions":
        for k, (w, ws, loser, ls) in enumerate(parse_lgc(rd("pnfl.lgc")), start=1):
            print(f"{k:2d} {w} {ws} - {loser} {ls}")
    elif what == "draft":
        print([(n, lg["teams"][n]["city"]) for n in parse_dft(rd("PNFL.dft"))])
    elif what == "tmn":
        for team, pid in parse_tmn(rd("PNFL.tmn")):
            print(team, lg["teams"][team]["city"], pid, name(pid))
    elif what == "stats":
        key = int(arg)
        for ty, rid, st in sorted(parse_stats(rd("PNFL.dat"))):
            if rid == key:
                print(f"type {ty:3d} {stat_label(ty):70s} {st}")
    else:
        print(
            "teams:",
            len(lg["teams"]),
            "players:",
            len(players),
            "stat records:",
            len(parse_stats(rd("PNFL.dat"))),
        )


if __name__ == "__main__":
    main(sys.argv)
