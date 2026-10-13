from __future__ import annotations

from athc.errors import AthcError


class SchedulerError(AthcError):
    """Raised when the scheduler cannot build a league from its files, a valid
    matchup list or a schedule."""
