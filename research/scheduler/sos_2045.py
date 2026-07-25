"""Build the 2045 final ranking (SOS tiebreaks) -> 2046.league.ini standings.
2045->2046 relocation: Los Angeles -> Buffalo (only roster change)."""

from collections import defaultdict

WINEQ = {
    "New York A": 11,
    "Indianapolis": 8,
    "New England": 7,
    "Jacksonville": 4,
    "Washington": 13,
    "Philadelphia": 12,
    "Atlanta": 2,
    "New York N": 2,
    "Houston": 11,
    "Denver": 11,
    "Pittsburgh": 10,
    "Los Angeles": 9,
    "Las Vegas": 3,
    "Minnesota": 12,
    "San Francisco": 11,
    "Chicago": 8,
    "Seattle": 6,
    "Green Bay": 4,
}

SCHEDULE = """
New England @ New York A | Pittsburgh @ Houston | Los Angeles @ Indianapolis | Denver @ Jacksonville | New York N @ Washington | Philadelphia @ Las Vegas | Atlanta @ Minnesota | Chicago @ San Francisco | Green Bay @ Seattle
New York A @ Houston | Indianapolis @ New England | Las Vegas @ Pittsburgh | Los Angeles @ Seattle | Washington @ Chicago | New York N @ Philadelphia | Atlanta @ Denver | Minnesota @ San Francisco | Green Bay @ Jacksonville
New York A @ New England | Jacksonville @ Indianapolis | Houston @ Pittsburgh | Las Vegas @ Los Angeles | Denver @ Green Bay | Washington @ New York N | Chicago @ Minnesota | San Francisco @ Philadelphia | Seattle @ Atlanta
New York A @ Las Vegas | Jacksonville @ Pittsburgh | Houston @ Los Angeles | Denver @ New England | Philadelphia @ Indianapolis | Atlanta @ Washington | Minnesota @ Green Bay | Chicago @ New York N | Seattle @ San Francisco
Pittsburgh @ Indianapolis | Las Vegas @ Jacksonville | Los Angeles @ Denver | Washington @ Houston | New York N @ New England | Philadelphia @ Seattle | Minnesota @ New York A | Chicago @ Atlanta | Green Bay @ San Francisco
New England @ Atlanta | Indianapolis @ New York A | Jacksonville @ New York N | Las Vegas @ San Francisco | Los Angeles @ Houston | Denver @ Pittsburgh | Philadelphia @ Washington | Seattle @ Minnesota | Green Bay @ Chicago
New York A @ Chicago | New England @ Indianapolis | Houston @ Denver | Pittsburgh @ Washington | New York N @ Green Bay | Atlanta @ Los Angeles | Minnesota @ Philadelphia | San Francisco @ Jacksonville | Seattle @ Las Vegas
Houston @ Jacksonville | Pittsburgh @ Chicago | Las Vegas @ New England | Denver @ Los Angeles | Washington @ Indianapolis | Philadelphia @ New York A | Atlanta @ New York N | San Francisco @ Seattle | Green Bay @ Minnesota
New York A @ Jacksonville | New England @ Los Angeles | Indianapolis @ Atlanta | Denver @ Las Vegas | Minnesota @ Pittsburgh | Chicago @ Houston | San Francisco @ Washington | Seattle @ New York N | Green Bay @ Philadelphia
New York A @ New York N | New England @ Washington | Indianapolis @ Las Vegas | Jacksonville @ Philadelphia | Los Angeles @ Pittsburgh | Denver @ Houston | Atlanta @ San Francisco | Minnesota @ Seattle | Chicago @ Green Bay
New England @ Jacksonville | Houston @ Las Vegas | Pittsburgh @ Denver | Los Angeles @ New York A | New York N @ Atlanta | Philadelphia @ Chicago | Minnesota @ Washington | San Francisco @ Indianapolis | Seattle @ Green Bay
Indianapolis @ Houston | Jacksonville @ New York A | Las Vegas @ Denver | Washington @ Seattle | New York N @ Pittsburgh | Atlanta @ Philadelphia | Chicago @ New England | San Francisco @ Minnesota | Green Bay @ Los Angeles
New York A @ Denver | New England @ Minnesota | Indianapolis @ Seattle | Jacksonville @ Atlanta | Houston @ New York N | Pittsburgh @ Las Vegas | Los Angeles @ Philadelphia | San Francisco @ Chicago | Green Bay @ Washington
Indianapolis @ Jacksonville | Houston @ New England | Pittsburgh @ Los Angeles | Las Vegas @ Green Bay | Denver @ San Francisco | Washington @ New York A | New York N @ Minnesota | Philadelphia @ Atlanta | Chicago @ Seattle
New York A @ Indianapolis | New England @ Pittsburgh | Jacksonville @ Los Angeles | Las Vegas @ Houston | Washington @ Philadelphia | New York N @ San Francisco | Atlanta @ Green Bay | Minnesota @ Chicago | Seattle @ Denver
Indianapolis @ Denver | Jacksonville @ New England | Houston @ Minnesota | Pittsburgh @ New York A | Los Angeles @ Las Vegas | Washington @ Atlanta | Philadelphia @ New York N | San Francisco @ Green Bay | Seattle @ Chicago
"""

opp = defaultdict(list)
for line in SCHEDULE.strip().splitlines():
    for game in line.split("|"):
        a, h = (t.strip() for t in game.split("@"))
        opp[a].append(h)
        opp[h].append(a)
for t, o in opp.items():
    assert len(o) == 16, f"{t}: {len(o)}"

sos = {t: sum(WINEQ[x] for x in o) for t, o in opp.items()}
def hi(teams):  # tougher (higher) first
    return sorted(teams, key=lambda t: -sos[t])

# Tie groups needing SOS, with the 2045 division-standing order as the listed
# fallback if SOS ties (only matters for same-division pairs).
print("SOS tie groups (opp win-sum):")
for label, teams in [
    ("3-4  CC losers 11-5", ["New York A", "San Francisco"]),
    ("10-11  8-8", ["Indianapolis", "Chicago"]),
    ("14-15  4-12", ["Jacksonville", "Green Bay"]),
    ("17-18  2-14", ["Atlanta", "New York N"]),
]:
    print(f"  {label:<22}: " + ", ".join(f"{t}({sos[t]})" for t in hi(teams)))

final = [
    "Houston",
    "Minnesota",  # SB W, SB L
    *hi(["New York A", "San Francisco"]),  # CC losers (tie)
    "Washington",
    "Philadelphia",
    "Denver",
    "Pittsburgh",  # WC losers by record
    "Los Angeles",  # 9-7
    *hi(["Indianapolis", "Chicago"]),  # 8-8 (tie)
    "New England",  # 7-9
    "Seattle",  # 6-10
    *hi(["Jacksonville", "Green Bay"]),  # 4-12 (tie)
    "Las Vegas",  # 3-13
    *hi(["Atlanta", "New York N"]),  # 2-14 (tie)
]
assert len(final) == 18 and len(set(final)) == 18

RENAME = {"Los Angeles": "Buffalo"}  # 2045 -> 2046
print("\n2046.league.ini [OverallStandings] (2045 final, 2046 names):")
for i, t in enumerate(final, 1):
    print(f"  {i:>2}  {RENAME.get(t, t)}")
