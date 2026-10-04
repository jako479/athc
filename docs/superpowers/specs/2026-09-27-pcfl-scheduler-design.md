# Scheduler: second league format (PCFL) — design

Date: 2026-09-27. Status: reviewed; approved for planning.

## Goal

One matchup builder and one schedule builder serve two leagues:

| | PNFL | PCFL |
|---|---|---|
| Teams | 18, 9 per conference | 18, 9 per conference |
| Divisions | 4 (4, 5, 4, 5 teams) | none |
| Weeks | 16 | 12 |
| Conference games | division rivals twice, rest of conference once | every conference team once, 4 home / 4 away |
| Non-conference | 4 or 5; two fixed by division place, rest by SOS line | 4; all by SOS line (flat by default), 2 home / 2 away |
| Season shape | NFL-style rules | weeks 1-3 non-conference; weeks 4-12 conference with one cross-conference game each; week 12 is rivalry week |

The team count (18, two conferences of 9) stays fixed. Weeks and divisions become
league facts the code reads instead of constants.

## What the user asked for (PCFL rules)

- All conference teams play each other once, 4 home / 4 away.
- Non-conference matchups chosen by strength of schedule, configurable like the
  PNFL (`spread`), default flat (`0.0`).
- Non-conference hosting balanced 2 / 2 (fixed policy, like the PNFL's).
- Max 3 consecutive home or away games.
- Max 2 consecutive home or away *conference* games (counted along the sequence
  of conference games, ignoring a non-conference game between them).
- Non-conference games open the season. Nine-team conferences leave one team
  idle every all-conference week, so the round robin needs 9 weeks: weeks 1-3 are
  all non-conference and each of weeks 4-12 holds one cross-conference game
  between the two idle teams (each team's fourth non-conference game).
- The final week is rivalry week: nine fixed pairs, eight within a conference and
  one across (the two conference leftovers).
- Rivalry hosting rotates by season parity, with an on/off rule: the first-listed
  team hosts in even seasons, the second in odd seasons; off means the solver
  picks.
- No other PNFL phase-2 rule applies to the PCFL.

Out of scope: CLI and config-dir wiring (league selection; the two PCFL data
files are written at the layout the user specified for later wiring), the
release bundle, the writers' hard-coded "PNFL" titles (the golden report
byte-compares them; the wiring work passes a league name later). Tests build
schedules from constructed leagues and configs.

## Domain: league structure

`domain/league.py` drops the PNFL enums for plain values:

- `Conference(name)` — frozen dataclass.
- `Division(name, conference, expected_size)` — frozen dataclass.
- `Team(metro, conference, division=None)` — `division` is `None` in a league
  without divisions; when set, its conference must match. A league has divisions
  for all teams or for none (`build_teams` validates).
- `Team.same_division(other)` is the one definition of "same division":
  `division is not None and division == other.division`. Every classification
  in the builders, the report and the validation helpers uses it — a bare
  `team.division == other.division` would make every division-less pair
  "divisional".
- PNFL's four divisions stay as module constants (`AFC_EAST`, ...), keyed by the
  `[DivisionStandings]` key names, so the place table and existing tests keep
  working.
- `League` gains `conferences` — the two conferences sorted by name (AFC, NFC
  today; EASTERN, WESTERN for the PCFL; file order is irrelevant) — and a
  `has_divisions` property; `division_standings` is empty without divisions.
- `ConferenceRankings` keys per-conference ranks by `Conference` instead of
  `afc`/`nfc` attributes; `rank_of` and `overall_rank` are unchanged.
- Canonical team order for phase 2 and the writers: conference name, then
  division name, then metro. This reproduces today's PNFL order exactly. Phase 1
  keeps its own order (see below).
- Opponent classes per team come from helpers: divisional opponents (twice
  each), conference opponents (same conference, other division — or the whole
  conference without divisions), and non-conference game count = `weeks` minus
  the structural games. The final week's divisional-game count for a divisional
  league is the sum of `floor(size / 2)` over divisions (8 for the PNFL).

`domain/schedule.py` loses the season constants (`NUM_WEEKS`,
`HOME_GAMES_PER_TEAM`, `WEEK_16_DIVISIONAL_GAMES`, `nonconference_games_for`);
games per week stays 9 (18 teams). Their users move to the config / helpers:
`schedule_builder.py`, `fixed_cpsat_builder.py`, `tests/integration/
schedule_validation.py`, `tests/unit/scheduler/fixed_cpsat/test_schedule_*.py`,
`test_fixed_cpsat_inventory.py`, and the research scripts
`research/scheduler/build_real_reports.py` / `build_real_2048_report.py`
(outside lint scope; update their imports). Tests that build `Team` positionally
(`test_writers.py`, `test_schedule_builder.py`) pass the conference.

## Standings file

`<season>.league.ini` keeps `[OverallStandings]` and takes exactly one of:

- `[DivisionStandings]` — PNFL, unchanged.
- `[ConferenceStandings]` — two keys (the conference names, e.g. `WESTERN`,
  `EASTERN`), nine teams each in finish order. Defines conference membership.

Neither or both sections is a `ConfigError`; the "neither" message names both
sections (existing tests match on `DivisionStandings`). Per-conference 1-9 ranks
derive from the overall order for both formats.

## Scheduler rules file

`scheduler.toml` gains a league section and a rivalries section; missing keys
keep today's PNFL defaults so PNFL behaviour is unchanged.

```toml
[league]
weeks = 12                      # regular-season weeks; even; default 16

[phase2]
max_consecutive_home_or_away = 3              # shared with PNFL
max_consecutive_conference_home_or_away = 2   # new; 0 = off (default)
opening_nonconference_weeks = 3               # new; weeks 1-N all non-conference; 0 = off (default)
# PNFL-only home/away rules, now switchable (default on):
require_home_balance_per_six_weeks = false    # min/max_home_per_six_weeks
require_home_away_streak_caps = false         # max_three_game_home_away_streaks + max_teams_with_home/away_streak
require_mixed_home_away_at_season_ends = false

[rivalries]
rotate_home_by_season = true    # first-listed hosts in even seasons, second in odd
pairs = [["Michigan", "Ohio State"], ...]   # nine pairs, every team once
```

Validation and limits (each tested at the limit and one past it):

- `[league] weeks`: integer, even, > 0 → else `ConfigError` at load. Against
  the league: structural games `S` < `weeks` ≤ `S + 9` (a team cannot play the
  other conference more than 9 times) → else `ConfigError` where the league is
  resolved (PNFL: 12 < weeks ≤ 20 (even); PCFL: 10 ≤ weeks ≤ 16).
- `max_consecutive_conference_home_or_away`, `opening_nonconference_weeks`:
  integers ≥ 0 (0 = off) → else `ConfigError`.
- `opening_nonconference_weeks` against the league: the remaining weeks must
  hold every same-conference game: `(weeks − N) × 8 ≥ same-conference pairings`
  (8 = the most same-conference games one week can hold with two 9-team
  conferences) → else `ConfigError`. PCFL: 3 accepted, 4 rejected.
- `[rivalries]`: when the table exists, `pairs` is required; each entry is
  exactly two different non-blank strings (stripped); every team appears once;
  exactly `teams / 2` pairs; exactly one pair is cross-conference (a 9-team
  conference strands one team); names resolve to league teams. Shape errors are
  `ConfigError` at load; league-resolved errors are `ConfigError` where the
  league is known.
- `[league]` and `[rivalries]` reject unknown keys, like `[phase2]`.
- `require_home_away_streak_caps = false` with divisions is a `ConfigError` at
  builder construction (the soft objective needs the streak flags).

`load_scheduler_config(path=None)` accepts an explicit file so tests can load
the PCFL rules directly. The golden rules file
`tests/integration/data/PNFL.scheduler.toml` sets every new key explicitly
(`weeks = 16`, toggles `true`, amounts `0`) to honour its own contract; no
model change, no re-bless. The dev/release PNFL rules files are left alone
(defaults are identical) because the config layout is being reworked elsewhere.

Rule gating in phase 2:

| Rule group | Applies when |
|---|---|
| One game per week, host half the weeks, phase-1 inventory | always |
| Max consecutive home/away: window = cap + 1, `sum ≤ cap` and `sum ≥ 1` (today's hard-coded 4-week window equals this at cap 3) | always (amount) |
| Balanced hosting per class: each team hosts floor..ceil of half its conference games and half its non-conference games (PNFL: 5-team host 2 of 4, 4-team 2-3 of 5; PCFL: 4 of 8, 2 of 4). One `==` when floor equals ceil, otherwise `>=` then `<=` — today's shapes | always (fixed policy) |
| Divisional home-and-home split, every divisional sequencing/density/front-load/interleave rule, divisional league caps, final-week and last-two-weeks divisional, no back-to-back rematch, soft objective | league has divisions |
| Six-week home window | `require_home_balance_per_six_weeks` |
| ≤1 three-game home/away streak per team, and the league caps on teams with such streaks | `require_home_away_streak_caps` |
| Mixed home/away in the first and last three weeks | `require_mixed_home_away_at_season_ends` |
| Opening non-conference weeks: no same-conference game (divisional or conference) in weeks 1..N | `opening_nonconference_weeks > 0` |
| Conference-sequence streak cap | `max_consecutive_conference_home_or_away > 0` |
| Rivalry final week; rivalry hosting by parity | `[rivalries] pairs` present; `rotate_home_by_season` |

## Phase 1 (matchups)

One builder, structure-driven:

1. Divisional pairs twice (only with divisions).
2. Conference pairs once.
3. Fixed non-conference pairs: the PNFL place-table pairs (only with divisions;
   the table is keyed by division name and must cover the league's divisions)
   plus the cross-conference rivalry pairs. Fixed pairs are added to the model
   in sorted order (today iterates a `frozenset`, which is hash-randomized per
   process; sorting is safe because the golden already passes under any order).
4. One CP-SAT solve picks the remaining non-conference games: each team's
   degree is its non-conference count; fixed pairs forced; each team draws at
   least one top-half and one bottom-half opponent; the `spread` line objective
   is unchanged. The scoring scale is `lcm(20, non-conference counts)` — 20 for
   both leagues, so the PNFL model is byte-identical.
5. Validate: `weeks × 9` pairings, the expected non-conference total, no
   unresolved slots, all fixed pairs kept.

Variable grid order is preserved: rows are the first conference's teams in
conference-rank order, columns the second conference's teams in rank order
(`league.conferences[0]` is the row conference — AFC today).

## Phase 2 (placement)

The builder takes the league, `weeks`, the phase-2 amounts, the resolved rivalry
pairs and the season. New constraints:

- Opening non-conference weeks: no same-conference game in weeks 1..N.
- Conference-sequence streak cap, without reification: for every window of
  weeks `W` of length ≥ cap + 1, `conf_home(W) ≤ cap + |W| × conf_away(W)` and
  the mirror. A window with no away conference game may hold at most `cap`
  home conference games, which is exactly "no cap + 1 consecutive-in-sequence
  home conference games"; any away conference game in the window relaxes it.
- Rivalry final week: each rivalry pair meets in the last week; with rotation on,
  the parity of `season` fixes the host.

### PNFL preservation checklist

For a PNFL league the built CP-SAT model must be byte-identical to today's:

- `__init__` creates `x_`, `h_`, `d_` variables in the same order with the same
  names; no new helper variables (conference indicators, rivalry literals,
  window sums) are created unless their rule is on; the four/five-team sets are
  built only with divisions.
- `_populate_model` keeps its constraint order; a gated rule adds nothing when
  off; `_constraint_max_teams_with_streaks` still creates `has3h`, `has3a`,
  `has3d` in that order when both gates are on.
- Hosting constraints keep today's shapes (see the gating table); opponent
  lists iterate canonical team order.
- Phase 1 keeps rank-order grids and sorted fixed pairs.
- A fast regression test builds both PNFL models for the golden league (no
  solve) and compares a SHA-256 of `model.proto.SerializeToString()` against a
  value frozen before the refactor (after the fixed-pair sort). The slow golden
  test remains the end-to-end proof.

## Orchestration

`generate_schedule` (scheduler entry and `main.py`) takes a required
keyword-only `season`, reads `weeks` from the config, resolves rivalries against
the league, and passes both builders what they need. `main.py` already has the
season; the CLI is not changed. The test conftest passes a season.

## Data files

- `dev/leagues/PCFL/standings/2029.league.ini` — 2028 final standings
  (playoff tiers first, then record, then point differential):
  Texas, Tennessee, Notre Dame, Arkansas, Ohio State, Boston College, LSU,
  UCLA, Washington, Clemson, Oklahoma, Georgia, Penn State, USC, Colorado,
  Miami, Oregon, Michigan. `[ConferenceStandings]` lists WESTERN and EASTERN.
- `dev/leagues/PCFL/rules/scheduler.toml` — the rules above, commented like
  the PNFL file, `spread = 0.0`, rivalries: Michigan–Ohio State, USC–UCLA,
  Washington–Oregon, Notre Dame–Colorado, Oklahoma–Texas, LSU–Arkansas,
  Georgia–Tennessee, Clemson–Miami, Penn State–Boston College.

## Testing

- Domain: both league formats build; conference format rejects a missing or
  extra conference, a wrong conference size, duplicate and unknown teams, mixed
  with/without divisions; two division-less teams are not same-division;
  canonical order and conference order; opponent-class helpers; `weeks` at and
  one past both limits for each format.
- Config: `[league] weeks` (parsed, default, odd, zero, non-integer, unknown
  key), `[rivalries]` (missing `pairs`, empty, wrong arity, same team twice,
  non-string, whitespace stripped, unknown key, toggle), new `[phase2]` keys at
  0 and -1, `load_league` with each section and with neither/both,
  explicit-path loading, the two PCFL dev files load.
- League-resolved config: opening weeks 3 accepted / 4 rejected; rivalry pairs
  8 / 9 / 10, one vs three cross-conference, unknown name; streak caps off with
  divisions.
- Phase 1 (fast): conference-format inventory — totals, degree 4, cross-conference
  rivalry forced, top/bottom guard, flat line near 5, deterministic; PNFL tests
  unchanged in substance.
- Phase 2: model-build tests (no solve) that each new rule adds its constraints
  when on and nothing when off, and the PNFL fingerprint test; solved-schedule
  tests validating every PCFL rule (games, hosting, opening weeks, one
  cross-conference game per later week, both streak caps, rivalry week, hosting
  for an even and an odd season, rotation off). PCFL solves have no objective
  and are expected to be fast; they run in the fast suite if they stay under
  ~15 s, else they are marked `slow`.
- PNFL: existing unit tests pass with the domain rename; the golden integration
  test passes unchanged.

## Documentation

`docs/scheduler/README.md`, `ARCHITECTURE.md`, `phase-1-*.md`,
`phase-2-schedule.md`, the test matrices, CHANGELOG, STATUS and WORKLOG — short
and high-level: two league formats, the new keys, the gating table.
