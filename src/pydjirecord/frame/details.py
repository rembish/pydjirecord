"""Frame details — simplified Details for export."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .. import frame as _frame_mod
    from ..layout.details import Details, Platform
    from .anomaly import FlightAnomaly
    from .builder import RCSignalStats


@dataclass
class FrameDetails:
    """Simplified details for frame-mode exports.

    ``latitude`` / ``longitude``
        When constructed via :meth:`from_details` with *frames* and the header
        coordinates are ``(0, 0)``, these are computed from the first valid
        OSD GPS fix (``gps_level >= 3``).  The DJI app fails to populate the
        header coordinates in roughly 20 % of flights.

    ``total_distance``
        When constructed via :meth:`from_details` with *frames*, this is the
        accurate GPS track length from the last frame's
        ``osd.cumulative_distance``.  Without frames it falls back to the
        raw header value (which can carry stale values from prior flights).

    ``photo_num``
        When constructed via :meth:`from_details` with *frames*, this is the
        accurate photo count computed from Camera ``remain_photo_num`` delta.
        Without frames it falls back to the raw header value (always 0 for
        DJI Fly app logs).

    ``video_time``
        When constructed via :meth:`from_details` with *frames*, this is the
        accurate total recording duration computed from Camera ``record_time``
        segments.  Without frames it falls back to the raw header value.
    """

    latitude: float = 0.0
    longitude: float = 0.0
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
    anomaly: FlightAnomaly | None = None
    rc_signal: RCSignalStats | None = None

    @classmethod
    def from_details(
        cls,
        d: Details,
        frames: list[_frame_mod.Frame] | None = None,
    ) -> FrameDetails:
        latitude = d.latitude
        longitude = d.longitude
        total_distance = d.total_distance
        photo_num = d.capture_num
        video_time: float = float(d.video_time)
        anomaly: FlightAnomaly | None = None
        rc_signal: RCSignalStats | None = None
        if frames is not None:
            from .builder import (
                compute_coordinates,
                compute_flight_anomalies,
                compute_photo_num,
                compute_rc_signal,
                compute_video_time,
            )

            photo_num = compute_photo_num(frames)
            video_time = compute_video_time(frames)
            anomaly = compute_flight_anomalies(frames)
            rc_signal = compute_rc_signal(frames)
            if latitude == 0.0 and longitude == 0.0:
                latitude, longitude = compute_coordinates(frames)
            if frames:
                total_distance = frames[-1].osd.cumulative_distance

        return cls(
            latitude=latitude,
            longitude=longitude,
            total_time=d.total_time,
            total_distance=total_distance,
            max_height=d.max_height,
            max_horizontal_speed=d.max_horizontal_speed,
            max_vertical_speed=d.max_vertical_speed,
            photo_num=photo_num,
            video_time=video_time,
            aircraft_name=d.aircraft_name,
            aircraft_sn=d.aircraft_sn,
            camera_sn=d.camera_sn,
            rc_sn=d.rc_sn,
            app_platform=d.app_platform,
            app_version=d.app_version,
            anomaly=anomaly,
            rc_signal=rc_signal,
        )
