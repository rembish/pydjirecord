"""Remote Controller record."""

from __future__ import annotations

import enum
from dataclasses import dataclass

from .._binary import BinaryReader
from ..layout.details import ProductType


class FlightModeSwitch(enum.IntEnum):
    ONE = 0
    TWO = 1
    THREE = 2

    @classmethod
    def _missing_(cls, value: object) -> FlightModeSwitch | None:
        if not isinstance(value, int):
            return None
        obj = int.__new__(cls, value)
        obj._name_ = f"UNKNOWN_{value}"
        obj._value_ = value
        return obj


_MAVIC_PRO_REMAP: dict[int, int] = {0: 2, 1: 3, 2: 1}


@dataclass
class RC:
    """Remote Controller record."""

    aileron: int
    elevator: int
    throttle: int
    rudder: int

    @classmethod
    def from_bytes(cls, data: bytes, version: int, product_type: ProductType = ProductType.NONE) -> RC:
        """Parse RC record from binary data."""
        r = BinaryReader(data)
        aileron = r.read_u16()
        elevator = r.read_u16()
        throttle = r.read_u16()
        rudder = r.read_u16()
        return cls(aileron=aileron, elevator=elevator, throttle=throttle, rudder=rudder)
