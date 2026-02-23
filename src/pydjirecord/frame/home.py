"""Frame home sub-field."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..record.home import CompassCalibrationState, GoHomeMode, IOCMode


@dataclass
class FrameHome:
    """Normalized home point frame data."""

    latitude: float = 0.0
    longitude: float = 0.0
    altitude: float = 0.0
    height_limit: float = 0.0
    is_home_record: bool = False
    go_home_mode: GoHomeMode | None = None
    is_dynamic_home_point_enabled: bool = False
    is_near_distance_limit: bool = False
    is_near_height_limit: bool = False
    is_compass_calibrating: bool = False
    compass_calibration_state: CompassCalibrationState | None = None
    is_multiple_mode_enabled: bool = False
    is_beginner_mode: bool = False
    is_ioc_enabled: bool = False
    ioc_mode: IOCMode | None = None
    go_home_height: int = 0
    ioc_course_lock_angle: int | None = None
    max_allowed_height: float = 0.0
    current_flight_record_index: int = 0
