"""Config dataclass, loader, and change detection for autocontinue.

Settings live in the `[autocontinue]` table of `athc.toml` (found via
`athc.config.config_dir()` / `ATHC_CONFIG_DIR`). Every key is optional: a
missing file, table or key means the defaults on `Config`. The shipped
athc.toml turns drive_league_pregame on; missing, it is off.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

from athc.config import CONFIG_FILE, config_dir, config_file, config_table
from athc.errors import ConfigFileError

SECTION = "autocontinue"


@dataclass(frozen=True, slots=True)
class Config:
    mouse_move_duration: float = 0.0
    continue_pause: float = 1.0
    halftime_pause: float = 8.0
    hot_corner: bool = True
    drive_league_pregame: bool = False
    # Seconds after each pre-game click; 0 skips the click.
    plans_profiles_pause: float = 1.5  # after Plans/Profiles, and after Visitor
    conditions_pause: float = 2.5
    venues_pause: float = 1.5


# What a missing key means; slots leave no class attributes to read them from.
_DEFAULTS = Config()


def load_config() -> Config:
    """Read and validate `[autocontinue]` from `config_dir()/athc.toml`.

    Every key is optional: a missing file, section or key takes its default on
    `Config`. A value that is present but wrong raises ConfigFileError. Isolate
    the lookup in tests by setting `ATHC_CONFIG_DIR`.
    """
    section = config_table(SECTION)
    return Config(
        mouse_move_duration=_timing(
            section, "mouse_move_duration", default=_DEFAULTS.mouse_move_duration
        ),
        continue_pause=_timing(
            section, "continue_pause", default=_DEFAULTS.continue_pause
        ),
        halftime_pause=_timing(
            section, "halftime_pause", default=_DEFAULTS.halftime_pause
        ),
        hot_corner=_optional_bool(section, "hot_corner", default=_DEFAULTS.hot_corner),
        drive_league_pregame=_optional_bool(
            section, "drive_league_pregame", default=_DEFAULTS.drive_league_pregame
        ),
        plans_profiles_pause=_timing(
            section, "plans_profiles_pause", default=_DEFAULTS.plans_profiles_pause
        ),
        conditions_pause=_timing(
            section, "conditions_pause", default=_DEFAULTS.conditions_pause
        ),
        venues_pause=_timing(section, "venues_pause", default=_DEFAULTS.venues_pause),
    )


def config_signature() -> tuple[str, int, int] | None:
    """Cheap `(path, mtime_ns, size)` fingerprint of `config_dir()/athc.toml`, or
    None if absent. Changes iff the file changes, gating watch-loop re-reads."""
    path = config_dir() / CONFIG_FILE
    if not path.is_file():
        return None
    try:
        stat = path.stat()
    except OSError:
        return None
    return (str(path), stat.st_mtime_ns, stat.st_size)


def get_runtime_path(filename: str) -> Path:
    """On-disk path to a packaged image (e.g. continue_button.png)."""
    resource = resources.files("athc.autocontinue") / "images" / filename
    return Path(str(resource))


def _optional_bool(section: Mapping[str, Any], key: str, *, default: bool) -> bool:
    if key not in section:
        return default
    value = section[key]
    if not isinstance(value, bool):
        raise ConfigFileError(
            f"[{SECTION}] {key}: Must be true or false, got {_shown(value)}.",
            config_file(),
        )
    return value


def _shown(value: Any) -> str:
    """`value` as TOML spells it (`true`, `1979-05-27`); a string quoted."""
    if isinstance(value, bool):
        return str(value).lower()
    return repr(value) if isinstance(value, str) else str(value)


def _timing(section: Mapping[str, Any], key: str, *, default: float) -> float:
    """Seconds, 0 or more. NaN and infinity are not, since time.sleep refuses
    them. A TOML integer counts; a boolean, though an int to Python, does
    not."""
    if key not in section:
        return default
    value = section[key]
    if (
        isinstance(value, bool)
        or not isinstance(value, int | float)
        or not 0 <= value < math.inf
    ):
        raise ConfigFileError(
            f"[{SECTION}] {key}: Must be a number, 0 or more, got {_shown(value)}.",
            config_file(),
        )
    return float(value)
