"""RC Display Field record."""

from __future__ import annotations

from dataclasses import dataclass

from .._binary import BinaryReader


@dataclass
class RCDisplayField:
    """RC Display Field record — stick values from display."""

    aileron: int
    elevator: int
    throttle: int
    rudder: int

    @classmethod
    def from_bytes(cls, data: bytes, version: int = 0) -> RCDisplayField:
        r = BinaryReader(data)
        r.skip(7)  # unknown bytes
        aileron = r.read_u16()
        elevator = r.read_u16()
        throttle = r.read_u16()
        rudder = r.read_u16()
        return cls(aileron=aileron, elevator=elevator, throttle=throttle, rudder=rudder)
