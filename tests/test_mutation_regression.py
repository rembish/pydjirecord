"""Mutation regression tests against real v14 DJI logs.

These tests harden parser behavior for corrupted-but-plausible inputs using
in-memory byte mutations: bit flips, truncation, padding, and record-header
corruption.
"""

from __future__ import annotations

import random

import pytest

from pydjirecord import DJILog
from pydjirecord.error import MissingAuxiliaryDataError, ParseError

from ._log_discovery import discover_log_files


def _flip_byte(data: bytes, index: int) -> bytes:
    mutated = bytearray(data)
    mutated[index] ^= 0x5A
    return bytes(mutated)


@pytest.fixture(scope="module")
def real_v14_log_bytes() -> bytes:
    """Return one parseable v14 log from DJI_LOGS_DIR/examples."""
    for path in discover_log_files():
        raw = path.read_bytes()
        try:
            if DJILog.from_bytes(raw).version == 14:
                return raw
        except Exception:
            continue
    pytest.skip("No parseable v14 log found in DJI_LOGS_DIR/examples")


@pytest.fixture(scope="module")
def real_v14_log(real_v14_log_bytes: bytes) -> DJILog:
    return DJILog.from_bytes(real_v14_log_bytes)


def _assert_parse_stable(mutated: bytes) -> DJILog | None:
    """Parse mutated bytes; allow only known parse errors."""
    try:
        log = DJILog.from_bytes(mutated)
    except Exception as exc:
        assert isinstance(exc, (EOFError, OSError, OverflowError, ValueError, ParseError, MissingAuxiliaryDataError)), (
            f"Unexpected exception type for mutated input: {type(exc).__name__}: {exc}"
        )
        return None

    assert 1 <= log.version <= 14
    return log


def _assert_records_shape(log: DJILog) -> None:
    """Basic invariants for records() output shape."""
    keychains = [] if log.version >= 13 else None
    records = log.records(keychains=keychains)
    assert isinstance(records, list)
    assert len(records) <= len(log.inner)

    for rec in records:
        assert isinstance(rec.record_type, int)
        assert 0 <= rec.record_type <= 255
        assert hasattr(rec, "data")
        assert rec.data is not None


class TestMutationRegression:
    def test_tail_padding_keeps_metadata_parseable(self, real_v14_log_bytes: bytes, real_v14_log: DJILog) -> None:
        padded = real_v14_log_bytes + (b"\x00" * 256)
        log = DJILog.from_bytes(padded)
        assert log.version == real_v14_log.version
        assert log.details.aircraft_sn == real_v14_log.details.aircraft_sn
        assert log.details.start_time == real_v14_log.details.start_time

    def test_hard_truncation_raises_typed_parse_error(self, real_v14_log_bytes: bytes) -> None:
        truncated = real_v14_log_bytes[:120]
        with pytest.raises((EOFError, ValueError, ParseError, MissingAuxiliaryDataError)):
            DJILog.from_bytes(truncated)

    @pytest.mark.parametrize("cut_bytes", [32, 128, 512, 2048])
    def test_tail_truncation_is_stable(self, real_v14_log_bytes: bytes, cut_bytes: int) -> None:
        if cut_bytes >= len(real_v14_log_bytes):
            pytest.skip("cut too large for selected sample log")
        truncated = real_v14_log_bytes[:-cut_bytes]
        log = _assert_parse_stable(truncated)
        if log is not None and log.version >= 13:
            records = log.records(keychains=[])
            assert isinstance(records, list)

    def test_flip_in_detail_region_is_stable(self, real_v14_log_bytes: bytes, real_v14_log: DJILog) -> None:
        detail_flip_index = min(real_v14_log.prefix.detail_offset() + 20, len(real_v14_log_bytes) - 1)
        mutated = _flip_byte(real_v14_log_bytes, detail_flip_index)
        log = _assert_parse_stable(mutated)
        if log is not None and log.version >= 13:
            records = log.records(keychains=[])
            assert isinstance(records, list)

    def test_corrupt_first_record_magic_falls_back_to_raw_bytes(
        self,
        real_v14_log_bytes: bytes,
        real_v14_log: DJILog,
    ) -> None:
        records_start = real_v14_log.prefix.records_offset()
        if records_start >= len(real_v14_log_bytes):
            pytest.skip("Selected sample log has no records region")

        mutated = bytearray(real_v14_log_bytes)
        mutated[records_start] = 255  # force unknown magic type

        log = DJILog.from_bytes(bytes(mutated))
        records = log.records(keychains=[])
        assert records, "Expected at least one record from sample log"
        assert records[0].record_type == 255
        assert isinstance(records[0].data, (bytes, bytearray))


class TestRandomizedMutationInvariants:
    @pytest.mark.parametrize("seed", list(range(24)))
    def test_seeded_record_region_mutations_preserve_records_shape(
        self,
        real_v14_log_bytes: bytes,
        real_v14_log: DJILog,
        seed: int,
    ) -> None:
        """Randomized bit flips should never produce unknown exception types.

        For parseable mutations, records() output must retain structural
        invariants regardless of content quality.
        """
        records_start = real_v14_log.prefix.records_offset()
        if records_start >= len(real_v14_log_bytes):
            pytest.skip("Selected sample log has no records region")

        rng = random.Random(seed)
        mutated = bytearray(real_v14_log_bytes)
        start = max(records_start - 32, 0)
        for _ in range(6):
            idx = rng.randrange(start, len(mutated))
            mutated[idx] ^= rng.randrange(1, 256)

        log = _assert_parse_stable(bytes(mutated))
        if log is not None:
            _assert_records_shape(log)
