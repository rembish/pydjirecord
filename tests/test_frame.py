"""Tests for frame building from records."""

from __future__ import annotations

import math

from pydjirecord.frame import Frame
from pydjirecord.frame.anomaly import FlightSeverity
from pydjirecord.frame.battery import FrameBattery
from pydjirecord.frame.builder import (
    _finalize,
    _is_valid_gps,
    _reset,
    compute_coordinates,
    compute_flight_anomalies,
    compute_photo_num,
    compute_rc_signal,
    compute_video_time,
    records_to_frames,
)
from pydjirecord.layout.details import Details, ProductType
from pydjirecord.record import Record
from pydjirecord.record.app_tip import AppTip
from pydjirecord.record.camera import Camera, CameraWorkMode, SDCardState
from pydjirecord.record.gimbal import Gimbal, GimbalMode
from pydjirecord.record.home import CompassCalibrationState, GoHomeMode, Home, IOCMode
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


def _make_camera(
    *,
    is_recording: bool = False,
    record_time: int = 0,
    remain_photo_num: int = 0,
) -> Camera:
    """Build a Camera record with the given recording state and record_time."""
    return Camera(
        is_shooting_single_photo=False,
        is_recording=is_recording,
        has_sd_card=True,
        sd_card_state=SDCardState.NORMAL,
        work_mode=CameraWorkMode.RECORDING if is_recording else CameraWorkMode.CAPTURE,
        record_time=record_time,
        remain_photo_num=remain_photo_num,
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


class TestPhotoNum:
    def test_no_photos_zero(self) -> None:
        """No remain_photo_num data → photo_num is 0."""
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [
            Record(record_type=4, data=_make_camera(remain_photo_num=0)),
            Record(record_type=1, data=_make_osd(fly_time=1.0)),
        ]
        frames = records_to_frames(records, details)
        assert compute_photo_num(frames) == 0

    def test_no_change_zero(self) -> None:
        """remain_photo_num stays constant → 0 photos."""
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [
            Record(record_type=4, data=_make_camera(remain_photo_num=2200)),
            Record(record_type=1, data=_make_osd(fly_time=1.0)),
            Record(record_type=4, data=_make_camera(remain_photo_num=2200)),
            Record(record_type=1, data=_make_osd(fly_time=2.0)),
        ]
        frames = records_to_frames(records, details)
        assert compute_photo_num(frames) == 0

    def test_counts_delta(self) -> None:
        """remain_photo_num decreases → delta is the photo count."""
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [
            # First OSD establishes frame_index; Camera before it sets baseline
            Record(record_type=1, data=_make_osd(fly_time=1.0)),
            Record(record_type=4, data=_make_camera(remain_photo_num=2200)),
            Record(record_type=1, data=_make_osd(fly_time=2.0)),
            Record(record_type=4, data=_make_camera(remain_photo_num=2197)),
            Record(record_type=1, data=_make_osd(fly_time=3.0)),
            Record(record_type=4, data=_make_camera(remain_photo_num=2192)),
            Record(record_type=1, data=_make_osd(fly_time=4.0)),
        ]
        frames = records_to_frames(records, details)
        assert compute_photo_num(frames) == 8  # 2200 - 2192

    def test_remain_photo_num_in_frame(self) -> None:
        """Camera.remain_photo_num propagates to FrameCamera."""
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [
            Record(record_type=4, data=_make_camera(remain_photo_num=1500)),
            Record(record_type=1, data=_make_osd(fly_time=1.0)),
        ]
        frames = records_to_frames(records, details)
        assert frames[0].camera.remain_photo_num == 1500


def _make_home(**overrides: object) -> Home:
    """Build a minimal Home record with defaults."""
    defaults = dict(
        longitude=19.8,
        latitude=41.3,
        altitude=95.0,
        is_home_record=True,
        go_home_mode=GoHomeMode.NORMAL,
        is_dynamic_home_point_enabled=False,
        is_near_distance_limit=False,
        is_near_height_limit=False,
        is_multiple_mode_open=False,
        has_go_home=False,
        compass_state=CompassCalibrationState.NOT_CALIBRATING,
        is_compass_adjust=False,
        is_beginner_mode=False,
        is_ioc_open=False,
        ioc_mode=IOCMode.COURSE_LOCK,
        aircraft_head_direction=0,
        go_home_height=30,
        ioc_course_lock_angle=0,
        current_flight_record_index=0,
        max_allowed_height=120.0,
    )
    defaults.update(overrides)
    return Home(**defaults)


class TestIsValidGps:
    def test_valid_coordinates(self) -> None:
        assert _is_valid_gps(41.3, 19.8) is True

    def test_zero_zero_invalid(self) -> None:
        assert _is_valid_gps(0.0, 0.0) is False

    def test_sentinel_invalid(self) -> None:
        """DJI firmware sentinel (800000.0 rad → ~45836623°) is rejected."""
        import math

        sentinel = math.degrees(800000.0)
        assert _is_valid_gps(sentinel, sentinel) is False

    def test_out_of_range_latitude(self) -> None:
        assert _is_valid_gps(91.0, 19.8) is False
        assert _is_valid_gps(-91.0, 19.8) is False

    def test_out_of_range_longitude(self) -> None:
        assert _is_valid_gps(41.3, 181.0) is False
        assert _is_valid_gps(41.3, -181.0) is False

    def test_boundary_values(self) -> None:
        assert _is_valid_gps(90.0, 180.0) is True
        assert _is_valid_gps(-90.0, -180.0) is True


class TestHomeSentinelFiltering:
    def test_sentinel_home_not_applied(self) -> None:
        """Home records with the firmware sentinel are ignored."""
        import math

        sentinel = math.degrees(800000.0)
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [
            Record(record_type=2, data=_make_home(latitude=sentinel, longitude=sentinel)),
            Record(record_type=1, data=_make_osd(fly_time=1.0)),
        ]
        frames = records_to_frames(records, details)
        assert frames[0].home.latitude == 0.0
        assert frames[0].home.longitude == 0.0

    def test_valid_home_applied(self) -> None:
        """Normal home coordinates are applied to the frame."""
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [
            Record(record_type=2, data=_make_home(latitude=41.3, longitude=19.8)),
            Record(record_type=1, data=_make_osd(fly_time=1.0)),
        ]
        frames = records_to_frames(records, details)
        assert frames[0].home.latitude == 41.3
        assert frames[0].home.longitude == 19.8

    def test_sentinel_then_valid_home(self) -> None:
        """Sentinel is ignored but subsequent valid home is applied."""
        import math

        sentinel = math.degrees(800000.0)
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [
            Record(record_type=2, data=_make_home(latitude=sentinel, longitude=sentinel)),
            Record(record_type=1, data=_make_osd(fly_time=1.0)),
            # Second OSD triggers frame[0] append; the valid Home between
            # the two OSDs is already applied to the accumulating frame.
            Record(record_type=2, data=_make_home(latitude=41.3, longitude=19.8)),
            Record(record_type=1, data=_make_osd(fly_time=2.0)),
            Record(record_type=1, data=_make_osd(fly_time=3.0)),
        ]
        frames = records_to_frames(records, details)
        # frame[0] gets the valid home (applied between 1st and 2nd OSD)
        assert frames[0].home.latitude == 41.3
        assert frames[0].home.longitude == 19.8


class TestComputeCoordinates:
    def test_first_valid_gps_returned(self) -> None:
        """Returns coordinates from first frame with valid GPS."""
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [
            Record(
                record_type=1,
                data=_make_osd(
                    latitude=0.0,
                    longitude=0.0,
                    is_gps_valid=False,
                    gps_level=0,
                    fly_time=1.0,
                ),
            ),
            Record(
                record_type=1,
                data=_make_osd(
                    latitude=41.3,
                    longitude=19.8,
                    is_gps_valid=True,
                    gps_level=4,
                    fly_time=2.0,
                ),
            ),
            Record(
                record_type=1,
                data=_make_osd(
                    latitude=41.4,
                    longitude=19.9,
                    is_gps_valid=True,
                    gps_level=4,
                    fly_time=3.0,
                ),
            ),
        ]
        frames = records_to_frames(records, details)
        lat, lon = compute_coordinates(frames)
        assert lat == 41.3
        assert lon == 19.8

    def test_no_valid_gps_returns_zero(self) -> None:
        """Returns (0, 0) when no frame has a valid GPS fix."""
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [
            Record(
                record_type=1,
                data=_make_osd(
                    latitude=0.0,
                    longitude=0.0,
                    is_gps_valid=False,
                    gps_level=0,
                    fly_time=1.0,
                ),
            ),
        ]
        frames = records_to_frames(records, details)
        lat, lon = compute_coordinates(frames)
        assert lat == 0.0
        assert lon == 0.0

    def test_skips_low_gps_level(self) -> None:
        """Frames with gps_level < 3 are skipped."""
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [
            Record(
                record_type=1,
                data=_make_osd(
                    latitude=41.0,
                    longitude=19.0,
                    is_gps_valid=True,
                    gps_level=2,
                    fly_time=1.0,
                ),
            ),
            Record(
                record_type=1,
                data=_make_osd(
                    latitude=41.3,
                    longitude=19.8,
                    is_gps_valid=True,
                    gps_level=4,
                    fly_time=2.0,
                ),
            ),
        ]
        frames = records_to_frames(records, details)
        lat, lon = compute_coordinates(frames)
        assert lat == 41.3
        assert lon == 19.8

    def test_empty_frames(self) -> None:
        assert compute_coordinates([]) == (0.0, 0.0)


class TestFrameDetailsCoordinates:
    def test_uses_header_when_nonzero(self) -> None:
        """Non-zero header coordinates are passed through."""
        from pydjirecord.frame.details import FrameDetails

        d = Details(product_type=ProductType.MAVIC_AIR2, latitude=41.3, longitude=19.8)
        fd = FrameDetails.from_details(d)
        assert fd.latitude == 41.3
        assert fd.longitude == 19.8

    def test_falls_back_to_frames_when_zero(self) -> None:
        """Zero header coordinates are replaced by first valid OSD GPS fix."""
        from pydjirecord.frame.details import FrameDetails

        d = Details(product_type=ProductType.MAVIC_AIR2, latitude=0.0, longitude=0.0)
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [
            Record(
                record_type=1,
                data=_make_osd(
                    latitude=0.0,
                    longitude=0.0,
                    is_gps_valid=False,
                    gps_level=0,
                    fly_time=1.0,
                ),
            ),
            Record(
                record_type=1,
                data=_make_osd(
                    latitude=39.75,
                    longitude=20.0,
                    is_gps_valid=True,
                    gps_level=4,
                    fly_time=2.0,
                ),
            ),
        ]
        frames = records_to_frames(records, details)
        fd = FrameDetails.from_details(d, frames)
        assert fd.latitude == 39.75
        assert fd.longitude == 20.0

    def test_stays_zero_when_no_gps(self) -> None:
        """Zero header + no valid GPS in frames → stays (0, 0)."""
        from pydjirecord.frame.details import FrameDetails

        d = Details(product_type=ProductType.MAVIC_AIR2, latitude=0.0, longitude=0.0)
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [
            Record(
                record_type=1,
                data=_make_osd(
                    latitude=0.0,
                    longitude=0.0,
                    is_gps_valid=False,
                    gps_level=0,
                    fly_time=1.0,
                ),
            ),
        ]
        frames = records_to_frames(records, details)
        fd = FrameDetails.from_details(d, frames)
        assert fd.latitude == 0.0
        assert fd.longitude == 0.0

    def test_total_distance_from_frames(self) -> None:
        """total_distance uses cumulative_distance from last frame."""
        from pydjirecord.frame.details import FrameDetails

        d = Details(product_type=ProductType.MAVIC_AIR2, total_distance=999.0)
        details = Details(product_type=ProductType.MAVIC_AIR2)
        records = [
            Record(
                record_type=1,
                data=_make_osd(
                    latitude=41.0,
                    longitude=19.0,
                    is_gps_valid=True,
                    gps_level=4,
                    fly_time=1.0,
                ),
            ),
            Record(
                record_type=1,
                data=_make_osd(
                    latitude=41.001,
                    longitude=19.0,
                    is_gps_valid=True,
                    gps_level=4,
                    fly_time=2.0,
                ),
            ),
        ]
        frames = records_to_frames(records, details)
        fd = FrameDetails.from_details(d, frames)
        # Should use frame-computed distance (~111 m), not header value (999 m)
        assert 100.0 < fd.total_distance < 120.0

    def test_total_distance_falls_back_to_header(self) -> None:
        """Without frames, total_distance uses header value."""
        from pydjirecord.frame.details import FrameDetails

        d = Details(product_type=ProductType.MAVIC_AIR2, total_distance=1234.5)
        fd = FrameDetails.from_details(d)
        assert fd.total_distance == 1234.5


def _make_frames_with_osd(**overrides: object) -> list[Frame]:
    """Build a list with a single Frame whose OSD fields are overridden."""
    frame = Frame()
    for key, value in overrides.items():
        setattr(frame.osd, key, value)
    return [frame]


class TestFlightAnomalies:
    def test_red_battery_force_landing(self) -> None:
        """BATTERY_FORCE_LANDING action triggers RED severity."""
        frames = _make_frames_with_osd(
            flight_action=FlightAction.BATTERY_FORCE_LANDING,
            height=50.0,
        )
        anomaly = compute_flight_anomalies(frames)
        assert anomaly.severity == FlightSeverity.RED
        assert FlightAction.BATTERY_FORCE_LANDING in anomaly.actions

    def test_red_out_of_control(self) -> None:
        """OUT_OF_CONTROL_GO_HOME action triggers RED severity."""
        frames = _make_frames_with_osd(
            flight_action=FlightAction.OUT_OF_CONTROL_GO_HOME,
            height=30.0,
        )
        anomaly = compute_flight_anomalies(frames)
        assert anomaly.severity == FlightSeverity.RED

    def test_red_motor_blocked_during_flight(self) -> None:
        """Motor blocked at altitude > 1m triggers RED severity."""
        frames = _make_frames_with_osd(
            is_motor_blocked=True,
            height=50.0,
        )
        anomaly = compute_flight_anomalies(frames)
        assert anomaly.severity == FlightSeverity.RED
        assert anomaly.motor_blocked is True

    def test_red_freefall(self) -> None:
        """Descent speed > 10 m/s triggers RED severity."""
        frames = _make_frames_with_osd(
            z_speed=12.0,
            height=100.0,
        )
        anomaly = compute_flight_anomalies(frames)
        assert anomaly.severity == FlightSeverity.RED
        assert anomaly.max_descent_speed == 12.0

    def test_amber_smart_power_go_home(self) -> None:
        """SMART_POWER_GO_HOME action triggers AMBER severity."""
        frames = _make_frames_with_osd(
            flight_action=FlightAction.SMART_POWER_GO_HOME,
            height=30.0,
        )
        anomaly = compute_flight_anomalies(frames)
        assert anomaly.severity == FlightSeverity.AMBER
        assert FlightAction.SMART_POWER_GO_HOME in anomaly.actions

    def test_amber_negative_final_altitude(self) -> None:
        """Final altitude < -5m triggers AMBER severity."""
        frames = _make_frames_with_osd(height=-10.0)
        anomaly = compute_flight_anomalies(frames)
        assert anomaly.severity == FlightSeverity.AMBER
        assert anomaly.final_altitude == -10.0

    def test_amber_gps_degraded(self) -> None:
        """GPS degraded > 50% of flight (min 100 frames) triggers AMBER."""
        frames: list[Frame] = []
        for _ in range(100):
            frame = Frame()
            frame.osd.gps_level = 2
            frames.append(frame)
        anomaly = compute_flight_anomalies(frames)
        assert anomaly.severity == FlightSeverity.AMBER
        assert anomaly.gps_degraded_ratio == 1.0

    def test_amber_gps_degraded_below_min_frames(self) -> None:
        """GPS degradation with < 100 frames does not trigger AMBER."""
        frames: list[Frame] = []
        for _ in range(50):
            frame = Frame()
            frame.osd.gps_level = 2
            frames.append(frame)
        anomaly = compute_flight_anomalies(frames)
        assert anomaly.severity == FlightSeverity.GREEN

    def test_green_normal_flight(self) -> None:
        """Normal flight with no anomalies is GREEN."""
        frames = _make_frames_with_osd(
            height=50.0,
            z_speed=1.0,
            gps_level=4,
            flight_action=FlightAction.NONE,
        )
        anomaly = compute_flight_anomalies(frames)
        assert anomaly.severity == FlightSeverity.GREEN
        assert anomaly.actions == []
        assert anomaly.motor_blocked is False

    def test_startup_motor_block_not_counted(self) -> None:
        """Motor blocked at height=0 (startup) is NOT counted."""
        frames = _make_frames_with_osd(
            is_motor_blocked=True,
            height=0.0,
        )
        anomaly = compute_flight_anomalies(frames)
        assert anomaly.motor_blocked is False
        assert anomaly.severity == FlightSeverity.GREEN

    def test_empty_frames(self) -> None:
        """Empty frame list returns GREEN with no anomalies."""
        anomaly = compute_flight_anomalies([])
        assert anomaly.severity == FlightSeverity.GREEN

    def test_red_overrides_amber(self) -> None:
        """When both RED and AMBER conditions exist, severity is RED."""
        frame = Frame()
        frame.osd.flight_action = FlightAction.BATTERY_FORCE_LANDING
        frame.osd.height = -10.0  # would be AMBER alone
        anomaly = compute_flight_anomalies([frame])
        assert anomaly.severity == FlightSeverity.RED


class TestRCSignalStats:
    def test_empty_frames(self) -> None:
        stats = compute_rc_signal([])
        assert stats.uplink_min is None
        assert stats.downlink_min is None

    def test_signal_stats(self) -> None:
        frames = [Frame(), Frame(), Frame()]
        frames[0].rc.downlink_signal = 80
        frames[0].rc.uplink_signal = 70
        frames[1].rc.downlink_signal = 60
        frames[1].rc.uplink_signal = 90
        frames[2].rc.downlink_signal = 100
        frames[2].rc.uplink_signal = 50
        stats = compute_rc_signal(frames)
        assert stats.downlink_min == 60
        assert stats.downlink_avg == 80.0
        assert stats.uplink_min == 50
        assert stats.uplink_avg == 70.0

    def test_partial_signal(self) -> None:
        frames = [Frame(), Frame()]
        frames[0].rc.downlink_signal = 75
        # No uplink at all
        stats = compute_rc_signal(frames)
        assert stats.downlink_min == 75
        assert stats.downlink_avg == 75.0
        assert stats.uplink_min is None
        assert stats.uplink_avg is None
