"""Every frozen dataclass in athc is slotted, and so is every file model."""

import dataclasses
import importlib
import inspect
import pkgutil

import athc

FILE_LIBRARIES = (
    "athc.fbpro98_gameplan.model",
    "athc.fbpro98_lg2.model",
    "athc.fbpro98_lge.model",
    "athc.fbpro98_play.model",
    "athc.fbpro98_profile.model",
    "athc.fbpro98_pyr.model",
    "athc.fbpro98_stats.model",
)


def _dataclasses_of(module_name: str) -> list[type]:
    module = importlib.import_module(module_name)
    return [
        cls
        for _, cls in inspect.getmembers(module, inspect.isclass)
        if cls.__module__ == module.__name__
        # Only the decorator's own params say how the class was declared.
        and dataclasses.is_dataclass(cls)
        and vars(cls).get("__dataclass_params__") is not None
    ]


def _frozen_dataclasses() -> list[type]:
    found: list[type] = []
    for info in pkgutil.walk_packages(athc.__path__, prefix="athc."):
        if info.name.endswith(".__main__"):
            continue  # runs the CLI on import
        found += [
            cls
            for cls in _dataclasses_of(info.name)
            if vars(cls)["__dataclass_params__"].frozen
        ]
    return found


def _file_models() -> list[type]:
    return [cls for name in FILE_LIBRARIES for cls in _dataclasses_of(name)]


def _name(cls: type) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


def test_walk_finds_the_frozen_dataclasses() -> None:
    assert "athc.config.LeagueConfig" in {_name(c) for c in _frozen_dataclasses()}


def test_every_frozen_dataclass_is_slotted() -> None:
    unslotted = sorted(
        _name(cls) for cls in _frozen_dataclasses() if "__slots__" not in vars(cls)
    )
    assert unslotted == []


def test_walk_finds_the_file_models() -> None:
    assert "athc.fbpro98_gameplan.model.GamePlan" in {_name(c) for c in _file_models()}


def test_every_file_model_is_mutable_and_slotted() -> None:
    frozen = sorted(
        _name(cls) for cls in _file_models() if vars(cls)["__dataclass_params__"].frozen
    )
    unslotted = sorted(
        _name(cls) for cls in _file_models() if "__slots__" not in vars(cls)
    )
    assert (frozen, unslotted) == ([], [])
