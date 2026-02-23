"""CLI entry point for pydjirecord (``python -m pydjirecord``)."""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from datetime import datetime
from enum import IntEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .djilog import DJILog

if TYPE_CHECKING:
    from .layout.details import Details


def _json_default(obj: object) -> Any:
    """JSON serializer for types not handled by the default encoder."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, IntEnum):
        return obj.name
    msg = f"Object of type {type(obj).__name__} is not JSON serializable"
    raise TypeError(msg)


def _details_to_dict(details: Details, version: int) -> dict[str, Any]:
    """Serialize version + details to a JSON-friendly dict."""
    d = dataclasses.asdict(details)
    d["start_time"] = details.start_time.isoformat()
    d["product_type"] = details.product_type.name
    d["app_platform"] = details.app_platform.name
    return {"version": version, "details": d}


def _format_location(details: Details) -> str:
    """Build a comma-separated location string from non-empty parts."""
    parts = [s for s in (details.sub_street, details.street, details.city, details.area) if s]
    return ", ".join(parts)


def _format_duration(seconds: float) -> str:
    """Format seconds as Xm Ys."""
    m, s = divmod(int(seconds), 60)
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def _print_info(log: DJILog) -> None:
    """Print a human-readable summary to stdout."""
    d = log.details
    lines: list[str] = []

    lines.append(f"Log version:  {log.version}")
    lines.append("")

    # Aircraft
    product = d.product_type.name.replace("_", " ").title()
    lines.append(f"Aircraft:     {d.aircraft_name or product}")
    lines.append(f"Product type: {d.product_type.name}")
    lines.append(f"Aircraft SN:  {d.aircraft_sn or '(unknown)'}")
    lines.append(f"Camera SN:    {d.camera_sn or '(unknown)'}")
    lines.append(f"RC SN:        {d.rc_sn or '(unknown)'}")
    lines.append(f"Battery SN:   {d.battery_sn or '(unknown)'}")
    lines.append("")

    # Time and location
    lines.append(f"Start time:   {d.start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    location = _format_location(d)
    if location:
        lines.append(f"Location:     {location}")
    lines.append(f"Coordinates:  {d.latitude:.6f}, {d.longitude:.6f}")
    lines.append(f"Takeoff alt:  {d.take_off_altitude:.1f} m")
    lines.append("")

    # Flight stats
    lines.append("Flight stats:")
    lines.append(f"  Distance:   {d.total_distance:.1f} m")
    lines.append(f"  Duration:   {_format_duration(d.total_time)}")
    lines.append(f"  Max height: {d.max_height:.1f} m")
    lines.append(f"  Max H speed: {d.max_horizontal_speed:.1f} m/s")
    lines.append(f"  Max V speed: {d.max_vertical_speed:.1f} m/s")
    lines.append("")

    # Media
    lines.append(f"Photos:       {d.capture_num}")
    lines.append(f"Video time:   {_format_duration(d.video_time)}")
    lines.append("")

    # App
    lines.append(f"App:          {d.app_platform.name} v{d.app_version}")

    print("\n".join(lines))


def _export_json(log: DJILog, output: Path | None) -> None:
    """Write JSON to *output* file or stdout."""
    data = _details_to_dict(log.details, log.version)
    text = json.dumps(data, indent=2, default=_json_default)
    if output is not None:
        output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


def _not_implemented(name: str) -> None:
    print(f"Error: --{name} export requires records/frames (not yet implemented)", file=sys.stderr)
    sys.exit(1)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="pydjirecord",
        description="Parse and inspect DJI drone flight log files.",
    )
    parser.add_argument("file", metavar="FILE", type=Path, help="DJI flight log file (.txt)")

    out = parser.add_argument_group("output")
    out.add_argument("--json", action="store_true", help="output details as JSON to stdout")
    out.add_argument("-o", "--output", metavar="FILE", type=Path, help="write JSON to FILE")

    future = parser.add_argument_group("export (requires records/frames)")
    future.add_argument("--geojson", metavar="FILE", type=Path, help="export GeoJSON track")
    future.add_argument("--kml", metavar="FILE", type=Path, help="export KML track")
    future.add_argument("--csv", metavar="FILE", type=Path, help="export CSV telemetry")
    future.add_argument("--raw", action="store_true", help="output raw records instead of frames")

    parser.add_argument("--api-key", metavar="KEY", help="DJI API key for v13+ AES decryption")

    return parser


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Read and parse log file
    file_path: Path = args.file
    if not file_path.exists():
        parser.error(f"file not found: {file_path}")

    data = file_path.read_bytes()
    log = DJILog.from_bytes(data)

    # Handle stubbed exports
    for flag in ("geojson", "kml", "csv"):
        if getattr(args, flag) is not None:
            _not_implemented(flag)
    if args.raw:
        _not_implemented("raw")

    # JSON output
    if args.json or args.output:
        _export_json(log, args.output)
        return

    # Default: human-readable info
    _print_info(log)


if __name__ == "__main__":
    main()
