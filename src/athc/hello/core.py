from __future__ import annotations

from athc.config import load_config


def greet() -> str:
    cfg = load_config().get("hello", {})
    return cfg.get("greeting", "hello from athc (no config set)")
