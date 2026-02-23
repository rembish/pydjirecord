"""Frame RC sub-field."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FrameRC:
    """Normalized remote control frame data."""

    downlink_signal: int | None = None
    uplink_signal: int | None = None
    aileron: int = 0
    elevator: int = 0
    throttle: int = 0
    rudder: int = 0
