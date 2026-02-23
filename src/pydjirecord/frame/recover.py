"""Frame recover sub-field."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..layout.details import Platform


@dataclass
class FrameRecover:
    """Normalized aircraft metadata frame data."""

    app_platform: Platform | None = None
    app_version: str = ""
    aircraft_name: str = ""
    aircraft_sn: str = ""
    camera_sn: str = ""
    rc_sn: str = ""
    battery_sn: str = ""
