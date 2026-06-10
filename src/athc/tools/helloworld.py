from __future__ import annotations

from athc.config import load_config


def main() -> int:
    cfg = load_config().get("helloworld", {})
    print(cfg.get("greeting", "hi from helloworld (no config set)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
