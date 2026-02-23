"""Tests for frame building from records."""

from __future__ import annotations

from pydjirecord.frame import Frame
from pydjirecord.frame.battery import FrameBattery
from pydjirecord.frame.builder import _finalize, _reset, records_to_frames
from pydjirecord.layout.details import Details, ProductType
from pydjirecord.record import Record
from pydjirecord.record.app_tip import AppTip
from pydjirecord.record.gimbal import Gimbal, GimbalMode
from pydjirecord.record.osd import (
    OSD,
    AppCommand,
    BatteryType,
    DroneType,
    FlightAction,
    FlightMode,
    GoHomeStatus,
    GroundOrSky,
    ImuInitFailReason,
    MotorStartFailedCause,
    NonGPSCause,
)


def _make_osd(**overrides: object) -> OSD:
    """Build a minimal OSD record with defaults."""
    defaults = dict(
        longitude=19.8,
        latitude=41.3,
        altitude=50.0,
        speed_x=1.0,
        speed_y=2.0,
        speed_z=0.5,
        pitch=0.0,
        roll=0.0,
        yaw=90.0,
        flight_mode=FlightMode.GPS_ATTI,
        rc_outcontrol=False,
        app_command=AppCommand(0),
        can_ioc_work=False,
        ground_or_sky=GroundOrSky.SKY,
        is_motor_up=True,
        is_swave_work=False,
        go_home_status=GoHomeStatus.STANDBY,
        is_vision_used=False,
        voltage_warning=0,
        is_imu_preheated=True,
        is_gps_valid=True,
        is_compass_error=False,
        wave_error=False,
        gps_level=3,
        battery_type=BatteryType.SMART,
        is_out_of_limit=False,
        is_go_home_height_modified=False,
        is_propeller_catapult=False,
        is_motor_blocked=False,
        is_not_enough_force=False,
        is_barometer_dead_in_air=False,
        is_vibrating=False,
        is_acceletor_over_range=False,
        gps_num=12,
        flight_action=FlightAction.NONE,
        motor_start_failed_cause=MotorStartFailedCause.NONE,
        non_gps_cause=NonGPSCause.ALREADY,
        battery=80,
        s_wave_height=0.0,
        fly_time=10.0,
        drone_type=DroneType.MAVIC_AIR2,
        imu_init_fail_reason=ImuInitFailReason.MONITOR_ERROR,
    )
    defaults.update(overrides)
    return OSD(**defaults)


class TestRecordsToFrames:
    def test_empty_records(self) -> None:
        details = Details(product_type=ProductType.MAVIC_AIR2)
        frames = records_to_frames([], details)
        assert frames == []

    def test_single_osd_no_push(self) -> None:
        """A single OSD doesn't push a frame (frame pushed on NEXT OSD)."""
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [Record(record_type=1, data=_make_osd())]
        frames = records_to_frames(records, details)
        assert len(frames) == 0

    def test_two_osds_push_one_frame(self) -> None:
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [
            Record(record_type=1, data=_make_osd(fly_time=1.0)),
            Record(record_type=1, data=_make_osd(fly_time=2.0)),
        ]
        frames = records_to_frames(records, details)
        assert len(frames) == 1
        assert frames[0].osd.fly_time == 1.0

    def test_gimbal_accumulates(self) -> None:
        details = Details(product_type=ProductType.MAVIC_AIR2)
        gimbal = Gimbal(
            pitch=-10.0,
            roll=0.0,
            yaw=45.0,
            mode=GimbalMode.YAW_FOLLOW,
            is_pitch_at_limit=True,
            is_roll_at_limit=False,
            is_yaw_at_limit=False,
            is_stuck=False,
        )
        records = [
            Record(record_type=3, data=gimbal),
            Record(record_type=1, data=_make_osd(fly_time=1.0)),
            Record(record_type=1, data=_make_osd(fly_time=2.0)),
        ]
        frames = records_to_frames(records, details)
        assert len(frames) == 1
        assert frames[0].gimbal.pitch == -10.0
        assert frames[0].gimbal.mode == GimbalMode.YAW_FOLLOW

    def test_app_tip_accumulates(self) -> None:
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [
            Record(record_type=9, data=AppTip(message="Hello")),
            Record(record_type=9, data=AppTip(message="World")),
            Record(record_type=1, data=_make_osd(fly_time=1.0)),
            Record(record_type=1, data=_make_osd(fly_time=2.0)),
        ]
        frames = records_to_frames(records, details)
        assert "Hello" in frames[0].app.tip
        assert "World" in frames[0].app.tip

    def test_app_tip_resets_between_frames(self) -> None:
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [
            Record(record_type=9, data=AppTip(message="Tip1")),
            Record(record_type=1, data=_make_osd(fly_time=1.0)),
            Record(record_type=1, data=_make_osd(fly_time=2.0)),
            Record(record_type=1, data=_make_osd(fly_time=3.0)),
        ]
        frames = records_to_frames(records, details)
        assert len(frames) == 2
        assert "Tip1" in frames[0].app.tip
        # Second frame tip should NOT contain Tip1 (only flight mode change msg)
        assert "Tip1" not in frames[1].app.tip


class TestFinalize:
    def test_height_max_tracking(self) -> None:
        frame = Frame()
        frame.osd.height = 100.0
        frame.osd.height_max = 50.0
        _finalize(frame)
        assert frame.osd.height_max == 100.0

    def test_cell_voltage_estimation(self) -> None:
        frame = Frame()
        frame.battery = FrameBattery(
            cell_num=3,
            cell_voltages=[0.0, 0.0, 0.0],
            voltage=11.4,
        )
        _finalize(frame)
        assert frame.battery.is_cell_voltage_estimated is True
        assert abs(frame.battery.cell_voltages[0] - 3.8) < 0.01

    def test_cell_voltage_deviation(self) -> None:
        frame = Frame()
        frame.battery = FrameBattery(
            cell_num=3,
            cell_voltages=[3.8, 3.7, 3.9],
            voltage=11.4,
        )
        _finalize(frame)
        assert frame.battery.cell_voltage_deviation > 0


class TestReset:
    def test_resets_camera_photo(self) -> None:
        frame = Frame()
        frame.camera.is_photo = True
        _reset(frame)
        assert frame.camera.is_photo is False

    def test_resets_app_messages(self) -> None:
        frame = Frame()
        frame.app.tip = "test"
        frame.app.warn = "warning"
        _reset(frame)
        assert frame.app.tip == ""
        assert frame.app.warn == ""
