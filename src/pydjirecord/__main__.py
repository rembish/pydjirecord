"""CLI entry point for pydjirecord (``python -m pydjirecord``)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
from dotenv import load_dotenv

from .djilog import DJILog
from .error import DJILogError
from .export.csv import export_csv
from .export.geojson import export_geojson
from .export.json import export_json
from .export.kml import export_kml
from .frame.details import FrameDetails

if TYPE_CHECKING:
    from .frame import Frame
    from .keychain.api import KeychainFeaturePoint
    from .layout.details import Details


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


def _print_info(log: DJILog, frames: list[Frame] | None = None) -> None:
    """Print a human-readable summary to stdout."""
    d = log.details
    fd = FrameDetails.from_details(d, frames)
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
    lines.append(f"Coordinates:  {fd.latitude:.6f}, {fd.longitude:.6f}")
    lines.append(f"Takeoff alt:  {d.take_off_altitude:.1f} m")
    lines.append("")

    # Flight stats
    lines.append("Flight stats:")
    lines.append(f"  Distance:   {fd.total_distance:.1f} m")
    lines.append(f"  Duration:   {_format_duration(d.total_time)}")
    lines.append(f"  Max height: {d.max_height:.1f} m")
    lines.append(f"  Max H speed: {d.max_horizontal_speed:.1f} m/s")
    lines.append(f"  Max V speed: {d.max_vertical_speed:.1f} m/s")
    if frames:
        lines.append(f"  Frames:     {len(frames)}")
    lines.append("")

    # Media
    lines.append(f"Photos:       {fd.photo_num}")
    lines.append(f"Video time:   {_format_duration(fd.video_time)}")
    lines.append("")

    # App
    lines.append(f"App:          {d.app_platform.name} v{d.app_version}")

    print("\n".join(lines))


def _get_keychains(
    log: DJILog,
    api_key: str | None,
    custom_department: int | None = None,
    custom_version: int | None = None,
    *,
    cache: bool = True,
) -> list[list[KeychainFeaturePoint]] | None:
    """Fetch keychains for v13+ logs, return None for older versions."""
    if log.version < 13:
        return None
    if not api_key:
        print("Error: v13+ logs require --api-key or DJI_API_KEY env var for decryption", file=sys.stderr)
        sys.exit(1)
    if custom_department is not None or custom_version is not None:
        req = log.keychains_request()
        if custom_department is not None:
            req.department = custom_department
        if custom_version is not None:
            req.version = custom_version
        return req.fetch(api_key, cache=cache)
    return log.fetch_keychains(api_key, cache=cache)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="djirecord",
        description="Parse and inspect DJI drone flight log files.",
    )
    parser.add_argument("file", metavar="FILE", type=Path, help="DJI flight log file (.txt)")

    fmt = parser.add_mutually_exclusive_group()
    fmt.add_argument("--json", action="store_true", help="output as JSON")
    fmt.add_argument("--raw", action="store_true", help="output raw records as JSON")
    fmt.add_argument("--geojson", action="store_true", help="output as GeoJSON")
    fmt.add_argument("--kml", action="store_true", help="output as KML")
    fmt.add_argument("--csv", action="store_true", help="output as CSV")

    parser.add_argument("-o", "--output", metavar="FILE", default="-", help="output file (default: stdout)")
    parser.add_argument("--api-key", metavar="KEY", help="DJI API key for v13+ AES decryption")
    parser.add_argument("--api-custom-department", metavar="INT", type=int, help="override keychain API department")
    parser.add_argument("--api-custom-version", metavar="INT", type=int, help="override keychain API version")
    parser.add_argument("--no-cache", action="store_true", default=False, help="disable local keychain cache")

    return parser


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    load_dotenv()

    parser = build_parser()
    args = parser.parse_args(argv)

    # Read and parse log file
    file_path: Path = args.file
    if not file_path.exists():
        parser.error(f"file not found: {file_path}")

    data = file_path.read_bytes()
    log = DJILog.from_bytes(data)

    api_key: str | None = args.api_key or os.environ.get("DJI_API_KEY")
    custom_department: int | None = args.api_custom_department
    custom_version: int | None = args.api_custom_version
    use_cache: bool = not args.no_cache
    output_path: str = args.output

    # No format flag → human-readable info
    if not (args.json or args.raw or args.geojson or args.kml or args.csv):
        frames: list[Frame] | None = None
        try:
            if log.version < 13:
                frames = log.frames(None)
            elif api_key:
                keychains = _get_keychains(log, api_key, custom_department, custom_version, cache=use_cache)
                frames = log.frames(keychains)
        except (DJILogError, httpx.HTTPError, ValueError, OSError) as exc:
            print(f"Warning: frame decryption failed ({exc}), showing header values only", file=sys.stderr)
            frames = None
        _print_info(log, frames)
        return

    # JSON / raw JSON
    if args.json or args.raw:
        if args.raw or api_key or log.version < 13:
            keychains = _get_keychains(log, api_key, custom_department, custom_version, cache=use_cache)
            if args.raw:
                records = log.records(keychains)
                text = export_json(log, raw_records=records)
            else:
                frames = log.frames(keychains)
                text = export_json(log, frames=frames)
        else:
            # --json without API key on v13+: details-only fallback
            text = export_json(log)
        if output_path == "-":
            print(text)
        else:
            Path(output_path).write_text(text + "\n", encoding="utf-8")
        return

    # Frame-based exports require decryption
    keychains = _get_keychains(log, api_key, custom_department, custom_version, cache=use_cache)
    frames = log.frames(keychains)

    if args.kml:
        # KML uses binary output (XML declaration with encoding)
        if output_path == "-":
            export_kml(frames, log.details, sys.stdout.buffer)
        else:
            with Path(output_path).open("wb") as fh:
                export_kml(frames, log.details, fh)
    elif args.geojson:
        if output_path == "-":
            export_geojson(frames, log.details, sys.stdout)
        else:
            with Path(output_path).open("w", encoding="utf-8") as fh:
                export_geojson(frames, log.details, fh)
    elif args.csv:
        if output_path == "-":
            export_csv(frames, log.details, sys.stdout)
        else:
            with Path(output_path).open("w", newline="", encoding="utf-8") as fh:
                export_csv(frames, log.details, fh)


if __name__ == "__main__":
    main()
