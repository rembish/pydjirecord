"""Frame details — simplified Details for export."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .. import frame as _frame_mod
    from ..layout.details import Details, Platform


@dataclass
class FrameDetails:
    """Simplified details for frame-mode exports.

    ``video_time``
        When constructed via :meth:`from_details` with *frames*, this is the
        accurate total recording duration computed from Camera ``record_time``
        segments.  Without frames it falls back to the raw header value.
    """

    total_time: float = 0.0
    total_distance: float = 0.0
    max_height: float = 0.0
    max_horizontal_speed: float = 0.0
    max_vertical_speed: float = 0.0
    photo_num: int = 0
    video_time: float = 0.0
    aircraft_name: str = ""
    aircraft_sn: str = ""
    camera_sn: str = ""
    rc_sn: str = ""
    app_platform: Platform | None = None
    app_version: str = ""

    @classmethod
    def from_details(
        cls,
        d: Details,
        frames: list[_frame_mod.Frame] | None = None,
    ) -> FrameDetails:
        video_time: float = float(d.video_time)
        if frames is not None:
            from .builder import compute_video_time

            video_time = compute_video_time(frames)

        return cls(
            total_time=d.total_time,
            total_distance=d.total_distance,
            max_height=d.max_height,
            max_horizontal_speed=d.max_horizontal_speed,
            max_vertical_speed=d.max_vertical_speed,
            photo_num=d.capture_num,
            video_time=video_time,
            aircraft_name=d.aircraft_name,
            aircraft_sn=d.aircraft_sn,
            camera_sn=d.camera_sn,
            rc_sn=d.rc_sn,
            app_platform=d.app_platform,
            app_version=d.app_version,
        )
