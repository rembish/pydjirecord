"""Recover record — aircraft metadata."""

from __future__ import annotations

from dataclasses import dataclass

from .._binary import BinaryReader
from ..layout.details import Platform, ProductType, _parse_battery_sn


@dataclass
class Recover:
    """Recover record with aircraft identification data."""

    product_type: ProductType
    app_platform: Platform
    app_version: str
    aircraft_sn: str
    aircraft_name: str
    camera_sn: str
    rc_sn: str
    battery_sn: str

    @classmethod
    def from_bytes(cls, data: bytes, version: int) -> Recover:
        """Parse recover record from binary data."""
        r = BinaryReader(data)
        product_type = ProductType(r.read_u8())
        app_platform = Platform(r.read_u8())
        ver_bytes = r.read_bytes(3)
        app_version = f"{ver_bytes[0]}.{ver_bytes[1]}.{ver_bytes[2]}"
        sn_len = 10 if version <= 7 else 16
        aircraft_sn = r.read_string(sn_len)
        aircraft_name = r.read_string(32)
        _timestamp = r.read_i64()
        camera_sn = r.read_string(sn_len)
        rc_sn = r.read_string(sn_len)
        battery_buf = r.read_bytes(sn_len)
        battery_sn = _parse_battery_sn(product_type, battery_buf)
        return cls(
            product_type=product_type,
            app_platform=app_platform,
            app_version=app_version,
            aircraft_sn=aircraft_sn,
            aircraft_name=aircraft_name,
            camera_sn=camera_sn,
            rc_sn=rc_sn,
            battery_sn=battery_sn,
        )
