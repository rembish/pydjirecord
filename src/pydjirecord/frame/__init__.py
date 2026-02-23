"""Normalized frame data representation."""

from __future__ import annotations

from dataclasses import dataclass, field

from .app import FrameApp
from .battery import FrameBattery
from .camera import FrameCamera
from .custom import FrameCustom
from .details import FrameDetails
from .gimbal import FrameGimbal
from .home import FrameHome
from .osd import FrameOSD
from .rc import FrameRC
from .recover import FrameRecover

__all__ = [
    "Frame",
    "FrameApp",
    "FrameBattery",
    "FrameCamera",
    "FrameCustom",
    "FrameDetails",
    "FrameGimbal",
    "FrameHome",
    "FrameOSD",
    "FrameRC",
    "FrameRecover",
]


@dataclass
class Frame:
    """A normalized frame combining all record types for one flight moment."""

    custom: FrameCustom = field(default_factory=FrameCustom)
    osd: FrameOSD = field(default_factory=FrameOSD)
    gimbal: FrameGimbal = field(default_factory=FrameGimbal)
    camera: FrameCamera = field(default_factory=FrameCamera)
    rc: FrameRC = field(default_factory=FrameRC)
    battery: FrameBattery = field(default_factory=FrameBattery)
    home: FrameHome = field(default_factory=FrameHome)
    recover: FrameRecover = field(default_factory=FrameRecover)
    app: FrameApp = field(default_factory=FrameApp)
