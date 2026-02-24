"""Tests for frame building from records."""

from __future__ import annotations

import math

from pydjirecord.frame import Frame
from pydjirecord.frame.battery import FrameBattery
from pydjirecord.frame.builder import _finalize, _reset, compute_video_time, records_to_frames
from pydjirecord.layout.details import Details, ProductType
from pydjirecord.record import Record
from pydjirecord.record.app_tip import AppTip
from pydjirecord.record.camera import Camera, CameraWorkMode, SDCardState
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

    def test_single_osd_produces_one_frame(self) -> None:
        """A single OSD produces exactly one frame (flushed at end of loop)."""
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [Record(record_type=1, data=_make_osd(fly_time=1.0))]
        frames = records_to_frames(records, details)
        assert len(frames) == 1
        assert frames[0].osd.fly_time == 1.0

    def test_two_osds_produce_two_frames(self) -> None:
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [
            Record(record_type=1, data=_make_osd(fly_time=1.0)),
            Record(record_type=1, data=_make_osd(fly_time=2.0)),
        ]
        frames = records_to_frames(records, details)
        assert len(frames) == 2
        assert frames[0].osd.fly_time == 1.0
        assert frames[1].osd.fly_time == 2.0

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
        assert len(frames) == 2
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
        assert len(frames) == 3
        assert "Tip1" in frames[0].app.tip
        # Second frame tip should NOT contain Tip1 (only flight mode change msg)
        assert "Tip1" not in frames[1].app.tip


class TestCumulativeDistance:
    def test_zero_with_single_osd(self) -> None:
        """First frame has no previous point, cumulative distance stays 0."""
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [Record(record_type=1, data=_make_osd(latitude=41.0, longitude=19.0, is_gps_valid=True, gps_level=4))]
        frames = records_to_frames(records, details)
        assert frames[0].osd.cumulative_distance == 0.0

    def test_accumulates_between_valid_gps_frames(self) -> None:
        """Cumulative distance grows with successive valid GPS frames."""
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [
            Record(
                record_type=1,
                data=_make_osd(latitude=41.0, longitude=19.0, is_gps_valid=True, gps_level=4, fly_time=1.0),
            ),
            Record(
                record_type=1,
                data=_make_osd(latitude=41.001, longitude=19.0, is_gps_valid=True, gps_level=4, fly_time=2.0),
            ),
        ]
        frames = records_to_frames(records, details)
        assert frames[0].osd.cumulative_distance == 0.0
        # ~111 m per 0.001 degree latitude
        assert 100.0 < frames[1].osd.cumulative_distance < 120.0

    def test_no_accumulation_below_gps_level_3(self) -> None:
        """GPS fixes with level < 3 are not counted."""
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [
            Record(
                record_type=1,
                data=_make_osd(latitude=41.0, longitude=19.0, is_gps_valid=True, gps_level=4, fly_time=1.0),
            ),
            Record(
                record_type=1,
                data=_make_osd(latitude=41.001, longitude=19.0, is_gps_valid=True, gps_level=2, fly_time=2.0),
            ),
            Record(
                record_type=1,
                data=_make_osd(latitude=41.002, longitude=19.0, is_gps_valid=True, gps_level=4, fly_time=3.0),
            ),
        ]
        frames = records_to_frames(records, details)
        # Frame 2 has poor GPS — no step added
        assert frames[1].osd.cumulative_distance == 0.0
        # Frame 3 jumps from frame 1's position (last valid), skipping frame 2
        assert 200.0 < frames[2].osd.cumulative_distance < 240.0

    def test_no_accumulation_when_gps_not_used(self) -> None:
        """GPS fixes with is_gps_valid=False are not counted."""
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [
            Record(
                record_type=1,
                data=_make_osd(latitude=41.0, longitude=19.0, is_gps_valid=True, gps_level=4, fly_time=1.0),
            ),
            Record(
                record_type=1,
                data=_make_osd(latitude=41.001, longitude=19.0, is_gps_valid=False, gps_level=4, fly_time=2.0),
            ),
        ]
        frames = records_to_frames(records, details)
        assert frames[1].osd.cumulative_distance == 0.0

    def test_carries_across_frames(self) -> None:
        """Cumulative distance carries forward from frame to frame."""
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [
            Record(
                record_type=1,
                data=_make_osd(latitude=41.0, longitude=19.0, is_gps_valid=True, gps_level=4, fly_time=1.0),
            ),
            Record(
                record_type=1,
                data=_make_osd(latitude=41.001, longitude=19.0, is_gps_valid=True, gps_level=4, fly_time=2.0),
            ),
            Record(
                record_type=1,
                data=_make_osd(latitude=41.002, longitude=19.0, is_gps_valid=True, gps_level=4, fly_time=3.0),
            ),
        ]
        frames = records_to_frames(records, details)
        d1 = frames[1].osd.cumulative_distance
        d2 = frames[2].osd.cumulative_distance
        assert d2 > d1
        # Each step is roughly the same distance
        assert abs(d2 - 2 * d1) < 1.0


class TestHSpeedComputation:
    def test_h_speed_computed(self) -> None:
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [
            Record(record_type=1, data=_make_osd(speed_x=3.0, speed_y=4.0, fly_time=1.0)),
            Record(record_type=1, data=_make_osd(speed_x=0.0, speed_y=0.0, fly_time=2.0)),
        ]
        frames = records_to_frames(records, details)
        assert len(frames) == 2
        assert abs(frames[0].osd.h_speed - 5.0) < 0.001  # 3-4-5 triangle

    def test_h_speed_max_tracks_maximum(self) -> None:
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [
            Record(record_type=1, data=_make_osd(speed_x=3.0, speed_y=4.0, fly_time=1.0)),
            Record(record_type=1, data=_make_osd(speed_x=1.0, speed_y=1.0, fly_time=2.0)),
            Record(record_type=1, data=_make_osd(speed_x=0.0, speed_y=0.0, fly_time=3.0)),
        ]
        frames = records_to_frames(records, details)
        assert len(frames) == 3
        # First frame: h_speed = 5.0
        assert abs(frames[0].osd.h_speed - 5.0) < 0.001
        assert abs(frames[0].osd.h_speed_max - 5.0) < 0.001
        # Second frame: h_speed = sqrt(2) ≈ 1.414, but max carried from first
        assert abs(frames[1].osd.h_speed - math.sqrt(2)) < 0.001
        assert abs(frames[1].osd.h_speed_max - 5.0) < 0.001

    def test_finalize_h_speed(self) -> None:
        frame = Frame()
        frame.osd.x_speed = 6.0
        frame.osd.y_speed = 8.0
        _finalize(frame)
        assert abs(frame.osd.h_speed - 10.0) < 0.001
        assert abs(frame.osd.h_speed_max - 10.0) < 0.001


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


def _make_camera(*, is_recording: bool = False, record_time: int = 0) -> Camera:
    """Build a Camera record with the given recording state and record_time."""
    return Camera(
        is_shooting_single_photo=False,
        is_recording=is_recording,
        has_sd_card=True,
        sd_card_state=SDCardState.NORMAL,
        work_mode=CameraWorkMode.RECORDING if is_recording else CameraWorkMode.CAPTURE,
        record_time=record_time,
    )


class TestVideoTime:
    def test_no_recording_zero_video_time(self) -> None:
        """No recording segments → video_time is 0."""
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [
            Record(record_type=4, data=_make_camera(is_recording=False, record_time=0)),
            Record(record_type=1, data=_make_osd(fly_time=1.0)),
            Record(record_type=1, data=_make_osd(fly_time=2.0)),
        ]
        frames = records_to_frames(records, details)
        assert compute_video_time(frames) == 0.0

    def test_single_recording_segment(self) -> None:
        """One recording segment: max record_time is the video duration."""
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [
            Record(record_type=4, data=_make_camera(is_recording=True, record_time=0)),
            Record(record_type=1, data=_make_osd(fly_time=1.0)),
            Record(record_type=4, data=_make_camera(is_recording=True, record_time=10)),
            Record(record_type=1, data=_make_osd(fly_time=2.0)),
            Record(record_type=4, data=_make_camera(is_recording=True, record_time=20)),
            Record(record_type=1, data=_make_osd(fly_time=3.0)),
            Record(record_type=4, data=_make_camera(is_recording=False, record_time=0)),
            Record(record_type=1, data=_make_osd(fly_time=4.0)),
        ]
        frames = records_to_frames(records, details)
        assert compute_video_time(frames) == 20.0

    def test_two_recording_segments(self) -> None:
        """Two segments: sum of max record_time from each."""
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [
            # Segment 1: record_time goes 0 → 15
            Record(record_type=4, data=_make_camera(is_recording=True, record_time=0)),
            Record(record_type=1, data=_make_osd(fly_time=1.0)),
            Record(record_type=4, data=_make_camera(is_recording=True, record_time=15)),
            Record(record_type=1, data=_make_osd(fly_time=2.0)),
            # Gap: not recording
            Record(record_type=4, data=_make_camera(is_recording=False, record_time=0)),
            Record(record_type=1, data=_make_osd(fly_time=3.0)),
            # Segment 2: record_time goes 0 → 30
            Record(record_type=4, data=_make_camera(is_recording=True, record_time=0)),
            Record(record_type=1, data=_make_osd(fly_time=4.0)),
            Record(record_type=4, data=_make_camera(is_recording=True, record_time=30)),
            Record(record_type=1, data=_make_osd(fly_time=5.0)),
            Record(record_type=4, data=_make_camera(is_recording=False, record_time=0)),
            Record(record_type=1, data=_make_osd(fly_time=6.0)),
        ]
        frames = records_to_frames(records, details)
        assert compute_video_time(frames) == 45.0  # 15 + 30

    def test_recording_still_active_at_end(self) -> None:
        """Recording active at end of log → segment is still counted."""
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [
            Record(record_type=4, data=_make_camera(is_recording=True, record_time=0)),
            Record(record_type=1, data=_make_osd(fly_time=1.0)),
            Record(record_type=4, data=_make_camera(is_recording=True, record_time=44)),
            Record(record_type=1, data=_make_osd(fly_time=2.0)),
        ]
        frames = records_to_frames(records, details)
        assert compute_video_time(frames) == 44.0

    def test_record_time_in_frame(self) -> None:
        """Camera.record_time propagates to FrameCamera.record_time."""
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [
            Record(record_type=4, data=_make_camera(is_recording=True, record_time=42)),
            Record(record_type=1, data=_make_osd(fly_time=1.0)),
        ]
        frames = records_to_frames(records, details)
        assert frames[0].camera.record_time == 42
