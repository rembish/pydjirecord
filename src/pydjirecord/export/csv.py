"""CSV export."""

from __future__ import annotations

import csv
import sys
from datetime import datetime
from enum import IntEnum
from typing import TYPE_CHECKING, Any, TextIO

from ..frame.details import FrameDetails

if TYPE_CHECKING:
    from ..frame import Frame
    from ..layout.details import Details


def _val(v: Any) -> str:
    """Format a value for CSV output."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return str(v).lower()
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, IntEnum):
        return v.name
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def export_csv(frames: list[Frame], details: Details, output: TextIO = sys.stdout) -> None:
    """Export frames as CSV with ~120 columns."""
    if not frames:
        return

    frame_details = FrameDetails.from_details(details)

    # Determine cell count from first frame
    cell_num = frames[0].battery.cell_num if frames else 0

    # Build headers
    headers: list[str] = [
        "CUSTOM.dateTime",
        # OSD
        "OSD.flyTime",
        "OSD.latitude",
        "OSD.longitude",
        "OSD.height",
        "OSD.heightMax",
        "OSD.vpsHeight",
        "OSD.altitude",
        "OSD.xSpeed",
        "OSD.xSpeedMax",
        "OSD.ySpeed",
        "OSD.ySpeedMax",
        "OSD.zSpeed",
        "OSD.zSpeedMax",
        "OSD.pitch",
        "OSD.roll",
        "OSD.yaw",
        "OSD.flycState",
        "OSD.flycCommand",
        "OSD.flightAction",
        "OSD.isGPSUsed",
        "OSD.nonGPSCause",
        "OSD.gpsNum",
        "OSD.gpsLevel",
        "OSD.droneType",
        "OSD.isSwaveWork",
        "OSD.waveError",
        "OSD.goHomeStatus",
        "OSD.batteryType",
        "OSD.isOnGround",
        "OSD.isMotorOn",
        "OSD.isMotorBlocked",
        "OSD.motorStartFailedCause",
        "OSD.isImuPreheated",
        "OSD.imuInitFailReason",
        "OSD.isAcceleratorOverRange",
        "OSD.isBarometerDeadInAir",
        "OSD.isCompassError",
        "OSD.isGoHomeHeightModified",
        "OSD.canIOCWork",
        "OSD.isNotEnoughForce",
        "OSD.isOutOfLimit",
        "OSD.isPropellerCatapult",
        "OSD.isVibrating",
        "OSD.isVisionUsed",
        "OSD.voltageWarning",
        # GIMBAL
        "GIMBAL.mode",
        "GIMBAL.pitch",
        "GIMBAL.roll",
        "GIMBAL.yaw",
        "GIMBAL.isPitchAtLimit",
        "GIMBAL.isRollAtLimit",
        "GIMBAL.isYawAtLimit",
        "GIMBAL.isStuck",
        # CAMERA
        "CAMERA.isPhoto",
        "CAMERA.isVideo",
        "CAMERA.sdCardIsInserted",
        "CAMERA.sdCardState",
        # RC
        "RC.downlinkSignal",
        "RC.uplinkSignal",
        "RC.aileron",
        "RC.elevator",
        "RC.throttle",
        "RC.rudder",
        # BATTERY
        "BATTERY.chargeLevel",
        "BATTERY.voltage",
        "BATTERY.current",
        "BATTERY.currentCapacity",
        "BATTERY.fullCapacity",
        "BATTERY.cellNum",
        "BATTERY.isCellVoltageEstimated",
    ]
    # Dynamic cell voltage columns
    for i in range(1, cell_num + 1):
        headers.append(f"BATTERY.cellVoltage{i}")
    headers.extend(
        [
            "BATTERY.cellVoltageDeviation",
            "BATTERY.maxCellVoltageDeviation",
            "BATTERY.temperature",
            "BATTERY.minTemperature",
            "BATTERY.maxTemperature",
            # HOME
            "HOME.latitude",
            "HOME.longitude",
            "HOME.altitude",
            "HOME.heightLimit",
            "HOME.isHomeRecord",
            "HOME.goHomeMode",
            "HOME.isDynamicHomePointEnabled",
            "HOME.isNearDistanceLimit",
            "HOME.isNearHeightLimit",
            "HOME.isCompassCalibrating",
            "HOME.compassCalibrationState",
            "HOME.isMultipleModeEnabled",
            "HOME.isBeginnerMode",
            "HOME.isIOCEnabled",
            "HOME.IOCMode",
            "HOME.goHomeHeight",
            "HOME.IOCCourseLockAngle",
            "HOME.maxAllowedHeight",
            "HOME.currentFlightRecordIndex",
            # RECOVER
            "RECOVER.appPlatform",
            "RECOVER.appVersion",
            "RECOVER.aircraftName",
            "RECOVER.aircraftSerial",
            "RECOVER.cameraSerial",
            "RECOVER.rcSerial",
            "RECOVER.batterySerial",
            # APP
            "APP.tip",
            "APP.warn",
            # DETAILS
            "DETAILS.totalTime",
            "DETAILS.totalDistance",
            "DETAILS.maxHeight",
            "DETAILS.maxHorizontalSpeed",
            "DETAILS.maxVerticalSpeed",
            "DETAILS.photoNum",
            "DETAILS.videoTime",
            "DETAILS.aircraftName",
            "DETAILS.aircraftSerial",
            "DETAILS.cameraSerial",
            "DETAILS.rcSerial",
            "DETAILS.appPlatform",
            "DETAILS.appVersion",
        ]
    )

    writer = csv.writer(output)
    writer.writerow(headers)

    for f in frames:
        row: list[str] = [
            _val(f.custom.date_time),
            # OSD
            _val(f.osd.fly_time),
            _val(f.osd.latitude),
            _val(f.osd.longitude),
            _val(f.osd.height),
            _val(f.osd.height_max),
            _val(f.osd.vps_height),
            _val(f.osd.altitude),
            _val(f.osd.x_speed),
            _val(f.osd.x_speed_max),
            _val(f.osd.y_speed),
            _val(f.osd.y_speed_max),
            _val(f.osd.z_speed),
            _val(f.osd.z_speed_max),
            _val(f.osd.pitch),
            _val(f.osd.roll),
            _val(f.osd.yaw),
            _val(f.osd.flyc_state),
            _val(f.osd.flyc_command),
            _val(f.osd.flight_action),
            _val(f.osd.is_gpd_used),
            _val(f.osd.non_gps_cause),
            _val(f.osd.gps_num),
            _val(f.osd.gps_level),
            _val(f.osd.drone_type),
            _val(f.osd.is_swave_work),
            _val(f.osd.wave_error),
            _val(f.osd.go_home_status),
            _val(f.osd.battery_type),
            _val(f.osd.is_on_ground),
            _val(f.osd.is_motor_on),
            _val(f.osd.is_motor_blocked),
            _val(f.osd.motor_start_failed_cause),
            _val(f.osd.is_imu_preheated),
            _val(f.osd.imu_init_fail_reason),
            _val(f.osd.is_acceletor_over_range),
            _val(f.osd.is_barometer_dead_in_air),
            _val(f.osd.is_compass_error),
            _val(f.osd.is_go_home_height_modified),
            _val(f.osd.can_ioc_work),
            _val(f.osd.is_not_enough_force),
            _val(f.osd.is_out_of_limit),
            _val(f.osd.is_propeller_catapult),
            _val(f.osd.is_vibrating),
            _val(f.osd.is_vision_used),
            _val(f.osd.voltage_warning),
            # GIMBAL
            _val(f.gimbal.mode),
            _val(f.gimbal.pitch),
            _val(f.gimbal.roll),
            _val(f.gimbal.yaw),
            _val(f.gimbal.is_pitch_at_limit),
            _val(f.gimbal.is_roll_at_limit),
            _val(f.gimbal.is_yaw_at_limit),
            _val(f.gimbal.is_stuck),
            # CAMERA
            _val(f.camera.is_photo),
            _val(f.camera.is_video),
            _val(f.camera.sd_card_is_inserted),
            _val(f.camera.sd_card_state),
            # RC
            _val(f.rc.downlink_signal),
            _val(f.rc.uplink_signal),
            _val(f.rc.aileron),
            _val(f.rc.elevator),
            _val(f.rc.throttle),
            _val(f.rc.rudder),
            # BATTERY
            _val(f.battery.charge_level),
            _val(f.battery.voltage),
            _val(f.battery.current),
            _val(f.battery.current_capacity),
            _val(f.battery.full_capacity),
            _val(f.battery.cell_num),
            _val(f.battery.is_cell_voltage_estimated),
        ]
        # Dynamic cell voltages
        for i in range(cell_num):
            if i < len(f.battery.cell_voltages):
                row.append(_val(f.battery.cell_voltages[i]))
            else:
                row.append("")
        row.extend(
            [
                _val(f.battery.cell_voltage_deviation),
                _val(f.battery.max_cell_voltage_deviation),
                _val(f.battery.temperature),
                _val(f.battery.min_temperature),
                _val(f.battery.max_temperature),
                # HOME
                _val(f.home.latitude),
                _val(f.home.longitude),
                _val(f.home.altitude),
                _val(f.home.height_limit),
                _val(f.home.is_home_record),
                _val(f.home.go_home_mode),
                _val(f.home.is_dynamic_home_point_enabled),
                _val(f.home.is_near_distance_limit),
                _val(f.home.is_near_height_limit),
                _val(f.home.is_compass_calibrating),
                _val(f.home.compass_calibration_state),
                _val(f.home.is_multiple_mode_enabled),
                _val(f.home.is_beginner_mode),
                _val(f.home.is_ioc_enabled),
                _val(f.home.ioc_mode),
                _val(f.home.go_home_height),
                _val(f.home.ioc_course_lock_angle),
                _val(f.home.max_allowed_height),
                _val(f.home.current_flight_record_index),
                # RECOVER
                _val(f.recover.app_platform),
                _val(f.recover.app_version),
                _val(f.recover.aircraft_name),
                _val(f.recover.aircraft_sn),
                _val(f.recover.camera_sn),
                _val(f.recover.rc_sn),
                _val(f.recover.battery_sn),
                # APP
                _val(f.app.tip),
                _val(f.app.warn),
                # DETAILS
                _val(frame_details.total_time),
                _val(frame_details.total_distance),
                _val(frame_details.max_height),
                _val(frame_details.max_horizontal_speed),
                _val(frame_details.max_vertical_speed),
                _val(frame_details.photo_num),
                _val(frame_details.video_time),
                _val(frame_details.aircraft_name),
                _val(frame_details.aircraft_sn),
                _val(frame_details.camera_sn),
                _val(frame_details.rc_sn),
                _val(frame_details.app_platform),
                _val(frame_details.app_version),
            ]
        )
        writer.writerow(row)
