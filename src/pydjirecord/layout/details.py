"""Flight metadata (Details) parsing and related enums."""

from __future__ import annotations

import enum
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .._binary import BinaryReader

# ---------------------------------------------------------------------------
# ProductType enum
# ---------------------------------------------------------------------------


class ProductType(enum.IntEnum):
    """DJI aircraft product types."""

    NONE = 0
    INSPIRE1 = 1
    PHANTOM3_STANDARD = 2
    PHANTOM3_ADVANCED = 3
    PHANTOM3_PRO = 4
    OSMO = 5
    MATRICE100 = 6
    PHANTOM4 = 7
    LB2 = 8
    INSPIRE1_PRO = 9
    A3 = 10
    MATRICE600 = 11
    PHANTOM3_4K = 12
    MAVIC_PRO = 13
    ZENMUSE_XT = 14
    INSPIRE1_RAW = 15
    A2 = 16
    INSPIRE2 = 17
    OSMO_PRO = 18
    OSMO_RAW = 19
    OSMO_PLUS = 20
    MAVIC = 21
    OSMO_MOBILE = 22
    ORANGE_CV600 = 23
    PHANTOM4_PRO = 24
    N3FC = 25
    SPARK = 26
    MATRICE600_PRO = 27
    PHANTOM4_ADVANCED = 28
    PHANTOM3_SE = 29
    AG405 = 30
    MATRICE200 = 31
    MATRICE210 = 33
    MATRICE210_RTK = 34
    MAVIC_AIR = 38
    MAVIC2 = 42
    PHANTOM4_PRO_V2 = 44
    PHANTOM4_RTK = 46
    PHANTOM4_MULTISPECTRAL = 57
    MAVIC2_ENTERPRISE = 58
    MAVIC_MINI = 59
    MATRICE200_V2 = 60
    MATRICE210_V2 = 61
    MATRICE210_RTK_V2 = 62
    MAVIC_AIR2 = 67
    MATRICE300_RTK = 70
    FPV = 73
    MAVIC_AIR2S = 75
    MINI2 = 76
    MAVIC3 = 77
    MINI_SE = 96
    MINI3_PRO = 103
    MAVIC3_PRO = 111
    MINI2_SE = 113
    MATRICE30 = 116
    MAVIC3_ENTERPRISE = 118
    AVATA = 121
    MINI4_PRO = 126
    AVATA2 = 152
    MATRICE350_RTK = 170

    @classmethod
    def _missing_(cls, value: object) -> ProductType | None:
        if not isinstance(value, int):
            return None
        obj = int.__new__(cls, value)
        obj._name_ = f"UNKNOWN_{value}"
        obj._value_ = value
        return obj

    @property
    def battery_cell_num(self) -> int:
        """Number of cells per battery for this product type."""
        return _BATTERY_CELL_NUM.get(self.value, 4)

    @property
    def battery_num(self) -> int:
        """Number of batteries for this product type."""
        return _BATTERY_NUM.get(self.value, 1)


_BATTERY_CELL_NUM: dict[int, int] = {
    1: 6,
    2: 4,
    3: 4,
    4: 4,
    6: 6,
    7: 4,
    9: 6,
    11: 6,
    12: 4,
    13: 3,
    15: 6,
    17: 6,
    21: 3,
    24: 4,
    26: 3,
    27: 6,
    28: 4,
    29: 4,
    31: 6,
    33: 6,
    34: 6,
    38: 3,
    42: 4,
    44: 4,
    46: 4,
    57: 4,
    58: 4,
    59: 2,
    60: 6,
    61: 6,
    62: 6,
    67: 3,
    70: 12,
    73: 6,
    75: 3,
    76: 2,
    77: 4,
    96: 2,
    103: 2,
    111: 4,
    113: 2,
    116: 6,
    118: 4,
    121: 5,
    126: 2,
    152: 4,
    170: 12,
}

_BATTERY_NUM: dict[int, int] = {
    1: 2,
    6: 2,
    9: 2,
    11: 6,
    15: 2,
    17: 2,
    27: 6,
    31: 2,
    33: 2,
    34: 2,
    60: 2,
    61: 2,
    62: 2,
    70: 2,
    116: 2,
    170: 2,
}


# ---------------------------------------------------------------------------
# Platform enum
# ---------------------------------------------------------------------------


class Platform(enum.IntEnum):
    """App platform that recorded the log."""

    IOS = 1
    ANDROID = 2
    DJI_FLY = 6
    WINDOWS = 10
    MAC = 11
    LINUX = 12

    @classmethod
    def _missing_(cls, value: object) -> Platform | None:
        if not isinstance(value, int):
            return None
        obj = int.__new__(cls, value)
        obj._name_ = f"UNKNOWN_{value}"
        obj._value_ = value
        return obj


# ---------------------------------------------------------------------------
# Battery SN decoding
# ---------------------------------------------------------------------------

_BCD_PRODUCT_TYPES = frozenset(
    {
        ProductType.INSPIRE1,
        ProductType.INSPIRE1_PRO,
        ProductType.INSPIRE1_RAW,
    }
)


def _parse_battery_sn(product_type: ProductType, buf: bytes) -> str:
    """Decode battery serial from raw bytes.

    Inspire1 variants use reversed-BCD encoding; others use UTF-8.
    """
    if product_type in _BCD_PRODUCT_TYPES:
        # Low nibble of each byte → digit, reversed, leading zeros stripped
        digits = "".join(chr((b & 0xF) + ord("0")) for b in buf)
        return digits[::-1].lstrip("0")
    return buf.split(b"\x00", 1)[0].decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Details dataclass
# ---------------------------------------------------------------------------


@dataclass
class Details:
    """Flight metadata parsed from the log Details header block.

    These values are written by the DJI app at the end of a flight and are
    available without decryption.  Most are reliable; ``total_distance``,
    ``capture_num``, and ``video_time`` are notable exceptions — see their
    field notes below.

    ``total_distance``
        Converted from the binary header (stored as kilometres, exposed
        here in metres).  Reasonably accurate in most logs — verified
        against frame-computed ``cumulative_distance`` across 440+ flights
        with a consistent 1:1 ratio.  A small number of logs carry stale
        or cumulative values from previous flights.  The DJI C++ reference
        library ignores this field and recomputes from the GPS track, so
        prefer ``FrameOSD.cumulative_distance`` from the last decoded frame
        when decrypted records are available.

    ``capture_num``
        As stored in the binary header.  The DJI Fly app does not populate
        this field — it is always 0 across all tested aircraft (Mavic Air 2,
        Mini 4 Pro).  Per-frame photo events are available via
        ``FrameCamera.is_photo`` in the decrypted record stream.

    ``video_time``
        Raw value from the binary header.  This is **not** the per-flight
        recording duration — the ratio to actual in-frame recording time
        ranges from 1x to over 100x with no consistent unit.  The DJI C++
        reference library does not use it.  Per-frame recording state is
        available via ``FrameCamera.is_video`` in the decrypted record
        stream.
    """

    sub_street: str = ""
    street: str = ""
    city: str = ""
    area: str = ""
    is_favorite: bool = False
    is_new: bool = False
    needs_upload: bool = False
    record_line_count: int = 0
    detail_info_checksum: int = 0
    start_time: datetime = field(default_factory=lambda: datetime(1970, 1, 1, tzinfo=timezone.utc))
    longitude: float = 0.0
    latitude: float = 0.0
    total_distance: float = 0.0
    total_time: float = 0.0
    max_height: float = 0.0
    max_horizontal_speed: float = 0.0
    max_vertical_speed: float = 0.0
    capture_num: int = 0
    video_time: int = 0
    moment_pic_longitude: list[float] = field(default_factory=lambda: [0.0] * 4)
    moment_pic_latitude: list[float] = field(default_factory=lambda: [0.0] * 4)
    take_off_altitude: float = 0.0
    product_type: ProductType = ProductType.NONE
    aircraft_name: str = ""
    aircraft_sn: str = ""
    camera_sn: str = ""
    rc_sn: str = ""
    battery_sn: str = ""
    app_platform: Platform = field(default_factory=lambda: Platform(0))
    app_version: str = ""

    @classmethod
    def from_bytes(cls, data: bytes, version: int) -> Details:
        """Parse a Details block from *data* according to log *version*."""
        r = BinaryReader(data)

        # -- fixed sequential section (all versions) -----------------------
        sub_street = r.read_string(20)
        street = r.read_string(20)
        city = r.read_string(20)
        area = r.read_string(20)

        is_favorite = bool(r.read_u8())
        is_new = bool(r.read_u8())
        needs_upload = bool(r.read_u8())

        record_line_count = r.read_i32()
        detail_info_checksum = r.read_i32()

        ts_millis = r.read_i64()
        start_time = datetime.fromtimestamp(ts_millis / 1000, tz=timezone.utc)

        longitude = r.read_f64()
        latitude = r.read_f64()
        total_distance = r.read_f32() * 1000.0  # stored as km, expose as m
        total_time = r.read_i32() / 1000.0
        max_height = r.read_f32()
        max_horizontal_speed = r.read_f32()
        max_vertical_speed = r.read_f32()
        capture_num = r.read_i32()
        video_time = r.read_i64()

        _moment_pic_image_buf_len = r.read_i32_array(4)
        _moment_pic_shrink_buf_len = r.read_i32_array(4)

        moment_pic_longitude = [math.degrees(v) for v in r.read_f64_array(4)]
        moment_pic_latitude = [math.degrees(v) for v in r.read_f64_array(4)]

        _analysis_offset = r.read_i64()
        _user_api_center_id_md5 = r.read_bytes(16)

        # -- version-dependent section -------------------------------------
        if version <= 5:
            r.seek(352)
        take_off_altitude = r.read_f32() / 10.0

        if version <= 5:
            r.seek(277)
        product_type = ProductType(r.read_u8())

        _activation_timestamp = r.read_i64()

        name_len = 24 if version <= 5 else 32
        sn_len = 10 if version <= 5 else 16

        if version <= 5:
            r.seek(278)
        aircraft_name = r.read_string(name_len)

        if version <= 5:
            r.seek(267)
        aircraft_sn = r.read_string(sn_len)

        if version <= 5:
            r.seek(318)
        camera_sn = r.read_string(sn_len)

        rc_sn = r.read_string(sn_len)
        battery_buf = r.read_bytes(sn_len)
        battery_sn = _parse_battery_sn(product_type, battery_buf)

        app_platform = Platform(r.read_u8())
        version_bytes = r.read_bytes(3)
        app_version = f"{version_bytes[0]}.{version_bytes[1]}.{version_bytes[2]}"

        return cls(
            sub_street=sub_street,
            street=street,
            city=city,
            area=area,
            is_favorite=is_favorite,
            is_new=is_new,
            needs_upload=needs_upload,
            record_line_count=record_line_count,
            detail_info_checksum=detail_info_checksum,
            start_time=start_time,
            longitude=longitude,
            latitude=latitude,
            total_distance=total_distance,
            total_time=total_time,
            max_height=max_height,
            max_horizontal_speed=max_horizontal_speed,
            max_vertical_speed=max_vertical_speed,
            capture_num=capture_num,
            video_time=video_time,
            moment_pic_longitude=moment_pic_longitude,
            moment_pic_latitude=moment_pic_latitude,
            take_off_altitude=take_off_altitude,
            product_type=product_type,
            aircraft_name=aircraft_name,
            aircraft_sn=aircraft_sn,
            camera_sn=camera_sn,
            rc_sn=rc_sn,
            battery_sn=battery_sn,
            app_platform=app_platform,
            app_version=app_version,
        )
