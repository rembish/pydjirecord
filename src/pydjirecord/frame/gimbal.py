"""Frame gimbal sub-field."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..record.gimbal import GimbalMode


@dataclass
class FrameGimbal:
    """Normalized gimbal frame data."""

    mode: GimbalMode | None = None
    pitch: float = 0.0
    roll: float = 0.0
    yaw: float = 0.0
    is_pitch_at_limit: bool = False
    is_roll_at_limit: bool = False
    is_yaw_at_limit: bool = False
    is_stuck: bool = False
