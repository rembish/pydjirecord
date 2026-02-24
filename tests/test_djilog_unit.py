"""Unit tests for DJILog core orchestration (djilog.py).

These tests use crafted binary data so they run without any real flight-log
files and without network access (the fetch_keychains network call is
monkeypatched where needed).
"""

from __future__ import annotations

import struct

import pytest

from pydjirecord import DJILog
from pydjirecord.error import KeychainRequiredError, MissingAuxiliaryDataError
from pydjirecord.utils import crc64

# ---------------------------------------------------------------------------
# Binary construction helpers
# ---------------------------------------------------------------------------

_XOR_MAGIC = 0x123456789ABCDEF0
_MASK64 = 0xFFFFFFFFFFFFFFFF


def _xor_encode(plaintext: bytes, record_type: int = 0, first_byte: int = 0x41) -> bytes:
    """Self-inverse XOR encode — mirrors xor_decode in decoder.py."""
    seed = (first_byte + record_type) & 0xFF
    key_input = ((_XOR_MAGIC * first_byte) & _MASK64).to_bytes(8, "little")
    key = crc64(seed, key_input).to_bytes(8, "little")
    encrypted = bytes(b ^ key[i % 8] for i, b in enumerate(plaintext))
    return bytes([first_byte]) + encrypted


def _make_prefix(version: int, detail_offset: int = 0) -> bytes:
    """100-byte prefix blob."""
    return struct.pack("<QHB", detail_offset, 0, version) + b"\x00" * 89


def _make_aux_info(details: bytes | None = None) -> bytes:
    """AuxiliaryInfo block (magic=0) wrapping *details* (380 zero bytes by default)."""
    if details is None:
        details = b"\x00" * 380
    info_payload = bytes([1]) + struct.pack("<H", len(details)) + details + struct.pack("<H", 0)
    xor_info = _xor_encode(info_payload, record_type=0)
    return bytes([0]) + struct.pack("<H", len(xor_info)) + xor_info


def _make_aux_ver(version: int = 2, department: int = 3) -> bytes:
    """AuxiliaryVersion block (magic=1)."""
    return bytes([1]) + struct.pack("<H", 3) + struct.pack("<H", version) + bytes([department])


def _make_v7_log(records_bytes: bytes = b"") -> bytes:
    """Minimal v7 DJI log.

    Layout:
      Prefix (100 bytes): version=7, detail_offset = 100 + len(records) + 400
      Records area: *records_bytes*
      Details section: 400 zero bytes
    """
    detail_offset = 100 + len(records_bytes)
    prefix = _make_prefix(version=7, detail_offset=detail_offset)
    return prefix + records_bytes + b"\x00" * 400


def _make_v14_log(records_bytes: bytes = b"", department: int = 3) -> bytes:
    """Minimal v14 DJI log.

    Layout:
      Prefix (100 bytes): version=14, _detail_offset = 100 + 400 = 500
      Detail section (400 bytes): AuxInfo + AuxVer + padding
      Records area: *records_bytes*
    """
    aux_info = _make_aux_info()
    aux_ver = _make_aux_ver(department=department)
    detail_section = aux_info + aux_ver + b"\x00" * (400 - len(aux_info) - len(aux_ver))
    records_start = 100 + len(detail_section)
    prefix = _make_prefix(version=14, detail_offset=records_start)
    return prefix + detail_section + records_bytes


def _make_v7_record(magic: int) -> bytes:
    """Minimal XOR-compatible record with a valid 0xFF end marker.

    Format: [magic][length=1 LE 2B][0x00 seed byte][0xFF]

    After xor_decode the payload shrinks to zero bytes, which is safe for all
    record types (parse_record catches decoding errors and returns raw bytes).
    """
    return bytes([magic, 1, 0, 0x00, 0xFF])


# ---------------------------------------------------------------------------
# from_bytes
# ---------------------------------------------------------------------------


class TestFromBytes:
    def test_v7_takes_pre_v13_branch(self) -> None:
        """from_bytes follows the version < 13 path for v7 logs."""
        log = DJILog.from_bytes(_make_v7_log())
        assert log.version == 7
        assert log.auxiliary_version is None
        assert log.details is not None

    def test_v14_parses_aux_blocks(self, sample_log_bytes: bytes) -> None:
        """from_bytes parses AuxInfo + AuxVer for v14 logs."""
        log = DJILog.from_bytes(sample_log_bytes)
        assert log.version == 14
        # Details decoded from AuxiliaryInfo block
        assert log.details.aircraft_name == "Mini 2"

    def test_v14_wrong_first_aux_block_raises(self) -> None:
        """AuxiliaryVersion as first block raises MissingAuxiliaryDataError."""
        aux_ver = _make_aux_ver()
        detail_section = aux_ver + b"\x00" * (400 - len(aux_ver))
        records_start = 100 + len(detail_section)
        data = _make_prefix(version=14, detail_offset=records_start) + detail_section
        with pytest.raises(MissingAuxiliaryDataError):
            DJILog.from_bytes(data)

    def test_v14_zero_records_offset_is_recovered(self) -> None:
        """_detail_offset=0 triggers recover_detail_offset so records_offset > 0."""
        aux_info = _make_aux_info()
        aux_ver = _make_aux_ver()
        detail_section = aux_info + aux_ver + b"\x00" * (400 - len(aux_info) - len(aux_ver))
        # _detail_offset=0 → records_offset() == 0 → recovery path in from_bytes
        data = _make_prefix(version=14, detail_offset=0) + detail_section
        log = DJILog.from_bytes(data)
        assert log.version == 14
        assert log.prefix.records_offset() > 0


# ---------------------------------------------------------------------------
# records()
# ---------------------------------------------------------------------------


class TestRecords:
    def test_v13_without_keychains_raises(self, sample_log_bytes: bytes) -> None:
        log = DJILog.from_bytes(sample_log_bytes)
        with pytest.raises(KeychainRequiredError):
            log.records()

    def test_v14_with_empty_keychains_list_returns_empty(self, sample_log_bytes: bytes) -> None:
        """records([[]]): keychains list is non-None so no error; no records in stream."""
        log = DJILog.from_bytes(sample_log_bytes)
        assert log.records([[]]) == []

    def test_v7_no_keychains_needed(self) -> None:
        log = DJILog.from_bytes(_make_v7_log())
        assert log.records() == []

    def test_end_byte_mismatch_stops_loop(self) -> None:
        """A record with end_byte != 0xFF halts parsing before appending it."""
        # end_byte=0x00 instead of 0xFF
        bad_record = bytes([9, 1, 0, 0x00, 0x00])
        log = DJILog.from_bytes(_make_v7_log(records_bytes=bad_record))
        assert log.records() == []

    def test_truncated_records_area_stops_via_index_error(self) -> None:
        """records() stops cleanly when the records area extends past end of file."""
        # detail_offset=9999 >> file_size → records_end = 9999;
        # self.inner[100] raises IndexError → except: break → returns []
        data = _make_prefix(version=7, detail_offset=9999)  # 100 bytes total
        log = DJILog.from_bytes(data)
        assert log.records() == []

    def test_magic_50_causes_keychain_switch(self) -> None:
        """KeyStorageRecover (magic=50) in the stream triggers a keychain swap."""
        record = _make_v7_record(magic=50)
        log = DJILog.from_bytes(_make_v7_log(records_bytes=record))
        result = log.records()
        assert len(result) == 1
        assert result[0].record_type == 50

    def test_valid_record_appended(self) -> None:
        """A well-formed record appears in the returned list."""
        record = _make_v7_record(magic=9)  # AppTip
        log = DJILog.from_bytes(_make_v7_log(records_bytes=record))
        result = log.records()
        assert len(result) == 1
        assert result[0].record_type == 9

    def test_multiple_keychains_dequeued_in_order(self) -> None:
        """records() accepts and correctly dequeues multiple keychain groups."""
        log = DJILog.from_bytes(_make_v14_log())
        # Pass two empty inner groups; loop runs zero times → empty result
        assert log.records([[], []]) == []


# ---------------------------------------------------------------------------
# keychains_request()
# ---------------------------------------------------------------------------


class TestKeychainsRequest:
    def test_v7_returns_empty_request(self) -> None:
        """keychains_request() returns empty for version < 13."""
        log = DJILog.from_bytes(_make_v7_log())
        req = log.keychains_request()
        assert req.keychains == []

    def test_v14_extracts_version_and_department(self) -> None:
        log = DJILog.from_bytes(_make_v14_log())
        req = log.keychains_request()
        assert req.version == 2
        assert req.department == 3  # DJI_FLY

    def test_v14_unknown_department_maps_to_dji_fly(self) -> None:
        """Unknown department values in the AuxVer block fall back to DJI_FLY."""
        from pydjirecord.layout.auxiliary import Department

        log = DJILog.from_bytes(_make_v14_log(department=99))
        req = log.keychains_request()
        assert req.department == int(Department.DJI_FLY)

    def test_v14_magic_50_creates_new_keychain_group(self) -> None:
        """KeyStorageRecover (magic=50) in the record stream starts a new group."""
        record = _make_v7_record(magic=50)
        log = DJILog.from_bytes(_make_v14_log(records_bytes=record))
        req = log.keychains_request()
        # Group boundary: [[group before magic 50], [group after magic 50]]
        assert len(req.keychains) == 2

    def test_v14_end_byte_mismatch_stops_keychains_scan(self) -> None:
        """keychains_request stops scanning when end_byte != 0xFF."""
        bad_record = bytes([56, 1, 0, 0x00, 0x00])  # end_byte=0x00
        log = DJILog.from_bytes(_make_v14_log(records_bytes=bad_record))
        req = log.keychains_request()
        assert req.keychains == [[]]  # only the trailing empty group

    def test_v14_magic_56_unparseable_payload_skipped(self) -> None:
        """magic=56 record whose payload fails KeyStorage.from_bytes is silently skipped."""
        # 1-byte payload (XOR seed only) → xor_decode returns b"" → EOFError → pass
        record = _make_v7_record(magic=56)
        log = DJILog.from_bytes(_make_v14_log(records_bytes=record))
        req = log.keychains_request()
        assert len(req.keychains) == 1
        assert req.keychains[0] == []  # nothing appended after the parse failure

    def test_v14_magic_56_valid_payload_appended_to_group(self) -> None:
        """A successfully decoded KeyStorage record is appended to the current group."""
        # Build a real XOR-encoded KeyStorage record (feature_point=1, data=b"\xAB\xCD")
        ks_binary = struct.pack("<HH", 1, 2) + b"\xab\xcd"  # 6 bytes
        raw_payload = _xor_encode(ks_binary, record_type=56)
        record = bytes([56]) + struct.pack("<H", len(raw_payload)) + raw_payload + b"\xff"
        log = DJILog.from_bytes(_make_v14_log(records_bytes=record))
        req = log.keychains_request()
        assert len(req.keychains) == 1
        assert len(req.keychains[0]) == 1  # one EncodedKeychainFeaturePoint appended
        assert req.keychains[0][0].feature_point == 1


# ---------------------------------------------------------------------------
# fetch_keychains()
# ---------------------------------------------------------------------------


class TestFetchKeychains:
    def test_v7_returns_empty_list(self) -> None:
        log = DJILog.from_bytes(_make_v7_log())
        assert log.fetch_keychains("dummy") == []

    def test_v14_delegates_to_keychains_request_fetch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """v13+ fetch_keychains calls keychains_request().fetch() — network monkeypatched."""
        from pydjirecord.keychain.api import KeychainsRequest

        monkeypatch.setattr(KeychainsRequest, "fetch", lambda self, key: [])
        log = DJILog.from_bytes(_make_v14_log())
        assert log.fetch_keychains("dummy") == []


# ---------------------------------------------------------------------------
# frames()
# ---------------------------------------------------------------------------


class TestFrames:
    def test_v13_without_keychains_raises(self, sample_log_bytes: bytes) -> None:
        log = DJILog.from_bytes(sample_log_bytes)
        with pytest.raises(KeychainRequiredError):
            log.frames()

    def test_v14_empty_records_returns_empty_frames(self, sample_log_bytes: bytes) -> None:
        log = DJILog.from_bytes(sample_log_bytes)
        assert log.frames([[]]) == []

    def test_v7_no_records_returns_empty_frames(self) -> None:
        log = DJILog.from_bytes(_make_v7_log())
        assert log.frames() == []
