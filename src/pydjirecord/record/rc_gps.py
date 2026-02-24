"""RCGPS record (type 11) — remote controller GPS push."""

from __future__ import annotations

from dataclasses import dataclass

from .._binary import BinaryReader


@dataclass
class RCGPSTime:
    """Timestamp embedded in the RC GPS record."""

    hour: int
    minute: int
    second: int
    year: int
    month: int
    day: int


@dataclass
class RCGPS:
    """Remote controller GPS data (dji_rc_gps_info_push, 30 bytes packed).

    latitude and longitude are in decimal degrees (int32 * 1e-7).
    velocity_x / velocity_y are raw int32 values from the struct.
    """

    time: RCGPSTime
    latitude: float  # degrees
    longitude: float  # degrees
    velocity_x: int  # raw i32
    velocity_y: int  # raw i32
    gps_num: int  # number of satellites
    accuracy: float  # metres
    valid_data: int  # validity flags

    @classmethod
    def from_bytes(cls, data: bytes) -> RCGPS:
        r = BinaryReader(data)
        hour = r.read_u8()
        minute = r.read_u8()
        second = r.read_u8()
        year = r.read_u16()
        month = r.read_u8()
        day = r.read_u8()
        time = RCGPSTime(
            hour=hour,
            minute=minute,
            second=second,
            year=year,
            month=month,
            day=day,
        )
        latitude = r.read_i32() * 1e-7
        longitude = r.read_i32() * 1e-7
        velocity_x = r.read_i32()
        velocity_y = r.read_i32()
        gps_num = r.read_u8()
        accuracy = r.read_f32()
        valid_data = r.read_u16()
        return cls(
            time=time,
            latitude=latitude,
            longitude=longitude,
            velocity_x=velocity_x,
            velocity_y=velocity_y,
            gps_num=gps_num,
            accuracy=accuracy,
            valid_data=valid_data,
        )
