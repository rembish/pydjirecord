"""GeoJSON export."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from enum import IntEnum
from typing import TYPE_CHECKING, Any, TextIO

if TYPE_CHECKING:
    from ..frame import Frame
    from ..layout.details import Details


def _json_default(obj: object) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, IntEnum):
        return obj.name
    msg = f"Object of type {type(obj).__name__} is not JSON serializable"
    raise TypeError(msg)


def export_geojson(frames: list[Frame], details: Details, output: TextIO = sys.stdout) -> None:
    """Export frames as a GeoJSON Feature with LineString geometry."""
    coordinates: list[list[float]] = []
    for f in frames:
        if f.osd.latitude != 0.0 or f.osd.longitude != 0.0:
            coordinates.append([f.osd.longitude, f.osd.latitude, f.osd.altitude])

    properties: dict[str, Any] = {
        "subStreet": details.sub_street,
        "street": details.street,
        "city": details.city,
        "area": details.area,
        "isFavorite": int(details.is_favorite),
        "isNew": int(details.is_new),
        "needsUpload": int(details.needs_upload),
        "recordLineCount": details.record_line_count,
        "detailInfoChecksum": details.detail_info_checksum,
        "startTime": details.start_time.isoformat(),
        "totalDistance": details.total_distance,
        "totalTime": details.total_time,
        "maxHeight": details.max_height,
        "maxHorizontalSpeed": details.max_horizontal_speed,
        "maxVerticalSpeed": details.max_vertical_speed,
        "captureNum": details.capture_num,
        "videoTime": details.video_time,
        "momentPicLongitude": details.moment_pic_longitude,
        "momentPicLatitude": details.moment_pic_latitude,
        "takeOffAltitude": details.take_off_altitude,
        "productType": details.product_type.name,
        "aircraftName": details.aircraft_name,
        "aircraftSN": details.aircraft_sn,
        "cameraSN": details.camera_sn,
    }

    feature: dict[str, Any] = {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": coordinates,
        },
        "properties": properties,
    }

    json.dump(feature, output, indent=2, default=_json_default)
    output.write("\n")
