"""Every frozen dataclass in athc is slotted."""

import dataclasses
import importlib
import inspect
import pkgutil

import athc


def _frozen_dataclasses() -> list[type]:
    found: list[type] = []
    for info in pkgutil.walk_packages(athc.__path__, prefix="athc."):
        if info.name.endswith(".__main__"):
            continue  # runs the CLI on import
        module = importlib.import_module(info.name)
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ != module.__name__:
                continue
            # Only the decorator's own params say whether the class is frozen.
            params = vars(cls).get("__dataclass_params__")
            if dataclasses.is_dataclass(cls) and params is not None and params.frozen:
                found.append(cls)
    return found


def _name(cls: type) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


def test_walk_finds_the_frozen_dataclasses() -> None:
    assert "athc.config.LeagueConfig" in {_name(c) for c in _frozen_dataclasses()}


def test_every_frozen_dataclass_is_slotted() -> None:
    unslotted = sorted(
        _name(cls) for cls in _frozen_dataclasses() if "__slots__" not in vars(cls)
    )
    assert unslotted == []
