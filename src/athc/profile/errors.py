"""Errors the profile tool raises."""

from __future__ import annotations

from athc.errors import AthcError, StrPath
from athc.fbpro98_profile import ProfileType


class ProfileTypeMismatchError(AthcError):
    """The two profiles are not the same side (offense vs defense)."""

    def __init__(
        self,
        source_type: ProfileType,
        target_type: ProfileType,
        message: str | None = None,
        path: StrPath | None = None,
    ) -> None:
        self.source_type = source_type
        self.target_type = target_type
        super().__init__(
            message
            or (
                f"Profile type mismatch: {source_type.name.lower()} vs "
                f"{target_type.name.lower()}."
            ),
            path,
        )
