"""Errors the profile tool raises."""

from __future__ import annotations

from athc.errors import AthcError
from athc.fbpro98_profile import ProfileType


class ProfileTypeMismatchError(AthcError):
    """The two profiles are not the same side (offense vs defense)."""

    def __init__(
        self,
        source_type: ProfileType,
        target_type: ProfileType,
        message: str | None = None,
    ) -> None:
        self.source_type = source_type
        self.target_type = target_type
        super().__init__(
            message
            or f"profile type mismatch: {source_type.name} vs {target_type.name}"
        )
