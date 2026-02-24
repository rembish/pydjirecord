"""Convert raw records to normalized frames."""

from __future__ import annotations

import math
from copy import deepcopy
from typing import TYPE_CHECKING

from ..record.app_serious_warn import AppSeriousWarn
from ..record.app_tip import AppTip
from ..record.app_warn import AppWarn
from ..record.camera import Camera
from ..record.center_battery import CenterBattery
from ..record.custom import Custom
from ..record.gimbal import Gimbal
from ..record.home import Home
from ..record.ofdm import OFDM
from ..record.osd import OSD, AppCommand, GroundOrSky
from ..record.rc import RC
from ..record.rc_display_field import RCDisplayField
from ..record.recover import Recover
from ..record.smart_battery import SmartBattery
from ..record.smart_battery_group import (
    SmartBatteryDynamic,
    SmartBatterySingleVoltage,
    SmartBatteryStatic,
)
from ..utils import append_message, haversine_distance
from . import Frame
from .battery import FrameBattery
from .recover import FrameRecover

if TYPE_CHECKING:
    from ..layout.details import Details
    from ..record import Record


def records_to_frames(records: list[Record], details: Details) -> list[Frame]:
    """Convert a list of Record objects into normalized Frame objects."""
    frames: list[Frame] = []
    cell_num = details.product_type.battery_cell_num
    frame = Frame()
    frame.battery = FrameBattery(
        cell_num=cell_num,
        cell_voltages=[0.0] * cell_num,
        is_cell_voltage_estimated=True,
    )
    frame.recover = FrameRecover(
        app_platform=details.app_platform,
        app_version=details.app_version,
        aircraft_name=details.aircraft_name,
        aircraft_sn=details.aircraft_sn,
        camera_sn=details.camera_sn,
        rc_sn=details.rc_sn,
        battery_sn=details.battery_sn,
    )

    frame_index = 0
    # Previous valid GPS fix for cumulative distance accumulation.
    # Validity mirrors CoordinateIsValid in the DJI C++ reference:
    # gps_level >= 3 and is_gps_valid (isGPSBeingUsed).
    _prev_gps: tuple[float, float] | None = None  # (lat, lon)

    for record in records:
        data = record.data

        if isinstance(data, OSD):
            if frame_index > 0:
                _finalize(frame)
                frames.append(deepcopy(frame))
                _reset(frame)

            frame.osd.fly_time = data.fly_time
            # Only update coordinates if valid, preserving any prior values
            if data.latitude != 0.0 or data.longitude != 0.0:
                frame.osd.latitude = data.latitude
                frame.osd.longitude = data.longitude

            # Accumulate GPS track distance — mirrors CoordinateIsValid from
            # the DJI C++ reference: gps_level >= 3 and is_gps_valid.
            if data.is_gps_valid and data.gps_level >= 3 and (data.latitude != 0.0 or data.longitude != 0.0):
                curr = (data.latitude, data.longitude)
                if _prev_gps is not None:
                    frame.osd.cumulative_distance += haversine_distance(_prev_gps[0], _prev_gps[1], curr[0], curr[1])
                _prev_gps = curr

            frame.osd.altitude = data.altitude + frame.home.altitude
            frame.osd.height = data.altitude
            frame.osd.vps_height = data.s_wave_height
            frame.osd.x_speed = data.speed_x
            frame.osd.y_speed = data.speed_y
            frame.osd.z_speed = data.speed_z
            frame.osd.pitch = data.pitch
            frame.osd.yaw = data.yaw
            frame.osd.roll = data.roll

            if frame.osd.flyc_state != data.flight_mode:
                frame.app.tip = append_message(frame.app.tip, f"Flight mode changed to {data.flight_mode.name}.")
            frame.osd.flyc_state = data.flight_mode
            if isinstance(data.app_command, AppCommand) and data.app_command.value == 0:
                frame.osd.flyc_command = None
            else:
                frame.osd.flyc_command = data.app_command
            frame.osd.flight_action = data.flight_action
            frame.osd.gps_num = data.gps_num
            frame.osd.gps_level = data.gps_level
            frame.osd.is_gpd_used = data.is_gps_valid
            frame.osd.non_gps_cause = data.non_gps_cause
            frame.osd.drone_type = data.drone_type
            frame.osd.is_swave_work = data.is_swave_work
            frame.osd.wave_error = data.wave_error
            frame.osd.go_home_status = data.go_home_status
            frame.osd.battery_type = data.battery_type
            frame.osd.is_on_ground = data.ground_or_sky == GroundOrSky.GROUND
            frame.osd.is_motor_on = data.is_motor_up
            frame.osd.is_motor_blocked = data.is_motor_blocked
            frame.osd.motor_start_failed_cause = data.motor_start_failed_cause
            frame.osd.is_imu_preheated = data.is_imu_preheated
            frame.osd.imu_init_fail_reason = data.imu_init_fail_reason
            frame.osd.is_acceletor_over_range = data.is_acceletor_over_range
            frame.osd.is_barometer_dead_in_air = data.is_barometer_dead_in_air
            frame.osd.is_compass_error = data.is_compass_error
            frame.osd.is_go_home_height_modified = data.is_go_home_height_modified
            frame.osd.can_ioc_work = data.can_ioc_work
            frame.osd.is_not_enough_force = data.is_not_enough_force
            frame.osd.is_out_of_limit = data.is_out_of_limit
            frame.osd.is_propeller_catapult = data.is_propeller_catapult
            frame.osd.is_vibrating = data.is_vibrating
            frame.osd.is_vision_used = data.is_vision_used
            frame.osd.voltage_warning = data.voltage_warning

            frame_index += 1

        elif isinstance(data, Gimbal):
            frame.gimbal.mode = data.mode
            frame.gimbal.pitch = data.pitch
            frame.gimbal.roll = data.roll
            frame.gimbal.yaw = data.yaw
            if not frame.gimbal.is_pitch_at_limit and data.is_pitch_at_limit:
                frame.app.tip = append_message(frame.app.tip, "Gimbal pitch axis endpoint reached.")
            frame.gimbal.is_pitch_at_limit = data.is_pitch_at_limit
            if not frame.gimbal.is_roll_at_limit and data.is_roll_at_limit:
                frame.app.tip = append_message(frame.app.tip, "Gimbal roll axis endpoint reached.")
            frame.gimbal.is_roll_at_limit = data.is_roll_at_limit
            if not frame.gimbal.is_yaw_at_limit and data.is_yaw_at_limit:
                frame.app.tip = append_message(frame.app.tip, "Gimbal yaw axis endpoint reached.")
            frame.gimbal.is_yaw_at_limit = data.is_yaw_at_limit
            frame.gimbal.is_stuck = data.is_stuck

        elif isinstance(data, Camera):
            frame.camera.is_photo = data.is_shooting_single_photo
            frame.camera.is_video = data.is_recording
            frame.camera.sd_card_is_inserted = data.has_sd_card
            frame.camera.sd_card_state = data.sd_card_state
            frame.camera.record_time = data.record_time
            frame.camera.remain_photo_num = data.remain_photo_num

        elif isinstance(data, (RC, RCDisplayField)):
            frame.rc.aileron = data.aileron
            frame.rc.elevator = data.elevator
            frame.rc.throttle = data.throttle
            frame.rc.rudder = data.rudder

        elif isinstance(data, CenterBattery):
            frame.battery.charge_level = data.relative_capacity
            frame.battery.voltage = data.voltage
            frame.battery.current_capacity = data.current_capacity
            frame.battery.full_capacity = data.full_capacity
            frame.battery.is_cell_voltage_estimated = False

            cvs = frame.battery.cell_voltages
            cells = [
                data.voltage_cell1,
                data.voltage_cell2,
                data.voltage_cell3,
                data.voltage_cell4,
                data.voltage_cell5,
                data.voltage_cell6,
            ]
            for i in range(min(len(cvs), 6)):
                cvs[i] = cells[i]

        elif isinstance(data, SmartBattery):
            frame.battery.charge_level = data.percent
            frame.battery.voltage = data.voltage

        elif isinstance(data, SmartBatteryDynamic):
            if details.product_type.battery_num < 2 or data.index == 1:
                frame.battery.voltage = data.current_voltage
                frame.battery.current = data.current_current
                frame.battery.current_capacity = data.remained_capacity
                frame.battery.full_capacity = data.full_capacity
                frame.battery.charge_level = data.capacity_percent
                frame.battery.temperature = data.temperature

        elif isinstance(data, SmartBatterySingleVoltage):
            n = min(len(frame.battery.cell_voltages), data.cell_count)
            frame.battery.cell_voltages = [0.0] * len(frame.battery.cell_voltages)
            frame.battery.is_cell_voltage_estimated = False
            frame.battery.cell_voltages[:n] = data.cell_voltages[:n]

        elif isinstance(data, SmartBatteryStatic):
            frame.battery.design_capacity = data.designed_capacity
            frame.battery.lifetime_remaining = data.battery_life
            frame.battery.number_of_discharges = data.loop_times

        elif isinstance(data, OFDM):
            if data.is_up:
                frame.rc.uplink_signal = data.signal_percent
            else:
                frame.rc.downlink_signal = data.signal_percent

        elif isinstance(data, Custom):
            frame.custom.date_time = data.update_timestamp

        elif isinstance(data, Home):
            # Only update home coordinates if valid
            if data.latitude != 0.0 or data.longitude != 0.0:
                frame.home.latitude = data.latitude
                frame.home.longitude = data.longitude
            if frame.home.altitude == 0.0:
                frame.osd.altitude += data.altitude
            frame.home.altitude = data.altitude
            frame.home.height_limit = data.max_allowed_height
            frame.home.is_home_record = data.is_home_record
            frame.home.go_home_mode = data.go_home_mode
            frame.home.is_dynamic_home_point_enabled = data.is_dynamic_home_point_enabled
            frame.home.is_near_distance_limit = data.is_near_distance_limit
            frame.home.is_near_height_limit = data.is_near_height_limit
            frame.home.is_compass_calibrating = data.is_compass_adjust
            if data.is_compass_adjust:
                frame.home.compass_calibration_state = data.compass_state
            frame.home.is_multiple_mode_enabled = data.is_multiple_mode_open
            frame.home.is_beginner_mode = data.is_beginner_mode
            frame.home.is_ioc_enabled = data.is_ioc_open
            if data.is_ioc_open:
                frame.home.ioc_mode = data.ioc_mode
            frame.home.go_home_height = data.go_home_height
            if data.is_ioc_open:
                frame.home.ioc_course_lock_angle = data.ioc_course_lock_angle
            frame.home.max_allowed_height = data.max_allowed_height
            frame.home.current_flight_record_index = data.current_flight_record_index

        elif isinstance(data, Recover):
            frame.recover.app_platform = data.app_platform
            frame.recover.app_version = data.app_version
            frame.recover.aircraft_name = data.aircraft_name
            # Only update serials if the new value is at least as long
            if len(data.aircraft_sn) >= len(frame.recover.aircraft_sn):
                frame.recover.aircraft_sn = data.aircraft_sn
            if len(data.camera_sn) >= len(frame.recover.camera_sn):
                frame.recover.camera_sn = data.camera_sn
            if len(data.rc_sn) >= len(frame.recover.rc_sn):
                frame.recover.rc_sn = data.rc_sn
            if len(data.battery_sn) >= len(frame.recover.battery_sn):
                frame.recover.battery_sn = data.battery_sn

        elif isinstance(data, AppTip):
            frame.app.tip = append_message(frame.app.tip, data.message)

        elif isinstance(data, (AppWarn, AppSeriousWarn)):
            frame.app.warn = append_message(frame.app.warn, data.message)

    # Flush the final frame (it has no subsequent OSD to trigger the append)
    if frame_index > 0:
        _finalize(frame)
        frames.append(deepcopy(frame))

    return frames


def _finalize(frame: Frame) -> None:
    """Compute derived values."""
    osd = frame.osd
    bat = frame.battery

    if osd.height_max < osd.height:
        osd.height_max = osd.height
    if osd.x_speed_max < osd.x_speed:
        osd.x_speed_max = osd.x_speed
    if osd.y_speed_max < osd.y_speed:
        osd.y_speed_max = osd.y_speed
    if osd.z_speed_max < osd.z_speed:
        osd.z_speed_max = osd.z_speed

    osd.h_speed = math.sqrt(osd.x_speed**2 + osd.y_speed**2)
    if osd.h_speed_max < osd.h_speed:
        osd.h_speed_max = osd.h_speed

    # Estimate cell voltages if not provided
    if bat.cell_voltages and bat.cell_voltages[0] == 0.0 and bat.voltage > 0.0:
        bat.is_cell_voltage_estimated = True
        avg = bat.voltage / bat.cell_num if bat.cell_num > 0 else 0.0
        for i in range(len(bat.cell_voltages)):
            bat.cell_voltages[i] = avg

    # Temperature tracking
    if bat.temperature > bat.max_temperature:
        bat.max_temperature = bat.temperature
    if bat.temperature < bat.min_temperature or bat.min_temperature == 0.0:
        bat.min_temperature = bat.temperature

    # Cell voltage deviation
    if bat.cell_voltages:
        max_v = max(bat.cell_voltages)
        min_v = min(bat.cell_voltages)
        bat.cell_voltage_deviation = round((max_v - min_v) * 1000.0) / 1000.0
        if bat.cell_voltage_deviation > bat.max_cell_voltage_deviation:
            bat.max_cell_voltage_deviation = bat.cell_voltage_deviation


def _reset(frame: Frame) -> None:
    """Reset event-related values between frames."""
    frame.camera.is_photo = False
    frame.app.tip = ""
    frame.app.warn = ""
    if frame.battery.is_cell_voltage_estimated:
        for i in range(len(frame.battery.cell_voltages)):
            frame.battery.cell_voltages[i] = 0.0


def compute_video_time(frames: list[Frame]) -> float:
    """Compute total video recording duration from Camera record_time segments.

    Each recording segment has ``record_time`` counting up from 0.  The total
    video duration is the sum of the maximum ``record_time`` in each segment.
    """
    total = 0.0
    was_recording = False
    segment_max = 0

    for frame in frames:
        is_recording = frame.camera.is_video
        rt = frame.camera.record_time

        if is_recording:
            if rt > segment_max:
                segment_max = rt
        elif was_recording:
            # Recording just stopped — flush this segment
            total += segment_max
            segment_max = 0

        was_recording = is_recording

    # Flush final segment if still recording at end of log
    if was_recording:
        total += segment_max

    return total


def compute_photo_num(frames: list[Frame]) -> int:
    """Compute total photos taken from Camera ``remain_photo_num`` delta.

    ``remain_photo_num`` is a running counter of remaining photo capacity on
    the SD card.  The difference between the first and last non-zero values
    gives the exact number of photos taken during the flight.
    """
    first: int | None = None
    last: int | None = None

    for frame in frames:
        rpn = frame.camera.remain_photo_num
        if rpn > 0:
            if first is None:
                first = rpn
            last = rpn

    if first is None or last is None:
        return 0
    return max(0, first - last)
