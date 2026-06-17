"""Profile config: reads `[profile] rule_files` from `athc.ini`."""

from __future__ import annotations

import configparser
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from athc.config import CONFIG_FILE, config_dir

SECTION = "profile"


class ConfigFileError(ValueError):
    """Raised when the profile config INI cannot be read or parsed."""


@dataclass(frozen=True)
class Config:
    rule_files: tuple[Path, ...] = ()


def load_config(*, rule_files: Sequence[Path] | None = None) -> Config:
    """Load profile config from `config_dir()/athc.ini` (set `ATHC_CONFIG_DIR` to
    override). Missing file/section → no rules. `rule_files` (CLI `--rules`) wins."""
    if rule_files is not None:
        return Config(rule_files=tuple(rule_files))
    cp = _read(config_dir() / CONFIG_FILE)
    raw = cp.get(SECTION, "rule_files", fallback="")
    return Config(
        rule_files=tuple(
            Path(line.strip()) for line in raw.splitlines() if line.strip()
        )
    )


def _read(path: Path) -> configparser.ConfigParser:
    cp = configparser.ConfigParser()
    try:
        cp.read(path, encoding="utf-8")
    except configparser.Error as e:
        raise ConfigFileError(f"{path}: {e}") from e
    return cp
