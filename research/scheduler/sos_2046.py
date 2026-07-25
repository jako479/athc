"""Break 2046's record-ties by SOS (opponents' 2046 records), build the 2046
final ranking, and emit it in 2047 names for 2047.league.ini."""

from collections import defaultdict

# 2046 win-equivalent (all T=0 in 2046).
WINEQ = {
    "New York A": 11,
    "Buffalo": 10,
    "Indianapolis": 9,
    "New England": 3,
    "Washington": 11,
    "Philadelphia": 6,
    "Atlanta": 5,
    "New York N": 5,
    "Pittsburgh": 13,
    "Houston": 11,
    "Las Vegas": 8,
    "Jacksonville": 5,
    "Denver": 5,
    "Minnesota": 13,
    "Seattle": 9,
    "San Francisco": 8,
    "Chicago": 6,
    "Green Bay": 6,
}

SCHEDULE = """
Buffalo @ New York A | New England @ Indianapolis | Denver @ Houston | Pittsburgh @ Las Vegas | Jacksonville @ Seattle | Philadelphia @ Washington | Minnesota @ San Francisco | Chicago @ Atlanta | Green Bay @ New York N
Buffalo @ Denver | Indianapolis @ New York A | Pittsburgh @ Houston | Las Vegas @ Green Bay | Philadelphia @ Minnesota | Washington @ Atlanta | New York N @ Jacksonville | San Francisco @ Chicago | Seattle @ New England
New York A @ Buffalo | Houston @ Denver | Las Vegas @ Indianapolis | Jacksonville @ New England | Washington @ Philadelphia | Atlanta @ Pittsburgh | New York N @ San Francisco | Minnesota @ Chicago | Seattle @ Green Bay
Indianapolis @ Jacksonville | New England @ New York A | Denver @ San Francisco | Houston @ Buffalo | Las Vegas @ Pittsburgh | Philadelphia @ New York N | Atlanta @ Washington | Chicago @ Seattle | Green Bay @ Minnesota
Buffalo @ Indianapolis | New York A @ Houston | New England @ Las Vegas | Pittsburgh @ Denver | Philadelphia @ Atlanta | Washington @ Chicago | New York N @ Seattle | San Francisco @ Minnesota | Green Bay @ Jacksonville
Indianapolis @ New England | Denver @ New York A | Houston @ Las Vegas | Pittsburgh @ Seattle | Jacksonville @ Chicago | Philadelphia @ Buffalo | Washington @ San Francisco | Atlanta @ New York N | Minnesota @ Green Bay
Buffalo @ Jacksonville | New York A @ San Francisco | Indianapolis @ Green Bay | New England @ New York N | Denver @ Washington | Houston @ Pittsburgh | Las Vegas @ Atlanta | Chicago @ Minnesota | Seattle @ Philadelphia
Indianapolis @ Denver | New England @ Buffalo | Pittsburgh @ Jacksonville | Philadelphia @ Green Bay | Washington @ Houston | New York N @ Atlanta | Minnesota @ New York A | Chicago @ San Francisco | Seattle @ Las Vegas
New York A @ New England | Denver @ Pittsburgh | Houston @ Jacksonville | Las Vegas @ Buffalo | Washington @ New York N | Atlanta @ Minnesota | San Francisco @ Philadelphia | Chicago @ Indianapolis | Green Bay @ Seattle
Buffalo @ Washington | New York A @ Philadelphia | Indianapolis @ Pittsburgh | New England @ Atlanta | Las Vegas @ Houston | Jacksonville @ Denver | New York N @ Chicago | San Francisco @ Green Bay | Minnesota @ Seattle
Buffalo @ New England | New York A @ Las Vegas | Indianapolis @ New York N | Jacksonville @ Pittsburgh | San Francisco @ Houston | Minnesota @ Denver | Chicago @ Philadelphia | Green Bay @ Washington | Seattle @ Atlanta
Denver @ New England | Houston @ Minnesota | Pittsburgh @ New York A | Jacksonville @ Las Vegas | Philadelphia @ Indianapolis | Atlanta @ Buffalo | New York N @ Washington | Chicago @ Green Bay | Seattle @ San Francisco
Buffalo @ Minnesota | New York A @ Indianapolis | Denver @ Jacksonville | Houston @ Philadelphia | Washington @ Seattle | New York N @ Pittsburgh | San Francisco @ Atlanta | Chicago @ New England | Green Bay @ Las Vegas
New York A @ New York N | Indianapolis @ Buffalo | New England @ Washington | Pittsburgh @ Chicago | Las Vegas @ Denver | Jacksonville @ Houston | Atlanta @ Philadelphia | Green Bay @ San Francisco | Seattle @ Minnesota
Houston @ Indianapolis | Pittsburgh @ New England | Las Vegas @ Jacksonville | Philadelphia @ Denver | Washington @ New York A | Atlanta @ Green Bay | San Francisco @ Buffalo | Minnesota @ New York N | Seattle @ Chicago
Buffalo @ Pittsburgh | New England @ Houston | Denver @ Las Vegas | Jacksonville @ New York A | Atlanta @ Indianapolis | New York N @ Philadelphia | San Francisco @ Seattle | Minnesota @ Washington | Green Bay @ Chicago
"""

opp = defaultdict(list)
for line in SCHEDULE.strip().splitlines():
    for game in line.split("|"):
        a, h = (t.strip() for t in game.split("@"))
        opp[a].append(h)
        opp[h].append(a)
for t, o in opp.items():
    assert len(o) == 16, f"{t}: {len(o)}"

sos = {t: sum(WINEQ[o2] for o2 in o) for t, o in opp.items()}

# Two non-playoff record-ties needing SOS (tougher = higher opp wins = ranked higher).
for rec, teams in [
    ("6-10", ["Philadelphia", "Chicago", "Green Bay"]),
    ("5-11", ["Jacksonville", "Denver", "Atlanta", "New York N"]),
]:
    order = sorted(teams, key=lambda t: -sos[t])
    print(f"{rec}: " + ", ".join(f"{t}({sos[t]})" for t in order))

# Full 2046 final ranking (playoff tiers fixed; ties filled by SOS above).
final_2046 = [
    "Pittsburgh",
    "Washington",
    "Minnesota",
    "New York A",  # SB W/L, CC losers
    "Houston",
    "Buffalo",
    "Seattle",
    "San Francisco",  # WC losers by record
    "Indianapolis",
    "Las Vegas",  # 9-7, 8-8
    *sorted(["Philadelphia", "Chicago", "Green Bay"], key=lambda t: -sos[t]),
    *sorted(["Jacksonville", "Denver", "Atlanta", "New York N"], key=lambda t: -sos[t]),
    "New England",
]
assert len(final_2046) == 18 and len(set(final_2046)) == 18

RENAME = {
    "Houston": "Miami",
    "New York A": "Baltimore",
    "Indianapolis": "Cincinnati",
    "New York N": "New York",
}
print("\n2047.league.ini [OverallStandings] (2046 final, 2047 names):")
for i, t in enumerate(final_2046, 1):
    print(f"  {i:>2}  {RENAME.get(t, t)}")
