"""Tests for record parsing with crafted binary data."""

from __future__ import annotations

import math
import struct

from pydjirecord.record import Record, parse_record
from pydjirecord.record.rc_gps import RCGPS, RCGPSTime
from pydjirecord.record.app_gps import AppGPS
from pydjirecord.record.app_tip import AppTip
from pydjirecord.record.app_warn import AppWarn
from pydjirecord.record.camera import Camera, SDCardState
from pydjirecord.record.center_battery import CenterBattery
from pydjirecord.record.component_serial import ComponentSerial, ComponentType
from pydjirecord.record.custom import Custom
from pydjirecord.record.firmware import Firmware, SenderType
from pydjirecord.record.gimbal import Gimbal, GimbalMode
from pydjirecord.record.home import (
    Home,
)
from pydjirecord.record.key_storage import KeyStorage
from pydjirecord.record.mc_params import FailSafeProtectionType, MCParams
from pydjirecord.record.ofdm import OFDM
from pydjirecord.record.osd import (
    OSD,
    DroneType,
    FlightMode,
    GroundOrSky,
    ImuInitFailReason,
)
from pydjirecord.record.rc import RC
from pydjirecord.record.rc_display_field import RCDisplayField
from pydjirecord.record.smart_battery import SmartBattery


class TestOSD:
    def _build_osd_bytes(self) -> bytes:
        """Build minimal OSD record binary data."""
        buf = bytearray()
        # longitude (f64, radians) = pi/4 => 45 degrees
        buf += struct.pack("<d", math.pi / 4)
        # latitude (f64, radians) = pi/6 => 30 degrees
        buf += struct.pack("<d", math.pi / 6)
        # altitude (i16) = 1000 => 100.0 m
        buf += struct.pack("<h", 1000)
        # speed_x, speed_y, speed_z (3 x i16) = 50, -30, 10
        buf += struct.pack("<hhh", 50, -30, 10)
        # pitch, roll, yaw (3 x i16) = 100, -50, 1800
        buf += struct.pack("<hhh", 100, -50, 1800)
        # bitpack1: flight_mode=6(GPS_ATTI) | rc_outcontrol=0
        buf += struct.pack("<B", 6)
        # app_command: 0 (unknown)
        buf += struct.pack("<B", 0)
        # bitpack2: can_ioc=1, ground_or_sky=2(Sky), motor_up=1, swave=0, go_home=0
        buf += struct.pack("<B", 0x01 | 0x04 | 0x08)  # can_ioc + sky + motor_up
        # bitpack3: vision=1, voltage_warning=0, imu_preheated=1, gps_valid=1
        buf += struct.pack("<B", 0x01 | 0x10 | 0x80)
        # bitpack4: compass_error=0, wave_error=0, gps_level=3, battery_type=2(Smart)
        buf += struct.pack("<B", (3 << 2) | (2 << 6))
        # bitpack5: all zeros
        buf += struct.pack("<B", 0)
        # gps_num
        buf += struct.pack("<B", 12)
        # flight_action: 0 (None)
        buf += struct.pack("<B", 0)
        # motor_start_failed_cause: 0 (None)
        buf += struct.pack("<B", 0)
        # bitpack6: non_gps_cause=0
        buf += struct.pack("<B", 0)
        # battery
        buf += struct.pack("<B", 80)
        # s_wave_height (u8)
        buf += struct.pack("<B", 50)
        # fly_time (u16) = 1200 => 120.0 seconds
        buf += struct.pack("<H", 1200)
        # motor_revolution, unknown(u16), version_c
        buf += struct.pack("<BHB", 0, 0, 0)
        # drone_type (v2+)
        buf += struct.pack("<B", 58)  # MAVIC_AIR2
        # imu_init_fail_reason (v3+)
        buf += struct.pack("<B", 0)
        return bytes(buf)

    def test_basic_osd_parse(self) -> None:
        data = self._build_osd_bytes()
        osd = OSD.from_bytes(data, version=14)
        assert abs(osd.longitude - 45.0) < 0.001
        assert abs(osd.latitude - 30.0) < 0.001
        assert osd.altitude == 100.0
        assert osd.speed_x == 5.0
        assert osd.fly_time == 120.0
        assert osd.gps_num == 12
        assert osd.flight_mode == FlightMode.GPS_ATTI
        assert osd.drone_type == DroneType.MAVIC_AIR2

    def test_version_1_no_drone_type(self) -> None:
        data = self._build_osd_bytes()
        osd = OSD.from_bytes(data, version=1)
        assert osd.drone_type == DroneType.NONE
        assert osd.imu_init_fail_reason == ImuInitFailReason.MONITOR_ERROR


class TestEnumMissing:
    def test_flight_mode_unknown(self) -> None:
        fm = FlightMode(200)
        assert fm.value == 200
        assert "UNKNOWN" in fm.name

    def test_drone_type_unknown(self) -> None:
        dt = DroneType(255)
        assert dt.value == 255

    def test_ground_or_sky_remapping(self) -> None:
        assert GroundOrSky(0) == GroundOrSky.GROUND
        assert GroundOrSky(1) == GroundOrSky.GROUND
        assert GroundOrSky(2) == GroundOrSky.SKY
        assert GroundOrSky(3) == GroundOrSky.SKY


class TestHome:
    def test_basic_home_parse(self) -> None:
        buf = bytearray()
        buf += struct.pack("<d", math.pi / 4)  # longitude
        buf += struct.pack("<d", math.pi / 6)  # latitude
        buf += struct.pack("<f", 500.0)  # altitude raw (500/10 = 50.0)
        # bitpack1: is_home_record=1, go_home_mode=0, dyn_home=0, near_dist=0, near_height=0, multi=0, has_go_home=0
        buf += struct.pack("<B", 0x01)
        # bitpack2: compass=0, adjust=0, beginner=0, ioc=0, ioc_mode=0
        buf += struct.pack("<B", 0)
        buf += struct.pack("<H", 120)  # go_home_height
        buf += struct.pack("<h", 0)  # ioc_course_lock_angle
        buf += struct.pack("<BBH", 0, 0, 0)  # sd_state, percent, left_time
        buf += struct.pack("<H", 5)  # current_flight_record_index
        home = Home.from_bytes(bytes(buf), version=6)
        assert abs(home.longitude - 45.0) < 0.001
        assert home.altitude == 50.0
        assert home.is_home_record is True
        assert home.go_home_height == 120


class TestGimbal:
    def test_basic_gimbal_parse(self) -> None:
        buf = bytearray()
        buf += struct.pack("<hhh", -100, 0, 1800)  # pitch, roll, yaw
        # bitpack1: mode=2(YawFollow) << 6
        buf += struct.pack("<B", 2 << 6)
        buf += struct.pack("<b", 0)  # roll_adjust
        buf += struct.pack("<h", 0)  # yaw_angle
        # bitpack2: pitch_at_limit=1
        buf += struct.pack("<B", 0x01)
        gimbal = Gimbal.from_bytes(bytes(buf), version=14)
        assert gimbal.pitch == -10.0
        assert gimbal.yaw == 180.0
        assert gimbal.mode == GimbalMode.YAW_FOLLOW
        assert gimbal.is_pitch_at_limit is True


class TestRC:
    def test_basic_rc_parse(self) -> None:
        buf = struct.pack("<HHHH", 1024, 1024, 1500, 1024)
        rc = RC.from_bytes(buf, version=14)
        assert rc.aileron == 1024
        assert rc.throttle == 1500


class TestCenterBattery:
    def test_basic_battery_parse(self) -> None:
        buf = bytearray()
        buf += struct.pack("<B", 75)  # relative_capacity
        buf += struct.pack("<H", 11400)  # voltage = 11.4V
        buf += struct.pack("<H", 3000)  # current_capacity
        buf += struct.pack("<H", 4000)  # full_capacity
        buf += struct.pack("<B", 95)  # life
        buf += struct.pack("<H", 50)  # discharges
        buf += struct.pack("<I", 0)  # error_type
        buf += struct.pack("<h", -500)  # current = -0.5A
        buf += struct.pack("<HHHHHH", 3800, 3800, 3800, 0, 0, 0)  # cell voltages
        buf += struct.pack("<H", 0)  # serial
        buf += struct.pack("<H", 0)  # product_date
        bat = CenterBattery.from_bytes(bytes(buf), version=6)
        assert bat.relative_capacity == 75
        assert abs(bat.voltage - 11.4) < 0.01
        assert abs(bat.current - (-0.5)) < 0.01
        assert abs(bat.voltage_cell1 - 3.8) < 0.01
        assert bat.temperature == 0.0  # version < 8


class TestCamera:
    def test_basic_camera_parse(self) -> None:
        # bitpack1: is_recording (bits 6-7) = 1
        bp1 = 1 << 6
        # bitpack2: has_sd_card (bit 1) = 1, sd_card_state (bits 2-5) = 0 (Normal)
        bp2 = 0x02
        buf = struct.pack("<BB", bp1, bp2)
        cam = Camera.from_bytes(buf)
        assert cam.is_recording is True
        assert cam.has_sd_card is True
        assert cam.sd_card_state == SDCardState.NORMAL


class TestCustom:
    def test_valid_timestamp(self) -> None:
        buf = bytearray()
        buf += struct.pack("<BB", 0, 0)  # camera_shoot, video_shoot
        buf += struct.pack("<ff", 0.0, 0.0)  # h_speed, distance
        # timestamp: 2021-05-22 12:00:00 UTC in milliseconds
        ts_millis = 1621684800000
        buf += struct.pack("<q", ts_millis)
        custom = Custom.from_bytes(bytes(buf))
        assert custom.update_timestamp.year == 2021


class TestOFDM:
    def test_downlink(self) -> None:
        ofdm = OFDM.from_bytes(bytes([75]))  # signal=75, is_up=False
        assert ofdm.signal_percent == 75
        assert ofdm.is_up is False

    def test_uplink(self) -> None:
        ofdm = OFDM.from_bytes(bytes([0x80 | 50]))  # signal=50, is_up=True
        assert ofdm.signal_percent == 50
        assert ofdm.is_up is True


class TestKeyStorage:
    def test_parse(self) -> None:
        buf = bytearray()
        buf += struct.pack("<H", 1)  # feature_point
        buf += struct.pack("<H", 4)  # data_length
        buf += b"\xaa\xbb\xcc\xdd"
        ks = KeyStorage.from_bytes(bytes(buf))
        assert ks.feature_point == 1
        assert ks.data == b"\xaa\xbb\xcc\xdd"


class TestAppMessages:
    def test_app_tip(self) -> None:
        tip = AppTip.from_bytes(b"Hello World\x00extra")
        assert tip.message == "Hello World"

    def test_app_warn(self) -> None:
        warn = AppWarn.from_bytes(b"Warning!\x00")
        assert warn.message == "Warning!"


class TestRCDisplayField:
    def test_parse(self) -> None:
        buf = bytearray(7)  # 7 unknown bytes
        buf += struct.pack("<HHHHH", 1024, 1024, 1500, 1024, 0)
        rc = RCDisplayField.from_bytes(bytes(buf))
        assert rc.aileron == 1024
        assert rc.throttle == 1500


class TestAppGPS:
    def test_basic_parse(self) -> None:
        buf = struct.pack("<dd", 19.82, 41.33)  # longitude, latitude
        gps = AppGPS.from_bytes(buf)
        assert abs(gps.longitude - 19.82) < 0.001
        assert abs(gps.latitude - 41.33) < 0.001

    def test_dispatch(self) -> None:
        buf = struct.pack("<dd", 19.82, 41.33)
        record = parse_record(14, buf, version=14)
        assert isinstance(record.data, AppGPS)


class TestFirmware:
    def test_basic_parse(self) -> None:
        buf = struct.pack("<BB", 3, 0) + bytes([1, 2, 3, 0])  # MC, sub=0, ver=1.2.3
        fw = Firmware.from_bytes(buf)
        assert fw.sender_type == SenderType.MC
        assert fw.sub_sender_type == 0
        assert fw.version == "1.2.3"

    def test_dispatch(self) -> None:
        buf = struct.pack("<BB", 1, 0) + bytes([4, 5, 6, 0])
        record = parse_record(15, buf, version=14)
        assert isinstance(record.data, Firmware)


class TestMCParams:
    def test_basic_parse(self) -> None:
        buf = struct.pack("<BB", 2, 0x07)  # GO_HOME, all flags set
        mc = MCParams.from_bytes(buf)
        assert mc.fail_safe_protection == FailSafeProtectionType.GO_HOME
        assert mc.mvo_func_enabled is True
        assert mc.avoid_obstacle_enabled is True
        assert mc.user_avoid_enabled is True

    def test_flags_off(self) -> None:
        buf = struct.pack("<BB", 0, 0x00)  # HOVER, no flags
        mc = MCParams.from_bytes(buf)
        assert mc.fail_safe_protection == FailSafeProtectionType.HOVER
        assert mc.mvo_func_enabled is False
        assert mc.avoid_obstacle_enabled is False
        assert mc.user_avoid_enabled is False

    def test_dispatch(self) -> None:
        buf = struct.pack("<BB", 0, 0)
        record = parse_record(19, buf, version=14)
        assert isinstance(record.data, MCParams)


class TestComponentSerial:
    def test_basic_parse(self) -> None:
        serial_bytes = b"ABC123\x00"
        buf = struct.pack("<HB", 2, len(serial_bytes)) + serial_bytes
        cs = ComponentSerial.from_bytes(buf)
        assert cs.component_type == ComponentType.AIRCRAFT
        assert cs.serial == "ABC123"

    def test_empty_serial(self) -> None:
        buf = struct.pack("<HB", 1, 1) + b"\x00"
        cs = ComponentSerial.from_bytes(buf)
        assert cs.component_type == ComponentType.CAMERA
        assert cs.serial == ""

    def test_dispatch(self) -> None:
        buf = struct.pack("<HB", 3, 2) + b"RC"
        record = parse_record(40, buf, version=14)
        assert isinstance(record.data, ComponentSerial)


class TestSmartBatteryFields:
    def _build_smart_battery_bytes(self, bp1: int = 0, bp2: int = 0) -> bytes:
        buf = bytearray()
        buf += struct.pack("<H", 100)  # useful_time
        buf += struct.pack("<H", 200)  # go_home_time
        buf += struct.pack("<H", 300)  # land_time
        buf += struct.pack("<H", 30)  # go_home_battery
        buf += struct.pack("<H", 20)  # land_battery
        buf += struct.pack("<f", 500.0)  # safe_fly_radius
        buf += struct.pack("<f", 10.0)  # volume_consume
        buf += struct.pack("<I", 0)  # status
        buf += struct.pack("<B", 0)  # go_home_status
        buf += struct.pack("<B", 10)  # go_home_countdown
        buf += struct.pack("<H", 11400)  # voltage = 11.4V
        buf += struct.pack("<B", 75)  # percent
        buf += struct.pack("<B", bp1)  # bitpack1
        buf += struct.pack("<B", bp2)  # bitpack2
        return bytes(buf)

    def test_low_warning_go_home(self) -> None:
        data = self._build_smart_battery_bytes(bp1=0x80 | 10)
        sb = SmartBattery.from_bytes(data)
        assert sb.low_warning == 10
        assert sb.low_warning_go_home == 1

    def test_serious_low_warning_landing(self) -> None:
        data = self._build_smart_battery_bytes(bp2=0x80 | 5)
        sb = SmartBattery.from_bytes(data)
        assert sb.serious_low_warning == 5
        assert sb.serious_low_warning_landing == 1

    def test_no_warning_flags(self) -> None:
        data = self._build_smart_battery_bytes(bp1=10, bp2=5)
        sb = SmartBattery.from_bytes(data)
        assert sb.low_warning_go_home == 0
        assert sb.serious_low_warning_landing == 0


class TestHomeAircraftHeadDirection:
    def test_aircraft_head_direction(self) -> None:
        buf = bytearray()
        buf += struct.pack("<d", math.pi / 4)  # longitude
        buf += struct.pack("<d", math.pi / 6)  # latitude
        buf += struct.pack("<f", 500.0)  # altitude raw
        # bitpack1: is_home_record=1, go_home_mode=0, aircraft_head_direction=1
        buf += struct.pack("<B", 0x01 | 0x04)
        buf += struct.pack("<B", 0)  # bitpack2
        buf += struct.pack("<H", 120)  # go_home_height
        buf += struct.pack("<h", 0)  # ioc_course_lock_angle
        buf += struct.pack("<BBH", 0, 0, 0)  # sd_state, percent, left_time
        buf += struct.pack("<H", 0)  # current_flight_record_index
        home = Home.from_bytes(bytes(buf), version=6)
        assert home.aircraft_head_direction == 1

    def test_aircraft_head_direction_zero(self) -> None:
        buf = bytearray()
        buf += struct.pack("<d", math.pi / 4)
        buf += struct.pack("<d", math.pi / 6)
        buf += struct.pack("<f", 500.0)
        buf += struct.pack("<B", 0x01)  # no 0x04 bit
        buf += struct.pack("<B", 0)
        buf += struct.pack("<H", 120)
        buf += struct.pack("<h", 0)
        buf += struct.pack("<BBH", 0, 0, 0)
        buf += struct.pack("<H", 0)
        home = Home.from_bytes(bytes(buf), version=6)
        assert home.aircraft_head_direction == 0


class TestRCGPS:
    @staticmethod
    def _make_rc_gps_bytes(
        hour: int = 12,
        minute: int = 30,
        second: int = 45,
        year: int = 2021,
        month: int = 5,
        day: int = 25,
        lat: int = 413000000,   # 41.3° × 1e7
        lon: int = 198000000,   # 19.8° × 1e7
        vx: int = 100,
        vy: int = -50,
        gps_num: int = 8,
        accuracy: float = 2.5,
        valid_data: int = 1,
    ) -> bytes:
        return struct.pack(
            "<BBBHBBiiiiBfH",
            hour, minute, second, year, month, day,
            lat, lon, vx, vy,
            gps_num, accuracy, valid_data,
        )

    def test_basic_parse(self) -> None:
        data = self._make_rc_gps_bytes()
        rc = RCGPS.from_bytes(data)
        assert isinstance(rc.time, RCGPSTime)
        assert rc.time.hour == 12
        assert rc.time.minute == 30
        assert rc.time.second == 45
        assert rc.time.year == 2021
        assert rc.time.month == 5
        assert rc.time.day == 25

    def test_coordinates_scaled(self) -> None:
        data = self._make_rc_gps_bytes(lat=413000000, lon=198000000)
        rc = RCGPS.from_bytes(data)
        assert abs(rc.latitude - 41.3) < 1e-6
        assert abs(rc.longitude - 19.8) < 1e-6

    def test_negative_coordinates(self) -> None:
        data = self._make_rc_gps_bytes(lat=-340000000, lon=-580000000)
        rc = RCGPS.from_bytes(data)
        assert abs(rc.latitude - (-34.0)) < 1e-6
        assert abs(rc.longitude - (-58.0)) < 1e-6

    def test_velocity_and_meta(self) -> None:
        data = self._make_rc_gps_bytes(vx=100, vy=-50, gps_num=8, accuracy=2.5, valid_data=1)
        rc = RCGPS.from_bytes(data)
        assert rc.velocity_x == 100
        assert rc.velocity_y == -50
        assert rc.gps_num == 8
        assert abs(rc.accuracy - 2.5) < 1e-4
        assert rc.valid_data == 1

    def test_dispatch(self) -> None:
        data = self._make_rc_gps_bytes()
        record = parse_record(11, data, version=14)
        assert isinstance(record.data, RCGPS)
        assert record.record_type == 11


class TestParseRecord:
    def test_osd_dispatch(self) -> None:
        buf = bytearray(80)
        record = parse_record(1, bytes(buf), version=14)
        assert isinstance(record, Record)
        assert record.record_type == 1
        assert isinstance(record.data, OSD)

    def test_unknown_magic(self) -> None:
        record = parse_record(255, b"\x00\x01\x02", version=14)
        assert record.record_type == 255
        assert isinstance(record.data, bytes)

    def test_keystorage_recover(self) -> None:
        record = parse_record(50, b"\x00", version=14)
        assert record.record_type == 50
        assert isinstance(record.data, bytes)
