"""Component serial number record."""

from __future__ import annotations

import enum
from dataclasses import dataclass

from .._binary import BinaryReader


class ComponentType(enum.IntEnum):
    CAMERA = 1
    AIRCRAFT = 2
    RC = 3
    BATTERY = 4

    @classmethod
    def _missing_(cls, value: object) -> ComponentType | None:
        if not isinstance(value, int):
            return None
        obj = int.__new__(cls, value)
        obj._name_ = f"UNKNOWN_{value}"
        obj._value_ = value
        return obj


@dataclass
class ComponentSerial:
    """Component serial number record."""

    component_type: ComponentType
    serial: str

    @classmethod
    def from_bytes(cls, data: bytes, version: int = 0) -> ComponentSerial:
        r = BinaryReader(data)
        component_type = ComponentType(r.read_u16())
        length = r.read_u8()
        raw = r.read_bytes(length)
        serial = raw.split(b"\x00", 1)[0].decode("utf-8", errors="replace")
        return cls(component_type=component_type, serial=serial)
