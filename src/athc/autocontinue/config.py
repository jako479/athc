"""Config dataclass, loader, and change detection for autocontinue.

Settings live in the `[autocontinue]` section of `athc.ini` (found via
`athc.config.config_dir()` / `ATHC_CONFIG_DIR`). Every key is optional: a
missing file, section or key means the defaults on `Config`.
"""

from __future__ import annotations

import configparser
import math
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from athc.config import CONFIG_FILE, config_dir
from athc.config import load_config as load_athc_config
from athc.errors import ConfigFileError

SECTION = "autocontinue"

# Accept the usual INI truthy/falsy spellings (true/false, yes/no, on/off, 1/0).
_BOOLEAN_STATES = configparser.RawConfigParser.BOOLEAN_STATES


@dataclass(frozen=True, slots=True)
class Config:
    mouse_move_duration: float = 0.0
    delay_before_continue: float = 1.0
    hot_corner: bool = True


# What a missing key means; slots leave no class attributes to read them from.
_DEFAULTS = Config()


def load_config() -> Config:
    """Read and validate `[autocontinue]` from `config_dir()/athc.ini`.

    Every key is optional: a missing file, section or key takes its default on
    `Config`. A value that is present but wrong raises ConfigFileError. Isolate
    the lookup in tests by setting `ATHC_CONFIG_DIR`.
    """
    section = load_athc_config().get(SECTION, {})
    return Config(
        mouse_move_duration=_timing(
            section, "mouse_move_duration", default=_DEFAULTS.mouse_move_duration
        ),
        delay_before_continue=_timing(
            section, "delay_before_continue", default=_DEFAULTS.delay_before_continue
        ),
        hot_corner=_optional_bool(section, "hot_corner", default=_DEFAULTS.hot_corner),
    )


def config_signature() -> tuple[str, int, int] | None:
    """Cheap `(path, mtime_ns, size)` fingerprint of `config_dir()/athc.ini`, or None if
    absent. Changes iff the file changes, gating watch-loop re-reads."""
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


def _optional_bool(section: Mapping[str, str], key: str, *, default: bool) -> bool:
    if key not in section:
        return default
    value = section[key].strip().lower()
    if value not in _BOOLEAN_STATES:
        raise ConfigFileError(
            f"[{SECTION}] {key}: Must be true or false, got {section[key]!r}.",
            config_dir() / CONFIG_FILE,
        )
    return _BOOLEAN_STATES[value]


def _timing(section: Mapping[str, str], key: str, *, default: float) -> float:
    """Seconds, 0 or more. NaN and infinity are not, since time.sleep refuses
    them."""
    if key not in section:
        return default
    try:
        value = float(section[key])
    except ValueError:
        value = None
    if value is None or not 0 <= value < math.inf:
        raise ConfigFileError(
            f"[{SECTION}] {key}: Must be a number, 0 or more, got {section[key]!r}.",
            config_dir() / CONFIG_FILE,
        )
    return value
