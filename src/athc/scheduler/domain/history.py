"""Non-conference matchup history for rotation-fair scheduling."""

from __future__ import annotations

import json
from os import PathLike
from pathlib import Path

from athc.scheduler.domain.league import Conference, League, Team

StrPath = str | PathLike[str]


def _make_matchup_key(team_a: Team, team_b: Team) -> str:
    """Return 'AFC metro|NFC metro' key for a non-conference pair."""
    afc = team_a if team_a.conference == Conference.AFC else team_b
    nfc = team_b if team_a.conference == Conference.AFC else team_a
    return f"{afc.metro}|{nfc.metro}"


class NonConfHistory:
    """Tracks the last season each non-conference pair played."""

    def __init__(self, matchups: dict[str, int] | None = None) -> None:
        self._matchups: dict[str, int] = {} if matchups is None else dict(matchups)
        # Recency is measured against the most recent season in the data itself.
        self._most_recent: int = max(self._matchups.values(), default=0)

    @classmethod
    def load(cls, path: StrPath) -> NonConfHistory:
        """Load from JSON file. Empty history if the file doesn't exist.

        Raises ValueError if the file is not valid history JSON (bad JSON, a
        missing `matchups` object, or a non-integer season).
        """
        path = Path(path)
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"not valid JSON: {error}") from error
        if not isinstance(data, dict) or not isinstance(data.get("matchups"), dict):
            raise ValueError("missing a 'matchups' object")
        matchups: dict[str, int] = data["matchups"]
        for key, season in matchups.items():
            if isinstance(season, bool) or not isinstance(season, int):
                raise ValueError(f"season for '{key}' must be an integer")
        return cls(matchups=matchups)

    def validate_teams(self, league: League) -> None:
        """Raise ValueError unless the matchups cover every AFC x NFC pair (keys
        `AFC metro|NFC metro`). Completeness is required because Scheduler A
        looks up arbitrary pairs, so a missing one would KeyError mid-solve.
        """
        afc = {t.metro for t in league.teams if t.conference == Conference.AFC}
        nfc = {t.metro for t in league.teams if t.conference == Conference.NFC}
        bad: list[str] = []
        for key in self._matchups:
            parts = key.split("|")
            if len(parts) != 2 or parts[0] not in afc or parts[1] not in nfc:
                bad.append(key)
        if bad:
            raise ValueError(f"matchups name unknown or misplaced teams: {sorted(bad)}")
        expected = {f"{a}|{n}" for a in afc for n in nfc}
        missing = sorted(expected - set(self._matchups))
        if missing:
            raise ValueError(
                f"missing {len(missing)} of {len(expected)} non-conference "
                f"pairs (e.g. {missing[0]})"
            )

    def last_played(self, team_a: Team, team_b: Team) -> int:
        """Return the last season these two teams played."""
        return self._matchups[_make_matchup_key(team_a, team_b)]

    def opponent_cost(self, team: Team, opp: Team) -> int:
        """Return recency cost for this matchup. Lower = more overdue.

        Measured against the most recent season in the history:
        - most recent season -> 0
        - one season older -> -1
        - two seasons older -> -2
        """
        return self.last_played(team, opp) - self._most_recent
