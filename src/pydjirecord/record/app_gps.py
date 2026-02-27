"""App GPS record."""

from __future__ import annotations

from dataclasses import dataclass

from .._binary import BinaryReader


@dataclass
class AppGPS:
    """App GPS record with latitude/longitude."""

    latitude: float
    longitude: float

    @classmethod
    def from_bytes(cls, data: bytes, version: int = 0) -> AppGPS:
        """Parse app GPS record from binary data."""
        r = BinaryReader(data)
        longitude = r.read_f64()
        latitude = r.read_f64()
        return cls(latitude=latitude, longitude=longitude)
