"""Gimbal record."""

from __future__ import annotations

import enum
from dataclasses import dataclass

from .._binary import BinaryReader
from ..utils import sub_byte_field


class GimbalMode(enum.IntEnum):
    FREE = 0
    FPV = 1
    YAW_FOLLOW = 2

    @classmethod
    def _missing_(cls, value: object) -> GimbalMode | None:
        if not isinstance(value, int):
            return None
        obj = int.__new__(cls, value)
        obj._name_ = f"UNKNOWN_{value}"
        obj._value_ = value
        return obj


@dataclass
class Gimbal:
    """Gimbal record."""

    pitch: float
    roll: float
    yaw: float
    mode: GimbalMode
    is_pitch_at_limit: bool
    is_roll_at_limit: bool
    is_yaw_at_limit: bool
    is_stuck: bool

    @classmethod
    def from_bytes(cls, data: bytes, version: int) -> Gimbal:
        """Parse gimbal record from binary data."""
        r = BinaryReader(data)
        pitch = r.read_i16() / 10.0
        roll = r.read_i16() / 10.0
        yaw = r.read_i16() / 10.0

        bp1 = r.read_u8()
        mode = GimbalMode(sub_byte_field(bp1, 0xC0))

        _roll_adjust = r.read_u8()  # i8
        _yaw_angle = r.read_i16()

        bp2 = r.read_u8()
        is_pitch_at_limit = bool(sub_byte_field(bp2, 0x01))
        is_roll_at_limit = bool(sub_byte_field(bp2, 0x02))
        is_yaw_at_limit = bool(sub_byte_field(bp2, 0x04))
        is_stuck = bool(sub_byte_field(bp2, 0x40))

        return cls(
            pitch=pitch,
            roll=roll,
            yaw=yaw,
            mode=mode,
            is_pitch_at_limit=is_pitch_at_limit,
            is_roll_at_limit=is_roll_at_limit,
            is_yaw_at_limit=is_yaw_at_limit,
            is_stuck=is_stuck,
        )
