"""Compare the point-diff candidate 2048 standings against the real file."""

from athc.scheduler.config import load_league

real = [t.metro for t in load_league("release/2048.league.ini").rankings.overall]
cand = [
    t.metro
    for t in load_league(
        "research/scheduler/2048_pointdiff.league.ini"
    ).rankings.overall
]

print(
    f"{'rank':>4} | {'real 2048.league.ini':<22} | {'point-diff candidate':<22} | match"
)
for i, (r, c) in enumerate(zip(real, cand, strict=True), 1):
    print(f"{i:>4} | {r:<22} | {c:<22} | {'OK' if r == c else 'X'}")
print("exact matches:", sum(r == c for r, c in zip(real, cand, strict=True)), "/ 18")
