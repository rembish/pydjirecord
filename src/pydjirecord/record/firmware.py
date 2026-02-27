"""Firmware version record."""

from __future__ import annotations

import enum
from dataclasses import dataclass

from .._binary import BinaryReader


class SenderType(enum.IntEnum):
    NONE = 0
    CAMERA = 1
    MC = 3
    GIMBAL = 4
    RC = 6
    BATTERY = 11

    @classmethod
    def _missing_(cls, value: object) -> SenderType | None:
        if not isinstance(value, int):
            return None
        obj = int.__new__(cls, value)
        obj._name_ = f"UNKNOWN_{value}"
        obj._value_ = value
        return obj


@dataclass
class Firmware:
    """Firmware version record."""

    sender_type: SenderType
    sub_sender_type: int
    version: str

    @classmethod
    def from_bytes(cls, data: bytes, version: int = 0) -> Firmware:
        """Parse firmware version record from binary data."""
        r = BinaryReader(data)
        sender_type = SenderType(r.read_u8())
        sub_sender_type = r.read_u8()
        ver_bytes = r.read_bytes(4)
        ver_str = f"{ver_bytes[0]}.{ver_bytes[1]}.{ver_bytes[2]}"
        return cls(
            sender_type=sender_type,
            sub_sender_type=sub_sender_type,
            version=ver_str,
        )
