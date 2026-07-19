"""Compute 2047 SOS (avg opponent 2046-rank) and order the tied teams by it."""

from collections import defaultdict

# 2046 final rank of each team, mapped to 2047 names (relocations: Houston->Miami,
# New York A->Baltimore, Indianapolis->Cincinnati, New York N->New York).
RANK_2046 = {
    "Pittsburgh": 1,
    "Washington": 2,
    "Minnesota": 3,
    "Baltimore": 4,
    "Miami": 5,
    "Buffalo": 6,
    "Seattle": 7,
    "San Francisco": 8,
    "Cincinnati": 9,
    "Las Vegas": 10,
    "Green Bay": 11,
    "Chicago": 12,
    "Philadelphia": 13,
    "Denver": 14,
    "Jacksonville": 15,
    "Atlanta": 16,
    "New York": 17,
    "New England": 18,
}

# 2047 regular season, weeks 1-16, "Away @ Home".
SCHEDULE = """
Pittsburgh @ New England | Las Vegas @ Seattle | Denver @ Buffalo | Baltimore @ Cincinnati | Washington @ Jacksonville | Atlanta @ Miami | New York @ Philadelphia | San Francisco @ Chicago | Green Bay @ Minnesota
Miami @ New England | Jacksonville @ Pittsburgh | Denver @ Baltimore | Washington @ Chicago | Philadelphia @ Las Vegas | New York @ Atlanta | Seattle @ Buffalo | San Francisco @ Minnesota | Green Bay @ Cincinnati
Buffalo @ New England | Jacksonville @ Baltimore | Pittsburgh @ Minnesota | Las Vegas @ Miami | Cincinnati @ Denver | Washington @ New York | Philadelphia @ Atlanta | Chicago @ Seattle | Green Bay @ San Francisco
Miami @ Denver | New England @ Las Vegas | Pittsburgh @ Cincinnati | Baltimore @ Buffalo | Atlanta @ Jacksonville | New York @ Washington | Minnesota @ Green Bay | Seattle @ Philadelphia | Chicago @ San Francisco
Miami @ Seattle | Buffalo @ Jacksonville | Pittsburgh @ Baltimore | Las Vegas @ Washington | Philadelphia @ Green Bay | New York @ Denver | Minnesota @ Atlanta | San Francisco @ New England | Chicago @ Cincinnati
Buffalo @ New York | Jacksonville @ Miami | New England @ Philadelphia | Denver @ Chicago | Cincinnati @ Pittsburgh | Baltimore @ Las Vegas | Washington @ Atlanta | Minnesota @ San Francisco | Green Bay @ Seattle
Las Vegas @ Jacksonville | Denver @ New England | Cincinnati @ Baltimore | Washington @ Pittsburgh | Philadelphia @ Buffalo | Atlanta @ Chicago | Minnesota @ Miami | Seattle @ New York | San Francisco @ Green Bay
Miami @ Jacksonville | Buffalo @ Las Vegas | New England @ Cincinnati | Pittsburgh @ Denver | Philadelphia @ San Francisco | Atlanta @ Washington | New York @ Green Bay | Seattle @ Minnesota | Chicago @ Baltimore
Buffalo @ Cincinnati | Jacksonville @ New York | New England @ Miami | Baltimore @ Denver | Minnesota @ Las Vegas | Seattle @ Pittsburgh | San Francisco @ Washington | Chicago @ Philadelphia | Green Bay @ Atlanta
Buffalo @ Miami | Las Vegas @ Pittsburgh | Cincinnati @ Jacksonville | Baltimore @ New England | Philadelphia @ Washington | Atlanta @ Denver | New York @ Minnesota | San Francisco @ Seattle | Green Bay @ Chicago
New England @ Jacksonville | Pittsburgh @ Buffalo | Denver @ Green Bay | Cincinnati @ Las Vegas | Baltimore @ San Francisco | Washington @ Miami | Philadelphia @ Minnesota | Atlanta @ New York | Seattle @ Chicago
Miami @ Pittsburgh | Jacksonville @ Buffalo | Las Vegas @ Denver | Cincinnati @ San Francisco | Washington @ Seattle | Atlanta @ Philadelphia | New York @ Baltimore | Minnesota @ Chicago | Green Bay @ New England
Miami @ Buffalo | Jacksonville @ New England | Pittsburgh @ Las Vegas | Denver @ Cincinnati | Baltimore @ Green Bay | Washington @ Philadelphia | Minnesota @ Seattle | San Francisco @ Atlanta | Chicago @ New York
Miami @ Philadelphia | Buffalo @ Washington | Jacksonville @ Denver | New England @ Atlanta | Las Vegas @ Cincinnati | Baltimore @ Pittsburgh | New York @ San Francisco | Seattle @ Green Bay | Chicago @ Minnesota
New England @ Buffalo | Las Vegas @ Baltimore | Denver @ Pittsburgh | Cincinnati @ Miami | Philadelphia @ New York | Atlanta @ Seattle | Minnesota @ Washington | San Francisco @ Jacksonville | Chicago @ Green Bay
Miami @ Baltimore | Buffalo @ Minnesota | Jacksonville @ Chicago | New England @ New York | Pittsburgh @ Philadelphia | Denver @ Las Vegas | Cincinnati @ Atlanta | Seattle @ San Francisco | Green Bay @ Washington
"""

# 2047 in-season win-equivalent (W + 0.5*T) for the standard SOS variant.
WINEQ_2047 = {
    "Miami": 11.0,
    "New England": 7.5,
    "Jacksonville": 6.0,
    "Buffalo": 4.0,
    "Baltimore": 13.0,
    "Denver": 9.5,
    "Las Vegas": 8.0,
    "Cincinnati": 7.0,
    "Pittsburgh": 5.5,
    "Washington": 9.5,
    "Atlanta": 9.0,
    "New York": 7.0,
    "Philadelphia": 6.0,
    "Chicago": 12.0,
    "Minnesota": 11.0,
    "Green Bay": 7.0,
    "San Francisco": 6.0,
    "Seattle": 5.0,
}

opponents: dict[str, list[str]] = defaultdict(list)
for line in SCHEDULE.strip().splitlines():
    for game in line.split("|"):
        away, home = (t.strip() for t in game.split("@"))
        opponents[away].append(home)
        opponents[home].append(away)

# Sanity: every team plays 16 games.
for team, opps in opponents.items():
    assert len(opps) == 16, f"{team}: {len(opps)} games"

# Two SOS variants: opponents' prior-season (2046) rank, and opponents'
# current-season (2047) record.
sos_rank = {t: sum(RANK_2046[o] for o in o2) / 16 for t, o2 in opponents.items()}
sos_rec = {t: sum(WINEQ_2047[o] for o in o2) / 16 for t, o2 in opponents.items()}

# Tied groups (2047 records) and the real 2048.league.ini order to reproduce.
groups = {
    "9-6-1": (["Denver", "Washington"], ["Denver", "Washington"]),
    "7-9-0": (
        ["New York", "Cincinnati", "Green Bay"],
        ["Green Bay", "Cincinnati", "New York"],
    ),
    "6-10-0": (
        ["Jacksonville", "Philadelphia", "San Francisco"],
        ["San Francisco", "Jacksonville", "Philadelphia"],
    ),
}

for rec, (teams, real_order) in groups.items():
    print(f"\n{rec}:   real file -> {real_order}")
    for t in real_order:
        print(
            f"  {t:<14} opp-2046-rank {sos_rank[t]:5.2f}   opp-2047-wins {sos_rec[t]:5.2f}"
        )
    by_rank = sorted(teams, key=lambda t: sos_rank[t])  # lower rank = tougher
    by_rec = sorted(teams, key=lambda t: -sos_rec[t])  # higher opp wins = tougher
    tag = lambda order: "MATCH" if order == real_order else "no"
    print(f"  by opp-2046-rank (tough->easy): {by_rank}  [{tag(by_rank)}]")
    print(f"  by opp-2047-wins (tough->easy): {by_rec}  [{tag(by_rec)}]")
