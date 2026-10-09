"""Shared helpers for `athc profile`: file collection, rules loading."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from athc.cli._files import Collected, collect_files, is_glob, named_file
from athc.errors import ConfigFileError
from athc.profile import ProfileRules, load_rules

__all__ = ["Collected", "collect_files", "is_glob", "load_rules_or_raise", "named_file"]


def load_rules_or_raise(rule_files: Iterable[Path]) -> ProfileRules:
    """The league's profile rules. ConfigFileError when none are configured; a
    rules file that cannot be read or parsed raises its own error."""
    files = list(rule_files)
    if not files:
        raise ConfigFileError(
            "no rules configured - nothing to check. "
            "Add profile.toml to the league folder."
        )
    return load_rules(files)
