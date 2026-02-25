"""Tests for layout parsing (prefix, details)."""

import struct
from datetime import datetime, timezone

import pytest

from pydjirecord.layout.details import Details, Platform, ProductType
from pydjirecord.layout.prefix import Prefix

# ---------------------------------------------------------------------------
# Prefix
# ---------------------------------------------------------------------------


class TestPrefix:
    def _make_prefix(self, detail_offset: int, version: int) -> bytes:
        """Build a 100-byte prefix blob."""
        buf = struct.pack("<QHB", detail_offset, 0, version)
        return buf.ljust(100, b"\x00")

    def test_parse_basic(self) -> None:
        data = self._make_prefix(detail_offset=5000, version=7)
        p = Prefix.from_bytes(data)
        assert p.version == 7
        assert p.detail_offset() == 5000

    def test_v6_records_at_old_prefix(self) -> None:
        p = Prefix.from_bytes(self._make_prefix(500, version=5))
        assert p.records_offset() == 12  # OLD_PREFIX_SIZE

    def test_v7_records_at_prefix_size(self) -> None:
        p = Prefix.from_bytes(self._make_prefix(5000, version=8))
        assert p.records_offset() == 100

    def test_v12_records_offset(self) -> None:
        p = Prefix.from_bytes(self._make_prefix(0, version=12))
        assert p.detail_offset() == 100
        assert p.records_offset() == 536  # 100 + 436

    def test_v13_records_offset_from_detail(self) -> None:
        p = Prefix.from_bytes(self._make_prefix(200, version=13))
        assert p.detail_offset() == 100
        assert p.records_offset() == 200

    def test_records_end_offset_v11(self) -> None:
        p = Prefix.from_bytes(self._make_prefix(5000, version=11))
        assert p.records_end_offset(10000) == 5000

    def test_records_end_offset_v12(self) -> None:
        p = Prefix.from_bytes(self._make_prefix(0, version=12))
        assert p.records_end_offset(10000) == 10000

    def test_recover_detail_offset(self) -> None:
        p = Prefix.from_bytes(self._make_prefix(0, version=13))
        assert p.records_offset() == 0
        p.recover_detail_offset(250)
        assert p.records_offset() == 250


# ---------------------------------------------------------------------------
# ProductType
# ---------------------------------------------------------------------------


class TestProductType:
    def test_known_value(self) -> None:
        assert ProductType(13) == ProductType.MAVIC_PRO

    def test_unknown_value(self) -> None:
        pt = ProductType(255)
        assert pt.value == 255
        assert "UNKNOWN" in pt.name

    def test_battery_cell_num(self) -> None:
        assert ProductType.MAVIC_PRO.battery_cell_num == 3
        assert ProductType.PHANTOM4.battery_cell_num == 4
        assert ProductType.MATRICE300_RTK.battery_cell_num == 12

    def test_battery_num(self) -> None:
        assert ProductType.INSPIRE2.battery_num == 2
        assert ProductType.MAVIC_PRO.battery_num == 1
        assert ProductType.MATRICE600.battery_num == 6

    def test_unknown_defaults(self) -> None:
        pt = ProductType(255)
        assert pt.battery_cell_num == 4
        assert pt.battery_num == 1


# ---------------------------------------------------------------------------
# Platform
# ---------------------------------------------------------------------------


class TestPlatform:
    def test_known(self) -> None:
        assert Platform(2) == Platform.ANDROID

    def test_unknown(self) -> None:
        p = Platform(99)
        assert p.value == 99


# ---------------------------------------------------------------------------
# Details
# ---------------------------------------------------------------------------


class TestDetails:
    @pytest.fixture()
    def sample_details_data(self) -> bytes:
        """Build a minimal v8 details block with known values."""
        buf = bytearray()
        # 4 x 20-byte strings
        buf += b"SubSt\x00" + b"\x00" * 14
        buf += b"MainStreet\x00" + b"\x00" * 9
        buf += b"CityName\x00" + b"\x00" * 11
        buf += b"AreaXY\x00" + b"\x00" * 13
        # is_favorite, is_new, needs_upload
        buf += bytes([1, 0, 1])
        # record_line_count, detail_info_checksum
        buf += struct.pack("<ii", 100, 0x1234)
        # start_time (ms since epoch) = 2021-05-22 15:51:13 UTC
        ts = int(datetime(2021, 5, 22, 15, 51, 13, tzinfo=timezone.utc).timestamp() * 1000)
        buf += struct.pack("<q", ts)
        # longitude, latitude
        buf += struct.pack("<dd", 12.345, 56.789)
        # total_distance, total_time (ms), max_height, max_h_speed, max_v_speed
        buf += struct.pack("<fifffif", 1500.0, 60000, 120.0, 15.5, 8.3, 42, 0)
        # Adjust: total_time is i32, capture_num is i32, video_time is i64
        # Redo properly:
        buf = bytearray()
        buf += b"SubSt\x00" + b"\x00" * 14
        buf += b"MainStreet\x00" + b"\x00" * 9
        buf += b"CityName\x00" + b"\x00" * 11
        buf += b"AreaXY\x00" + b"\x00" * 13
        buf += bytes([1, 0, 1])
        buf += struct.pack("<i", 100)  # record_line_count
        buf += struct.pack("<i", 0x1234)  # detail_info_checksum
        buf += struct.pack("<q", ts)  # start_time
        buf += struct.pack("<d", 12.345)  # longitude
        buf += struct.pack("<d", 56.789)  # latitude
        buf += struct.pack("<f", 1.5)  # total_distance (km in binary)
        buf += struct.pack("<i", 60000)  # total_time (ms)
        buf += struct.pack("<f", 120.0)  # max_height
        buf += struct.pack("<f", 15.5)  # max_horizontal_speed
        buf += struct.pack("<f", 8.3)  # max_vertical_speed
        buf += struct.pack("<i", 42)  # capture_num
        buf += struct.pack("<q", 300)  # video_time
        buf += struct.pack("<4i", 0, 0, 0, 0)  # moment_pic_image_buffer_len
        buf += struct.pack("<4i", 0, 0, 0, 0)  # moment_pic_shrink_image_buffer_len
        buf += struct.pack("<4d", 0.0, 0.0, 0.0, 0.0)  # moment_pic_longitude (radians)
        buf += struct.pack("<4d", 0.0, 0.0, 0.0, 0.0)  # moment_pic_latitude (radians)
        buf += struct.pack("<q", 0)  # _analysis_offset
        buf += b"\x00" * 16  # _user_api_center_id_md5

        # version > 5 sequential fields
        buf += struct.pack("<f", 450.0)  # take_off_altitude raw (450.0/10 = 45.0)
        buf += struct.pack("<B", 13)  # product_type = MAVIC_PRO
        buf += struct.pack("<q", 0)  # _activation_timestamp
        buf += b"MyDrone\x00" + b"\x00" * 24  # aircraft_name (32)
        buf += b"SN123456\x00" + b"\x00" * 7  # aircraft_sn (16)
        buf += b"CAM001\x00" + b"\x00" * 9  # camera_sn (16)
        buf += b"RC001\x00" + b"\x00" * 10  # rc_sn (16)
        buf += b"BAT001\x00" + b"\x00" * 9  # battery_buf (16)
        buf += struct.pack("<B", 2)  # app_platform = Android
        buf += bytes([1, 2, 3])  # app_version

        return bytes(buf)

    def test_parse_v8_details(self, sample_details_data: bytes) -> None:
        d = Details.from_bytes(sample_details_data, version=8)
        assert d.sub_street == "SubSt"
        assert d.street == "MainStreet"
        assert d.city == "CityName"
        assert d.area == "AreaXY"
        assert d.is_favorite is True
        assert d.is_new is False
        assert d.needs_upload is True
        assert d.record_line_count == 100
        assert d.start_time.year == 2021
        assert d.longitude == pytest.approx(12.345)
        assert d.latitude == pytest.approx(56.789)
        assert d.total_distance == pytest.approx(1500.0)
        assert d.total_time == pytest.approx(60.0)
        assert d.max_height == pytest.approx(120.0)
        assert d.capture_num == 42
        assert d.take_off_altitude == pytest.approx(45.0)
        assert d.product_type == ProductType.MAVIC_PRO
        assert d.aircraft_name == "MyDrone"
        assert d.aircraft_sn == "SN123456"
        assert d.camera_sn == "CAM001"
        assert d.rc_sn == "RC001"
        assert d.battery_sn == "BAT001"
        assert d.app_platform == Platform.ANDROID
        assert d.app_version == "1.2.3"
