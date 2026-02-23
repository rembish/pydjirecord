"""JSON export."""

from __future__ import annotations

import dataclasses
import json
from datetime import datetime
from enum import IntEnum
from typing import TYPE_CHECKING, Any

from ..frame.details import FrameDetails

if TYPE_CHECKING:
    from pathlib import Path

    from ..djilog import DJILog
    from ..frame import Frame
    from ..record import Record


def _json_default(obj: object) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, IntEnum):
        return obj.name
    msg = f"Object of type {type(obj).__name__} is not JSON serializable"
    raise TypeError(msg)


def _to_camel(name: str) -> str:
    """Convert snake_case to camelCase."""
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def _dataclass_to_dict(obj: object) -> Any:
    """Recursively convert dataclass to dict with camelCase keys."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        result: dict[str, Any] = {}
        for f in dataclasses.fields(obj):
            val = _dataclass_to_dict(getattr(obj, f.name))
            result[_to_camel(f.name)] = val
        return result
    if isinstance(obj, list):
        return [_dataclass_to_dict(v) for v in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, IntEnum):
        return obj.name
    if isinstance(obj, bytes):
        return None
    return obj


def _details_only_dict(log: DJILog) -> dict[str, Any]:
    """Build details-only JSON matching the legacy output format (snake_case keys)."""
    d = dataclasses.asdict(log.details)
    d["start_time"] = log.details.start_time.isoformat()
    d["product_type"] = log.details.product_type.name
    d["app_platform"] = log.details.app_platform.name
    return {"version": log.version, "details": d}


def _write_output(data: dict[str, Any], output: Path | None) -> str:
    """Serialize to JSON and optionally write to file."""
    text = json.dumps(data, indent=2, default=_json_default)
    if output is not None:
        output.write_text(text + "\n", encoding="utf-8")
    return text


def export_json(
    log: DJILog,
    frames: list[Frame] | None = None,
    raw_records: list[Record] | None = None,
    output: Path | None = None,
) -> str:
    """Export as JSON. Returns the JSON string.

    If *raw_records* is provided, exports raw records mode.
    If *frames* is provided, exports normalized frames mode.
    Otherwise, exports details-only mode (legacy).
    """
    if raw_records is not None:
        records_out = []
        for rec in raw_records:
            if rec.record_type in (50, 56):
                continue
            if isinstance(rec.data, (bytes, bytearray)):
                continue
            records_out.append(
                {
                    "type": type(rec.data).__name__,
                    "content": _dataclass_to_dict(rec.data),
                }
            )
        data: dict[str, Any] = {
            "version": log.version,
            "details": _dataclass_to_dict(log.details),
            "records": records_out,
        }
    elif frames is not None:
        frame_details = FrameDetails.from_details(log.details)
        data = {
            "version": log.version,
            "details": _dataclass_to_dict(frame_details),
            "frames": [_dataclass_to_dict(f) for f in frames],
        }
    else:
        data = _details_only_dict(log)

    return _write_output(data, output)
