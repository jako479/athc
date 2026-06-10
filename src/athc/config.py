from __future__ import annotations

import configparser
import os
from pathlib import Path

from platformdirs import user_config_path

CONFIG_FILE = "athc.ini"


def config_dir() -> Path:
    if override := os.environ.get("ATHC_CONFIG_DIR"):
        return Path(override)
    return user_config_path("athc", appauthor=False, ensure_exists=False)


def load_config() -> dict[str, dict[str, str]]:
    path = config_dir() / CONFIG_FILE
    cp = configparser.ConfigParser(interpolation=None)
    if path.is_file():
        cp.read(path, encoding="utf-8")
    return {section: dict(cp[section]) for section in cp.sections()}
