from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FactoryMission:
    factory_prefix: str
    mission_number: int

    @property
    def canonical_id(self) -> str:
        return f"{self.factory_prefix}-{self.mission_number}"


def parse_factory_id(value: str) -> FactoryMission:
    if not isinstance(value, str):
        raise TypeError("factory id must be a string")

    parts = value.split("-")
    if len(parts) != 2:
        raise ValueError("factory id must have the form '<prefix>-<number>'")

    prefix, raw_number = parts
    if prefix != "df":
        raise ValueError("factory prefix must be 'df'")
    if not raw_number.isdigit():
        raise ValueError("mission number must contain only digits")

    mission_number = int(raw_number)
    if mission_number <= 0:
        raise ValueError("mission number must be positive")

    return FactoryMission(factory_prefix=prefix, mission_number=mission_number)


def is_target_mission(value: str, target: int = 170) -> bool:
    mission = parse_factory_id(value)
    return mission.mission_number == target


def mission_signature(value: str) -> str:
    mission = parse_factory_id(value)
    return f"{mission.canonical_id}|core-online"
# [CRUX-MK]
