"""Tests for export modules."""

from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from pathlib import Path

from pydjirecord.djilog import DJILog
from pydjirecord.export.csv import export_csv
from pydjirecord.export.geojson import export_geojson
from pydjirecord.export.json import export_json
from pydjirecord.export.kml import export_kml
from pydjirecord.frame import Frame
from pydjirecord.frame.battery import FrameBattery
from pydjirecord.layout.details import Details, ProductType

SAMPLE_LOG = Path(__file__).parent / "fixtures" / "minimal_v14.txt"


def _make_frame(lat: float = 41.3, lon: float = 19.8, alt: float = 100.0) -> Frame:
    frame = Frame()
    frame.osd.latitude = lat
    frame.osd.longitude = lon
    frame.osd.altitude = alt
    frame.osd.fly_time = 10.0
    frame.battery = FrameBattery(cell_num=3, cell_voltages=[3.8, 3.8, 3.8])
    return frame


def _make_details() -> Details:
    return Details(
        product_type=ProductType.MAVIC_AIR2,
        aircraft_name="Test Air 2",
        aircraft_sn="TEST123",
        total_distance=1000.0,
        total_time=300.0,
        max_height=120.0,
        start_time=datetime(2021, 5, 22, 12, 0, tzinfo=timezone.utc),
    )


class TestGeoJSON:
    def test_output_structure(self, tmp_path: Path) -> None:
        frames = [_make_frame(), _make_frame(lat=41.4, lon=19.9, alt=110.0)]
        details = _make_details()
        out = tmp_path / "track.geojson"
        with out.open("w", encoding="utf-8") as fh:
            export_geojson(frames, details, fh)
        data = json.loads(out.read_text())
        assert data["type"] == "Feature"
        assert data["geometry"]["type"] == "LineString"
        coords = data["geometry"]["coordinates"]
        assert len(coords) == 2
        # GeoJSON: [lon, lat, alt]
        assert coords[0][0] == 19.8  # longitude first
        assert coords[0][1] == 41.3  # latitude second

    def test_properties(self, tmp_path: Path) -> None:
        frames = [_make_frame()]
        details = _make_details()
        buf = io.StringIO()
        export_geojson(frames, details, buf)
        data = json.loads(buf.getvalue())
        props = data["properties"]
        assert props["aircraftName"] == "Test Air 2"
        assert props["totalDistance"] == 1000.0


class TestKML:
    def test_output_structure(self, tmp_path: Path) -> None:
        frames = [_make_frame(), _make_frame(lat=41.4)]
        details = _make_details()
        out = tmp_path / "track.kml"
        with out.open("wb") as fh:
            export_kml(frames, details, fh)
        content = out.read_text()
        assert "kml" in content
        assert "LineString" in content
        assert "absolute" in content
        assert "Test Air 2" in content


class TestCSV:
    def test_output_structure(self, tmp_path: Path) -> None:
        frames = [_make_frame(), _make_frame()]
        details = _make_details()
        out = tmp_path / "telemetry.csv"
        with out.open("w", newline="", encoding="utf-8") as fh:
            export_csv(frames, details, fh)
        content = out.read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 3  # header + 2 data rows

    def test_headers(self, tmp_path: Path) -> None:
        frames = [_make_frame()]
        details = _make_details()
        buf = io.StringIO()
        export_csv(frames, details, buf)
        header = buf.getvalue().split("\n")[0]
        assert "CUSTOM.dateTime" in header
        assert "OSD.flyTime" in header
        assert "BATTERY.voltage" in header
        assert "HOME.latitude" in header

    def test_empty_frames(self) -> None:
        buf = io.StringIO()
        export_csv([], _make_details(), buf)
        assert buf.getvalue() == ""


class TestJSON:
    def test_details_only_mode(self) -> None:
        log = DJILog.from_bytes(SAMPLE_LOG.read_bytes())
        text = export_json(log)
        data = json.loads(text)
        assert data["version"] == 14
        assert "details" in data
        assert "frames" not in data
        assert "records" not in data

    def test_frames_mode(self) -> None:
        log = DJILog.from_bytes(SAMPLE_LOG.read_bytes())
        frames = [_make_frame()]
        text = export_json(log, frames=frames)
        data = json.loads(text)
        assert "frames" in data
        assert len(data["frames"]) == 1

    def test_json_to_file(self, tmp_path: Path) -> None:
        log = DJILog.from_bytes(SAMPLE_LOG.read_bytes())
        out = tmp_path / "out.json"
        export_json(log, output=out)
        data = json.loads(out.read_text())
        assert data["version"] == 14
