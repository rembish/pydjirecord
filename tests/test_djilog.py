"""Integration tests for DJILog.from_bytes with real example files.

Log discovery order:
1. ``$DJI_LOGS_DIR`` (if set and containing ``DJIFlightRecord_*.txt`` files).
2. Repository ``examples/`` directory.

To run explicitly::

    pytest -m integration tests/test_djilog.py
"""

from pathlib import Path

import pytest

from pydjirecord import DJILog, ProductType

from ._log_discovery import discover_log_files

pytestmark = pytest.mark.integration

EXAMPLE_FILES = discover_log_files()


@pytest.fixture(params=EXAMPLE_FILES, ids=[f.name for f in EXAMPLE_FILES])
def log_file(request: pytest.FixtureRequest) -> Path:
    return request.param  # type: ignore[return-value]


@pytest.fixture
def dji_log(log_file: Path) -> DJILog:
    return DJILog.from_bytes(log_file.read_bytes())


class TestDJILogFromBytes:
    def test_parses_without_error(self, dji_log: DJILog) -> None:
        assert dji_log is not None

    def test_version_is_reasonable(self, dji_log: DJILog) -> None:
        assert 1 <= dji_log.version <= 14

    def test_details_has_start_time(self, dji_log: DJILog) -> None:
        assert dji_log.details.start_time.year >= 2017

    def test_details_has_coordinates(self, dji_log: DJILog) -> None:
        d = dji_log.details
        # GPS coordinates should be in valid ranges
        assert -180 <= d.longitude <= 180
        assert -90 <= d.latitude <= 90

    def test_details_has_product_type(self, dji_log: DJILog) -> None:
        assert isinstance(dji_log.details.product_type, ProductType)

    def test_details_has_positive_distance(self, dji_log: DJILog) -> None:
        assert dji_log.details.total_distance >= 0

    def test_details_has_positive_time(self, dji_log: DJILog) -> None:
        assert dji_log.details.total_time >= 0

    def test_prefix_offsets_consistent(self, dji_log: DJILog) -> None:
        p = dji_log.prefix
        file_size = len(dji_log.inner)
        assert p.records_offset() < file_size
        assert p.records_end_offset(file_size) <= file_size
        assert p.records_offset() < p.records_end_offset(file_size)

    def test_aircraft_sn_not_empty(self, dji_log: DJILog) -> None:
        assert len(dji_log.details.aircraft_sn) > 0
