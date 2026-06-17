"""Config dataclass, loader, and change detection for autocontinue.

Settings live in the `[autocontinue]` section of `athc.ini` (found via
`athc.config.config_dir()` / `ATHC_CONFIG_DIR`). Unlike most tools, autocontinue
*requires* its settings -- a clicking watcher must not run on guessed timings.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from athc.config import CONFIG_FILE, config_dir
from athc.config import load_config as load_athc_config

SECTION = "autocontinue"


class ConfigError(Exception):
    """The `[autocontinue]` settings are missing or invalid."""


@dataclass(frozen=True)
class Config:
    mouse_move_duration: float
    delay_before_continue: float


def load_config() -> Config:
    """Read and validate `[autocontinue]` from `config_dir()/athc.ini`.

    Both settings are required; a missing section/key or a non-numeric value raises
    ConfigError. Isolate the lookup in tests by setting `ATHC_CONFIG_DIR`.
    """
    section = load_athc_config().get(SECTION)
    if section is None:
        raise ConfigError(
            f"No [{SECTION}] config found. Set ATHC_CONFIG_DIR or edit:\n"
            f"  {config_dir() / CONFIG_FILE}"
        )
    return Config(
        mouse_move_duration=_required_float(section, "mouse_move_duration"),
        delay_before_continue=_required_float(section, "delay_before_continue"),
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


def _required_float(section: Mapping[str, str], key: str) -> float:
    if key not in section:
        raise ConfigError(f"Missing required setting '{key}' in [{SECTION}].")
    try:
        return float(section[key])
    except ValueError:
        raise ConfigError(
            f"Invalid '{key}' in [{SECTION}]: {section[key]!r} (expected a number)."
        ) from None
