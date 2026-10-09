from __future__ import annotations

from athc.errors import AthcError


class SchedulerError(AthcError):
    """Raised when a scheduler cannot build a valid matchup list or schedule."""
