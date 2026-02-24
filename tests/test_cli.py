"""Tests for the CLI entry point."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from pydjirecord.__main__ import build_parser, main

SAMPLE_LOG = Path(__file__).parent / "fixtures" / "minimal_v14.txt"


class TestInfoOutput:
    def test_default_prints_info(self, capsys: pytest.CaptureFixture[str]) -> None:
        main([str(SAMPLE_LOG)])
        out = capsys.readouterr().out
        assert "Log version:" in out
        assert "Aircraft:" in out
        assert "Flight stats:" in out

    def test_info_contains_version(self, capsys: pytest.CaptureFixture[str]) -> None:
        main([str(SAMPLE_LOG)])
        out = capsys.readouterr().out
        assert "Log version:  14" in out

    def test_info_contains_serial(self, capsys: pytest.CaptureFixture[str]) -> None:
        main([str(SAMPLE_LOG)])
        out = capsys.readouterr().out
        assert "Aircraft SN:" in out

    def test_info_contains_coordinates(self, capsys: pytest.CaptureFixture[str]) -> None:
        main([str(SAMPLE_LOG)])
        out = capsys.readouterr().out
        assert "Coordinates:" in out

    def test_info_contains_app(self, capsys: pytest.CaptureFixture[str]) -> None:
        main([str(SAMPLE_LOG)])
        out = capsys.readouterr().out
        assert "App:" in out


class TestJsonOutput:
    def test_json_to_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        main([str(SAMPLE_LOG), "--json"])
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["version"] == 14
        assert "details" in data

    def test_json_has_details_fields(self, capsys: pytest.CaptureFixture[str]) -> None:
        main([str(SAMPLE_LOG), "--json"])
        out = capsys.readouterr().out
        details = json.loads(out)["details"]
        assert "aircraft_sn" in details
        assert "product_type" in details
        assert "start_time" in details
        assert "latitude" in details
        assert "longitude" in details

    def test_json_enums_are_strings(self, capsys: pytest.CaptureFixture[str]) -> None:
        main([str(SAMPLE_LOG), "--json"])
        out = capsys.readouterr().out
        details = json.loads(out)["details"]
        assert isinstance(details["product_type"], str)
        assert isinstance(details["app_platform"], str)

    def test_json_to_file(self, tmp_path: Path) -> None:
        out_file = tmp_path / "out.json"
        main([str(SAMPLE_LOG), "--json", "-o", str(out_file)])
        data = json.loads(out_file.read_text())
        assert data["version"] == 14
        assert "details" in data

    def test_json_start_time_is_iso(self, capsys: pytest.CaptureFixture[str]) -> None:
        main([str(SAMPLE_LOG), "--json"])
        out = capsys.readouterr().out
        details = json.loads(out)["details"]
        # Should be a valid ISO 8601 string
        assert "2021" in details["start_time"]
        assert "T" in details["start_time"]


class TestExportsRequireApiKey:
    """v14 logs require API key for frame-based exports."""

    @pytest.mark.parametrize("flag", ["--geojson", "--kml", "--csv"])
    def test_exports_exit_without_api_key(self, flag: str) -> None:
        with pytest.raises(SystemExit, match="1"):
            main([str(SAMPLE_LOG), flag])


class TestApiOverrideArgs:
    """--api-custom-department and --api-custom-version are accepted by the parser."""

    def test_custom_department_parsed(self) -> None:
        args = build_parser().parse_args([str(SAMPLE_LOG), "--api-custom-department", "2"])
        assert args.api_custom_department == 2

    def test_custom_version_parsed(self) -> None:
        args = build_parser().parse_args([str(SAMPLE_LOG), "--api-custom-version", "3"])
        assert args.api_custom_version == 3

    def test_both_overrides_parsed(self) -> None:
        args = build_parser().parse_args([str(SAMPLE_LOG), "--api-custom-department", "2", "--api-custom-version", "3"])
        assert args.api_custom_department == 2
        assert args.api_custom_version == 3

    def test_overrides_without_api_key_still_require_key(self) -> None:
        """Overrides alone don't bypass the API key requirement."""
        with pytest.raises(SystemExit, match="1"):
            main([str(SAMPLE_LOG), "--geojson", "--api-custom-department", "2"])


class TestMutuallyExclusiveFormats:
    """Only one format flag can be used at a time."""

    @pytest.mark.parametrize(
        "flags",
        [
            ["--json", "--kml"],
            ["--json", "--geojson"],
            ["--json", "--csv"],
            ["--raw", "--kml"],
            ["--geojson", "--kml"],
        ],
    )
    def test_combined_flags_error(self, flags: list[str]) -> None:
        with pytest.raises(SystemExit):
            main([str(SAMPLE_LOG), *flags])


class TestErrorHandling:
    def test_missing_file(self) -> None:
        with pytest.raises(SystemExit):
            main(["/nonexistent/file.txt"])

    def test_no_args(self) -> None:
        with pytest.raises(SystemExit):
            main([])


class TestModuleExecution:
    def test_python_m_invocation(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "pydjirecord", str(SAMPLE_LOG)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "Log version:" in result.stdout
