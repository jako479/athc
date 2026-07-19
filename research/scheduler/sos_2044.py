"""Build the 2044 final ranking (SOS tiebreaks) -> 2045.league.ini standings.
No 2044->2045 relocation (rosters identical)."""

from collections import defaultdict

WINEQ = {
    "New York A": 14,
    "New England": 6,
    "Indianapolis": 6,
    "Jacksonville": 4,
    "Washington": 10,
    "New York N": 7,
    "Philadelphia": 6,
    "Atlanta": 5,
    "Houston": 11,
    "Pittsburgh": 11,
    "Las Vegas": 8,
    "Los Angeles": 7,
    "Denver": 7,
    "Minnesota": 13,
    "Chicago": 12,
    "San Francisco": 9,
    "Seattle": 4,
    "Green Bay": 4,
}

SCHEDULE = """
New England @ Houston | Jacksonville @ New York A | Las Vegas @ Denver | Washington @ Seattle | Philadelphia @ Los Angeles | Atlanta @ New York N | San Francisco @ Indianapolis | Minnesota @ Chicago | Green Bay @ Pittsburgh
New York A @ Denver | Indianapolis @ Chicago | New England @ Seattle | Jacksonville @ Atlanta | Houston @ Philadelphia | Los Angeles @ Las Vegas | Pittsburgh @ New York N | Minnesota @ San Francisco | Green Bay @ Washington
New England @ Jacksonville | Houston @ Indianapolis | Los Angeles @ Pittsburgh | Las Vegas @ Green Bay | Denver @ Minnesota | Washington @ New York A | Philadelphia @ Chicago | New York N @ Atlanta | San Francisco @ Seattle
New York A @ New England | Indianapolis @ Los Angeles | Jacksonville @ Pittsburgh | Las Vegas @ Houston | Washington @ New York N | Philadelphia @ Minnesota | Atlanta @ Green Bay | Chicago @ San Francisco | Seattle @ Denver
New England @ Denver | Jacksonville @ Indianapolis | Houston @ Chicago | Los Angeles @ New York A | Pittsburgh @ Las Vegas | Washington @ Atlanta | New York N @ Philadelphia | Minnesota @ Green Bay | Seattle @ San Francisco
Indianapolis @ New York A | Los Angeles @ Houston | Pittsburgh @ New England | Denver @ Jacksonville | Philadelphia @ Washington | New York N @ Las Vegas | Atlanta @ Chicago | San Francisco @ Minnesota | Green Bay @ Seattle
New York A @ Houston | New England @ Indianapolis | Las Vegas @ Los Angeles | Pittsburgh @ Seattle | Washington @ San Francisco | Philadelphia @ New York N | Atlanta @ Denver | Chicago @ Minnesota | Green Bay @ Jacksonville
New York A @ Indianapolis | Jacksonville @ New England | Houston @ Los Angeles | Las Vegas @ Pittsburgh | Denver @ Green Bay | Washington @ Philadelphia | San Francisco @ Chicago | Minnesota @ New York N | Seattle @ Atlanta
New York A @ Las Vegas | Jacksonville @ Los Angeles | Houston @ Pittsburgh | Denver @ Indianapolis | New York N @ New England | Atlanta @ Washington | Chicago @ Green Bay | San Francisco @ Philadelphia | Seattle @ Minnesota
Los Angeles @ New England | Las Vegas @ Jacksonville | Pittsburgh @ Denver | Washington @ Houston | Philadelphia @ Indianapolis | New York N @ Seattle | Chicago @ New York A | San Francisco @ Atlanta | Green Bay @ Minnesota
Indianapolis @ Atlanta | New England @ New York A | Jacksonville @ Philadelphia | Las Vegas @ Minnesota | Pittsburgh @ Houston | Denver @ Los Angeles | New York N @ Washington | Seattle @ Chicago | Green Bay @ San Francisco
New York A @ San Francisco | Indianapolis @ New England | Houston @ Denver | Los Angeles @ Washington | Philadelphia @ Green Bay | Atlanta @ Pittsburgh | Chicago @ New York N | Minnesota @ Jacksonville | Seattle @ Las Vegas
Houston @ Jacksonville | Los Angeles @ San Francisco | Las Vegas @ Indianapolis | Denver @ Pittsburgh | Washington @ New England | New York N @ New York A | Atlanta @ Philadelphia | Minnesota @ Seattle | Green Bay @ Chicago
New York A @ Jacksonville | Indianapolis @ Pittsburgh | New England @ Atlanta | Denver @ Las Vegas | Chicago @ Los Angeles | San Francisco @ Houston | Minnesota @ Washington | Seattle @ Philadelphia | Green Bay @ New York N
New York A @ Philadelphia | Indianapolis @ Washington | New England @ Las Vegas | Jacksonville @ New York N | Pittsburgh @ Los Angeles | Denver @ Houston | Atlanta @ Minnesota | Chicago @ Seattle | San Francisco @ Green Bay
Indianapolis @ Jacksonville | Houston @ Las Vegas | Los Angeles @ Denver | Pittsburgh @ New York A | Philadelphia @ Atlanta | New York N @ San Francisco | Chicago @ Washington | Minnesota @ New England | Seattle @ Green Bay
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
def hi(teams):
    return sorted(teams, key=lambda t: -sos[t])

print("SOS tie groups (opp win-sum):")
for label, teams in [
    ("9-11   7-9", ["New York N", "Los Angeles", "Denver"]),
    ("12-14  6-10", ["New England", "Indianapolis", "Philadelphia"]),
    ("16-18  4-12", ["Jacksonville", "Seattle", "Green Bay"]),
]:
    print(f"  {label:<13}: " + ", ".join(f"{t}({sos[t]})" for t in hi(teams)))

final = [
    "New York A",
    "Minnesota",  # SB W, L
    "Pittsburgh",
    "Washington",  # CC losers (11 > 10)
    "Chicago",
    "Houston",
    "San Francisco",
    "Las Vegas",  # WC losers by record
    *hi(["New York N", "Los Angeles", "Denver"]),  # 7-9
    *hi(["New England", "Indianapolis", "Philadelphia"]),  # 6-10
    "Atlanta",  # 5-11
    *hi(["Jacksonville", "Seattle", "Green Bay"]),  # 4-12
]
assert len(final) == 18 and len(set(final)) == 18
print("\n2045.league.ini [Standings] (2044 final, no rename):")
for i, t in enumerate(final, 1):
    print(f"  {i:>2}  {t}")
