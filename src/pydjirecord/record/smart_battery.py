"""Smart battery record."""

from __future__ import annotations

from dataclasses import dataclass

from .._binary import BinaryReader


@dataclass
class SmartBattery:
    """Smart battery record."""

    useful_time: int
    go_home_time: int
    land_time: int
    go_home_battery: int
    land_battery: int
    safe_fly_radius: float
    volume_consume: float
    status: int
    go_home_status: int
    go_home_countdown: int
    voltage: float
    percent: int
    low_warning: int
    serious_low_warning: int

    @classmethod
    def from_bytes(cls, data: bytes, version: int = 0) -> SmartBattery:
        r = BinaryReader(data)
        useful_time = r.read_u16()
        go_home_time = r.read_u16()
        land_time = r.read_u16()
        go_home_battery = r.read_u16()
        land_battery = r.read_u16()
        safe_fly_radius = r.read_f32()
        volume_consume = r.read_f32()
        status = r.read_u32()
        go_home_status = r.read_u8()
        go_home_countdown = r.read_u8()
        voltage = r.read_u16() / 1000.0
        percent = r.read_u8()

        bp1 = r.read_u8()
        low_warning = bp1 & 0x7F

        bp2 = r.read_u8()
        serious_low_warning = bp2 & 0x7F

        return cls(
            useful_time=useful_time,
            go_home_time=go_home_time,
            land_time=land_time,
            go_home_battery=go_home_battery,
            land_battery=land_battery,
            safe_fly_radius=safe_fly_radius,
            volume_consume=volume_consume,
            status=status,
            go_home_status=go_home_status,
            go_home_countdown=go_home_countdown,
            voltage=voltage,
            percent=percent,
            low_warning=low_warning,
            serious_low_warning=serious_low_warning,
        )
