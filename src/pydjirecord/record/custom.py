"""Custom record — app-level timing data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .._binary import BinaryReader


@dataclass
class Custom:
    """Custom record with timestamp."""

    update_timestamp: datetime

    @classmethod
    def from_bytes(cls, data: bytes, version: int = 0) -> Custom:
        """Parse custom record from binary data."""
        r = BinaryReader(data)
        _camera_shoot = r.read_u8()
        _video_shoot = r.read_u8()
        _h_speed = r.read_f32()
        _distance = r.read_f32()
        millis = r.read_i64()
        secs = millis // 1000
        micros = (millis % 1000) * 1000
        try:
            ts = datetime.fromtimestamp(secs, tz=timezone.utc).replace(microsecond=micros)
            if ts.year < 2010 or ts.year > 2100:
                ts = datetime(1970, 1, 1, tzinfo=timezone.utc)
        except (OSError, OverflowError, ValueError):
            ts = datetime(1970, 1, 1, tzinfo=timezone.utc)
        return cls(update_timestamp=ts)
