"""Frame OSD sub-field."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..record.osd import (
        AppCommand,
        BatteryType,
        DroneType,
        FlightAction,
        FlightMode,
        GoHomeStatus,
        ImuInitFailReason,
        MotorStartFailedCause,
        NonGPSCause,
    )


@dataclass
class FrameOSD:
    """Normalized OSD frame data."""

    fly_time: float = 0.0
    latitude: float = 0.0
    longitude: float = 0.0
    height: float = 0.0
    height_max: float = 0.0
    vps_height: float = 0.0
    altitude: float = 0.0
    x_speed: float = 0.0
    x_speed_max: float = 0.0
    y_speed: float = 0.0
    y_speed_max: float = 0.0
    z_speed: float = 0.0
    z_speed_max: float = 0.0
    h_speed: float = 0.0
    h_speed_max: float = 0.0
    pitch: float = 0.0
    roll: float = 0.0
    yaw: float = 0.0
    flyc_state: FlightMode | None = None
    flyc_command: AppCommand | None = None
    flight_action: FlightAction | None = None
    is_gpd_used: bool = False
    non_gps_cause: NonGPSCause | None = None
    gps_num: int = 0
    gps_level: int = 0
    drone_type: DroneType | None = None
    is_swave_work: bool = False
    wave_error: bool = False
    go_home_status: GoHomeStatus | None = None
    battery_type: BatteryType | None = None
    is_on_ground: bool = False
    is_motor_on: bool = False
    is_motor_blocked: bool = False
    motor_start_failed_cause: MotorStartFailedCause | None = None
    is_imu_preheated: bool = False
    imu_init_fail_reason: ImuInitFailReason | None = None
    is_acceletor_over_range: bool = False
    is_barometer_dead_in_air: bool = False
    is_compass_error: bool = False
    is_go_home_height_modified: bool = False
    can_ioc_work: bool = False
    is_not_enough_force: bool = False
    is_out_of_limit: bool = False
    is_propeller_catapult: bool = False
    is_vibrating: bool = False
    is_vision_used: bool = False
    voltage_warning: int = 0
