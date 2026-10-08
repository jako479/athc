"""A league's labels for the offense and defense play categories.

Leagues abbreviate the game's category names (PNFL: `PSR` for Pass Short Right,
`RunLeft` for defense Run Left). The labels come from the league's settings
file; this module only holds and validates them. Special-teams categories have
no labels and always go by their game name.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from athc.fbpro98_play.model import DefensiveCategory, OffensiveCategory, PlayCategory


@dataclass(frozen=True, slots=True)
class CategoryLabels:
    """League label per offense / defense category. A category absent from its
    mapping has no label and goes by its game name. `CategoryLabels()` is a league
    with no labels."""

    offense: Mapping[OffensiveCategory, str] = field(default_factory=dict)
    defense: Mapping[DefensiveCategory, str] = field(default_factory=dict)

    @classmethod
    def from_tables(
        cls, offense: Mapping[str, object], defense: Mapping[str, object]
    ) -> CategoryLabels:
        """Build from two game-name -> label tables (the `[categories.offense]`
        and `[categories.defense]` tables of league.toml). ValueError names the
        first bad entry: a key that is not a category of that side, a label that
        is not a non-empty string, repeats within the side, or equals one of the
        side's category names."""
        return cls(
            _validate("offense", offense, list(OffensiveCategory)),
            _validate("defense", defense, list(DefensiveCategory)),
        )

    def label(self, category: PlayCategory) -> str:
        """The league label for `category`, else its game name."""
        if isinstance(category, OffensiveCategory):
            return self.offense.get(category, category.long)
        if isinstance(category, DefensiveCategory):
            return self.defense.get(category, category.long)
        return category.long

    def offense_by_label(self, label: str) -> OffensiveCategory | None:
        """The offense category the league calls `label`; None when none does."""
        return _by_label(self.offense, label)

    def defense_by_label(self, label: str) -> DefensiveCategory | None:
        """The defense category the league calls `label`; None when none does."""
        return _by_label(self.defense, label)


def _validate[C: PlayCategory](
    side: str, table: Mapping[str, object], members: Iterable[C]
) -> dict[C, str]:
    by_name = {m.long: m for m in members}
    result: dict[C, str] = {}
    used: dict[str, str] = {}  # label -> game name that claimed it
    for name, value in table.items():
        where = f"[categories.{side}] {name!r}"
        member = by_name.get(name)
        if member is None:
            raise ValueError(f"{where}: not a game category name for {side}")
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{where}: label must be a non-empty string")
        if value in by_name:
            raise ValueError(
                f"{where}: label {value!r} is a game category name for {side}"
            )
        if value in used:
            raise ValueError(
                f"{where}: label {value!r} already used by {used[value]!r}"
            )
        used[value] = name
        result[member] = value
    return result


def _by_label[C: PlayCategory](labels: Mapping[C, str], label: str) -> C | None:
    for member, value in labels.items():
        if value == label:
            return member
    return None
