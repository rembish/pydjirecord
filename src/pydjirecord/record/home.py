"""Home point record."""

from __future__ import annotations

import enum
import math
from dataclasses import dataclass

from .._binary import BinaryReader
from ..utils import sub_byte_field


class GoHomeMode(enum.IntEnum):
    NORMAL = 0
    FIXED_HEIGHT = 1

    @classmethod
    def _missing_(cls, value: object) -> GoHomeMode | None:
        if not isinstance(value, int):
            return None
        obj = int.__new__(cls, value)
        obj._name_ = f"UNKNOWN_{value}"
        obj._value_ = value
        return obj


class CompassCalibrationState(enum.IntEnum):
    NOT_CALIBRATING = 0
    HORIZONTAL = 1
    VERTICAL = 2
    SUCCESSFUL = 3
    FAILED = 4

    @classmethod
    def _missing_(cls, value: object) -> CompassCalibrationState | None:
        if not isinstance(value, int):
            return None
        obj = int.__new__(cls, value)
        obj._name_ = f"UNKNOWN_{value}"
        obj._value_ = value
        return obj


class IOCMode(enum.IntEnum):
    COURSE_LOCK = 1
    HOME_LOCK = 2
    HOTSPOT_SURROUND = 3

    @classmethod
    def _missing_(cls, value: object) -> IOCMode | None:
        if not isinstance(value, int):
            return None
        obj = int.__new__(cls, value)
        obj._name_ = f"UNKNOWN_{value}"
        obj._value_ = value
        return obj


@dataclass
class Home:
    """Home point record."""

    longitude: float
    latitude: float
    altitude: float
    is_home_record: bool
    go_home_mode: GoHomeMode
    is_dynamic_home_point_enabled: bool
    is_near_distance_limit: bool
    is_near_height_limit: bool
    is_multiple_mode_open: bool
    has_go_home: bool
    compass_state: CompassCalibrationState
    is_compass_adjust: bool
    is_beginner_mode: bool
    is_ioc_open: bool
    ioc_mode: IOCMode
    aircraft_head_direction: int
    go_home_height: int
    ioc_course_lock_angle: int
    current_flight_record_index: int
    max_allowed_height: float

    @classmethod
    def from_bytes(cls, data: bytes, version: int) -> Home:
        r = BinaryReader(data)
        longitude = math.degrees(r.read_f64())
        latitude = math.degrees(r.read_f64())
        altitude = r.read_f32() / 10.0

        bp1 = r.read_u8()
        is_home_record = bool(sub_byte_field(bp1, 0x01))
        go_home_mode = GoHomeMode(sub_byte_field(bp1, 0x02))
        aircraft_head_direction = sub_byte_field(bp1, 0x04)
        is_dynamic_home_point_enabled = bool(sub_byte_field(bp1, 0x08))
        is_near_distance_limit = bool(sub_byte_field(bp1, 0x10))
        is_near_height_limit = bool(sub_byte_field(bp1, 0x20))
        is_multiple_mode_open = bool(sub_byte_field(bp1, 0x40))
        has_go_home = bool(sub_byte_field(bp1, 0x80))

        bp2 = r.read_u8()
        compass_state = CompassCalibrationState(sub_byte_field(bp2, 0x03))
        is_compass_adjust = bool(sub_byte_field(bp2, 0x04))
        is_beginner_mode = bool(sub_byte_field(bp2, 0x08))
        is_ioc_open = bool(sub_byte_field(bp2, 0x10))
        ioc_mode = IOCMode(sub_byte_field(bp2, 0xE0))

        go_home_height = r.read_u16()
        ioc_course_lock_angle = r.read_i16()
        _flight_record_sd_state = r.read_u8()
        _record_sd_capacity_percent = r.read_u8()
        _record_sd_left_time = r.read_u16()
        current_flight_record_index = r.read_u16()

        max_allowed_height: float = 0.0
        if version >= 8:
            r.skip(5)
            max_allowed_height = r.read_f32()

        return cls(
            longitude=longitude,
            latitude=latitude,
            altitude=altitude,
            is_home_record=is_home_record,
            go_home_mode=go_home_mode,
            aircraft_head_direction=aircraft_head_direction,
            is_dynamic_home_point_enabled=is_dynamic_home_point_enabled,
            is_near_distance_limit=is_near_distance_limit,
            is_near_height_limit=is_near_height_limit,
            is_multiple_mode_open=is_multiple_mode_open,
            has_go_home=has_go_home,
            compass_state=compass_state,
            is_compass_adjust=is_compass_adjust,
            is_beginner_mode=is_beginner_mode,
            is_ioc_open=is_ioc_open,
            ioc_mode=ioc_mode,
            go_home_height=go_home_height,
            ioc_course_lock_angle=ioc_course_lock_angle,
            current_flight_record_index=current_flight_record_index,
            max_allowed_height=max_allowed_height,
        )
