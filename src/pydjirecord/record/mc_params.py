"""MC parameters record."""

from __future__ import annotations

import enum
from dataclasses import dataclass

from .._binary import BinaryReader


class FailSafeProtectionType(enum.IntEnum):
    HOVER = 0
    LANDING = 1
    GO_HOME = 2

    @classmethod
    def _missing_(cls, value: object) -> FailSafeProtectionType | None:
        if not isinstance(value, int):
            return None
        obj = int.__new__(cls, value)
        obj._name_ = f"UNKNOWN_{value}"
        obj._value_ = value
        return obj


@dataclass
class MCParams:
    """MC parameters record."""

    fail_safe_protection: FailSafeProtectionType
    mvo_func_enabled: bool
    avoid_obstacle_enabled: bool
    user_avoid_enabled: bool

    @classmethod
    def from_bytes(cls, data: bytes, version: int = 0) -> MCParams:
        r = BinaryReader(data)
        fail_safe_protection = FailSafeProtectionType(r.read_u8())
        bp1 = r.read_u8()
        mvo_func_enabled = bool(bp1 & 0x01)
        avoid_obstacle_enabled = bool(bp1 & 0x02)
        user_avoid_enabled = bool(bp1 & 0x04)
        return cls(
            fail_safe_protection=fail_safe_protection,
            mvo_func_enabled=mvo_func_enabled,
            avoid_obstacle_enabled=avoid_obstacle_enabled,
            user_avoid_enabled=user_avoid_enabled,
        )
