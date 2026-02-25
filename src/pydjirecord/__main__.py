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
from .frame.anomaly import FlightSeverity
from .frame.details import FrameDetails
from .record.component_serial import ComponentSerial
from .record.firmware import Firmware
from .record.mc_params import MCParams
from .record.rc_gps import RCGPS
from .record.smart_battery_group import SmartBatteryStatic

if TYPE_CHECKING:
    from .frame import Frame
    from .keychain.api import KeychainFeaturePoint
    from .layout.details import Details
    from .record import Record


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

    # RC signal
    sig = fd.rc_signal
    if sig is not None and (sig.downlink_min is not None or sig.uplink_min is not None):
        lines.append("RC signal:")
        if sig.downlink_min is not None and sig.downlink_avg is not None:
            lines.append(f"  Downlink:   min {sig.downlink_min}%, avg {sig.downlink_avg:.0f}%")
        if sig.uplink_min is not None and sig.uplink_avg is not None:
            lines.append(f"  Uplink:     min {sig.uplink_min}%, avg {sig.uplink_avg:.0f}%")
        lines.append("")

    # App
    lines.append(f"App:          {d.app_platform.name} v{d.app_version}")

    # Anomaly
    if fd.anomaly is not None and fd.anomaly.severity != FlightSeverity.GREEN:
        reasons: list[str] = []
        for action in fd.anomaly.actions:
            reasons.append(action.name)
        if fd.anomaly.motor_blocked:
            reasons.append("MOTOR_BLOCKED")
        if fd.anomaly.max_descent_speed > 10.0:
            reasons.append("freefall")
        if fd.anomaly.final_altitude < -5.0:
            reasons.append("negative_altitude")
        if fd.anomaly.gps_degraded_ratio > 0.5:
            reasons.append("gps_degraded")
        detail = ", ".join(reasons) if reasons else ""
        label = fd.anomaly.severity.name
        lines.append(f"Anomaly:      {label} ({detail})" if detail else f"Anomaly:      {label}")

    print("\n".join(lines))


def _print_hardware(
    log: DJILog,
    records: list[Record],
    frames: list[Frame],
) -> None:
    """Print a hardware-focused report to stdout."""
    d = log.details
    fd = FrameDetails.from_details(d, frames)
    lines: list[str] = []

    # Aircraft
    lines.append("AIRCRAFT")
    lines.append(f"  Model:          {d.aircraft_name or d.product_type.name}")
    lines.append(f"  Product type:   {d.product_type.name}")
    lines.append(f"  Serial:         {d.aircraft_sn or '(unknown)'}")
    lines.append(f"  Log version:    {log.version}")
    lines.append("")

    # Camera
    lines.append("CAMERA")
    lines.append(f"  Serial:         {d.camera_sn or '(unknown)'}")
    if frames:
        sd = "inserted" if any(fr.camera.sd_card_is_inserted for fr in frames) else "not detected"
        lines.append(f"  SD card:        {sd}")
    lines.append("")

    # Remote controller
    lines.append("REMOTE CONTROLLER")
    lines.append(f"  Serial:         {d.rc_sn or '(unknown)'}")
    sig = fd.rc_signal
    if sig is not None:
        if sig.downlink_min is not None and sig.downlink_avg is not None:
            lines.append(f"  Downlink:       min {sig.downlink_min}%, avg {sig.downlink_avg:.0f}%")
        if sig.uplink_min is not None and sig.uplink_avg is not None:
            lines.append(f"  Uplink:         min {sig.uplink_min}%, avg {sig.uplink_avg:.0f}%")

    rcgps_recs = [r.data for r in records if isinstance(r.data, RCGPS)]
    if rcgps_recs:
        valid = [g for g in rcgps_recs if g.valid_data and abs(g.latitude) > 0.01]
        lines.append(f"  GPS records:    {len(rcgps_recs)} ({len(valid)} with valid fix)")
        if valid:
            sats = [g.gps_num for g in valid]
            lines.append(f"  GPS satellites: min {min(sats)}, max {max(sats)}")
            accs = [g.accuracy for g in valid if g.accuracy > 0]
            if accs:
                lines.append(
                    f"  GPS accuracy:   {min(accs):.1f} - {max(accs):.1f} m (avg {sum(accs) / len(accs):.1f} m)"
                )
            lines.append(f"  Pilot position: {valid[0].latitude:.6f}, {valid[0].longitude:.6f}")
    lines.append("")

    # Battery
    lines.append("BATTERY")
    lines.append(f"  Serial:         {d.battery_sn or '(unknown)'}")
    statics = [r.data for r in records if isinstance(r.data, SmartBatteryStatic)]
    if statics:
        s = statics[-1]
        lines.append(f"  Design cap:     {s.designed_capacity} mAh")
        lines.append(f"  Charge cycles:  {s.loop_times}")
        lines.append(f"  Full voltage:   {s.full_voltage / 1000.0:.2f} V")
        if s.battery_life > 0:
            lines.append(f"  Battery life:   {s.battery_life}%")
    if frames:
        charges = [fr.battery.charge_level for fr in frames if fr.battery.charge_level > 0]
        voltages = [fr.battery.voltage for fr in frames if fr.battery.voltage > 0]
        currents = [fr.battery.current for fr in frames if fr.battery.current != 0.0]
        temps = [fr.battery.temperature for fr in frames if fr.battery.temperature != 0.0]
        if charges:
            lines.append(f"  Charge:         {charges[0]}% -> {charges[-1]}% (used {charges[0] - charges[-1]}%)")
        if voltages:
            lines.append(f"  Voltage:        {min(voltages):.2f} - {max(voltages):.2f} V")
        if currents:
            lines.append(f"  Peak current:   {max(currents):.2f} A")
        if temps:
            lines.append(f"  Temperature:    {min(temps):.1f} - {max(temps):.1f} C")
        bat_last = frames[-1].battery
        cells = [v for v in bat_last.cell_voltages if v > 0]
        if cells:
            dev = max(cells) - min(cells)
            lines.append(f"  Cells:          {len(cells)}, deviation {dev * 1000:.0f} mV")
            lines.append(f"  Cell voltages:  {' / '.join(f'{v:.3f}' for v in cells)} V")
        if bat_last.lifetime_remaining > 0:
            lines.append(f"  Life remaining: {bat_last.lifetime_remaining}%")
        if bat_last.number_of_discharges > 0:
            lines.append(f"  Discharges:     {bat_last.number_of_discharges}")
    lines.append("")

    # Firmware
    fw_recs = [r.data for r in records if isinstance(r.data, Firmware)]
    if fw_recs:
        lines.append("FIRMWARE")
        seen: set[tuple[str, int]] = set()
        for fw in fw_recs:
            key = (fw.sender_type.name, fw.sub_sender_type)
            if key not in seen:
                seen.add(key)
                sub = f".{fw.sub_sender_type}" if fw.sub_sender_type else ""
                lines.append(f"  {fw.sender_type.name}{sub}:".ljust(18) + f"v{fw.version}")
        lines.append("")

    # Flight controller settings
    mc_recs = [r.data for r in records if isinstance(r.data, MCParams)]
    if mc_recs:
        mc = mc_recs[-1]
        lines.append("FLIGHT CONTROLLER")
        lines.append(f"  Failsafe:       {mc.fail_safe_protection.name}")
        lines.append(f"  Obstacle avd:   {'ON' if mc.avoid_obstacle_enabled else 'OFF'}")
        lines.append(f"  Visual odom:    {'ON' if mc.mvo_func_enabled else 'OFF'}")
        lines.append(f"  User avoid:     {'ON' if mc.user_avoid_enabled else 'OFF'}")
        lines.append("")

    # Component serials
    cs_recs = [r.data for r in records if isinstance(r.data, ComponentSerial)]
    if cs_recs:
        lines.append("COMPONENT SERIALS")
        seen_serials: set[str] = set()
        for cs in cs_recs:
            if cs.serial and cs.serial not in seen_serials:
                seen_serials.add(cs.serial)
                lines.append(f"  {cs.component_type.name}:".ljust(18) + cs.serial)
        lines.append("")

    # Anomaly
    if fd.anomaly is not None and fd.anomaly.severity != FlightSeverity.GREEN:
        reasons: list[str] = [a.name for a in fd.anomaly.actions]
        if fd.anomaly.motor_blocked:
            reasons.append("MOTOR_BLOCKED")
        if fd.anomaly.max_descent_speed > 10.0:
            reasons.append("freefall")
        if fd.anomaly.final_altitude < -5.0:
            reasons.append("negative_altitude")
        if fd.anomaly.gps_degraded_ratio > 0.5:
            reasons.append("gps_degraded")
        detail = ", ".join(reasons) if reasons else ""
        label = fd.anomaly.severity.name
        lines.append(f"ANOMALY: {label} ({detail})" if detail else f"ANOMALY: {label}")
        lines.append("")

    print("\n".join(lines).rstrip())


def _get_keychains(
    log: DJILog,
    api_key: str | None,
    custom_department: int | None = None,
    custom_version: int | None = None,
    *,
    cache: bool = True,
    verify: bool = True,
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
        return req.fetch(api_key, cache=cache, verify=verify)
    return log.fetch_keychains(api_key, cache=cache, verify=verify)


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
    fmt.add_argument("--hardware", action="store_true", help="hardware report (aircraft, RC, battery, firmware)")

    parser.add_argument("-o", "--output", metavar="FILE", default="-", help="output file (default: stdout)")
    parser.add_argument("--api-key", metavar="KEY", help="DJI API key for v13+ AES decryption")
    parser.add_argument("--api-custom-department", metavar="INT", type=int, help="override keychain API department")
    parser.add_argument("--api-custom-version", metavar="INT", type=int, help="override keychain API version")
    parser.add_argument("--no-cache", action="store_true", default=False, help="disable local keychain cache")
    parser.add_argument(
        "--no-verify", action="store_true", default=False, help="disable TLS certificate verification for API requests"
    )

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
    use_verify: bool = not args.no_verify
    output_path: str = args.output

    # Hardware report
    if args.hardware:
        hw_records: list[Record] = []
        hw_frames: list[Frame] = []
        try:
            if log.version < 13:
                hw_records = log.records(None)
                hw_frames = log.frames(None)
            elif api_key:
                keychains = _get_keychains(
                    log, api_key, custom_department, custom_version, cache=use_cache, verify=use_verify
                )
                hw_records = log.records(keychains)
                hw_frames = log.frames(keychains)
        except (DJILogError, httpx.HTTPError, ValueError, OSError) as exc:
            print(f"Warning: decryption failed ({exc}), showing header values only", file=sys.stderr)
        _print_hardware(log, hw_records, hw_frames)
        return

    # No format flag → human-readable info
    if not (args.json or args.raw or args.geojson or args.kml or args.csv):
        info_frames: list[Frame] | None = None
        try:
            if log.version < 13:
                info_frames = log.frames(None)
            elif api_key:
                keychains = _get_keychains(
                    log, api_key, custom_department, custom_version, cache=use_cache, verify=use_verify
                )
                info_frames = log.frames(keychains)
        except (DJILogError, httpx.HTTPError, ValueError, OSError) as exc:
            print(f"Warning: frame decryption failed ({exc}), showing header values only", file=sys.stderr)
            info_frames = None
        _print_info(log, info_frames)
        return

    # JSON / raw JSON
    if args.json or args.raw:
        if args.raw or api_key or log.version < 13:
            keychains = _get_keychains(
                log, api_key, custom_department, custom_version, cache=use_cache, verify=use_verify
            )
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
    keychains = _get_keychains(log, api_key, custom_department, custom_version, cache=use_cache, verify=use_verify)
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
