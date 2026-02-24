"""Shared fixtures for pydjirecord tests."""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIXTURE_LOG = FIXTURES_DIR / "minimal_v14.txt"


def _make_minimal_v14_log() -> bytes:
    """Build a minimal valid v14 DJI flight log binary.

    Layout:
      Prefix (100 bytes)
      Detail section at offset 100 (400 bytes):
        AuxiliaryInfo block  (389 bytes) — XOR-encrypted Details
        AuxiliaryVersion block (6 bytes) — version=2, dept=DJI_FLY
        padding (5 bytes)
      Records area at offset 500: empty (file ends here)
    """
    from pydjirecord.utils import crc64

    xor_magic = 0x123456789ABCDEF0
    mask64 = 0xFFFFFFFFFFFFFFFF
    first_byte = 0x41  # arbitrary non-zero seed byte for XOR

    def _xor_encode(plaintext: bytes, record_type: int = 0) -> bytes:
        """Mirror of xor_decode — XOR is self-inverse."""
        seed = (first_byte + record_type) & 0xFF
        key_input = ((xor_magic * first_byte) & mask64).to_bytes(8, "little")
        key = crc64(seed, key_input).to_bytes(8, "little")
        encrypted = bytes(b ^ key[i % 8] for i, b in enumerate(plaintext))
        return bytes([first_byte]) + encrypted

    # ── Details binary (380 bytes for version > 5) ──────────────────────────
    # Field layout matches Details.from_bytes() for version >= 6.
    d = bytearray(380)
    p = 0
    p += 20  # sub_street  (null-padded)
    p += 20  # street
    p += 20  # city
    p += 20  # area
    p += 3  # is_favorite, is_new, needs_upload
    p += 4  # record_line_count (i32)
    p += 4  # detail_info_checksum (i32)

    # 2021-05-25T18:31:35Z → ms since epoch
    struct.pack_into("<q", d, p, 1621967495000)
    p += 8  # ts_millis (i64)

    struct.pack_into("<d", d, p, 19.8)
    p += 8  # longitude (f64)
    struct.pack_into("<d", d, p, 41.3)
    p += 8  # latitude (f64)
    struct.pack_into("<f", d, p, 1000.0)
    p += 4  # total_distance (f32)
    struct.pack_into("<i", d, p, 300000)
    p += 4  # total_time ms (i32)
    struct.pack_into("<f", d, p, 50.0)
    p += 4  # max_height (f32)
    struct.pack_into("<f", d, p, 10.0)
    p += 4  # max_horizontal_speed (f32)
    struct.pack_into("<f", d, p, 5.0)
    p += 4  # max_vertical_speed (f32)
    p += 4  # capture_num (i32)
    p += 8  # video_time (i64)
    p += 16  # _moment_pic_image_buf_len (4xi32)
    p += 16  # _moment_pic_shrink_buf_len (4xi32)
    p += 32  # moment_pic_longitude (4xf64, radians)
    p += 32  # moment_pic_latitude (4xf64, radians)
    p += 8  # _analysis_offset (i64)
    p += 16  # _user_api_center_id_md5 (16 bytes)

    struct.pack_into("<f", d, p, 0.0)
    p += 4  # take_off_altitude (f32)
    d[p] = 76  # product_type = MINI2 (76)
    p += 1
    p += 8  # _activation_timestamp (i64)

    name = b"Mini 2"
    d[p : p + len(name)] = name
    p += 32  # aircraft_name (32 bytes)

    sn = b"1ZNBBK"
    d[p : p + len(sn)] = sn
    p += 16  # aircraft_sn (16 bytes)
    p += 16  # camera_sn (16 bytes)
    p += 16  # rc_sn (16 bytes)
    p += 16  # battery_buf (16 bytes)

    d[p] = 6  # app_platform = DJI_FLY (6)
    p += 1
    d[p], d[p + 1], d[p + 2] = 1, 4, 2  # app_version "1.4.2"
    p += 3

    assert p == 380, f"Details binary is {p} bytes, expected 380"

    details_bytes = bytes(d)

    # ── AuxiliaryInfo inner payload ──────────────────────────────────────────
    # version_data(1B) + info_length(2B) + info_data(380B) + sig_length(2B)
    info_payload = bytes([1]) + struct.pack("<H", 380) + details_bytes + struct.pack("<H", 0)  # 385 bytes

    xor_info = _xor_encode(info_payload, record_type=0)  # 386 bytes
    # AuxiliaryInfo block: magic(0, 1B) + size(2B) + encoded(386B) = 389 bytes
    aux_info = bytes([0]) + struct.pack("<H", len(xor_info)) + xor_info

    # ── AuxiliaryVersion block ───────────────────────────────────────────────
    # magic(1, 1B) + size(3, 2B) + version(2, 2B) + department(3=DJI_FLY, 1B)
    aux_ver = bytes([1]) + struct.pack("<H", 3) + struct.pack("<H", 2) + bytes([3])

    # Detail section: 389 + 6 = 395 bytes, padded to 400
    detail_section = aux_info + aux_ver + bytes(5)

    # ── Prefix (100 bytes) ───────────────────────────────────────────────────
    # _detail_offset = records_start = 100 + 400 = 500 (records area is empty)
    records_start = 100 + len(detail_section)
    prefix = bytearray(100)
    struct.pack_into("<Q", prefix, 0, records_start)  # _detail_offset
    struct.pack_into("<B", prefix, 10, 14)  # version = 14

    return bytes(prefix) + detail_section


@pytest.fixture(scope="session", autouse=True)
def _create_fixture_log() -> None:
    """Write the minimal v14 log fixture before any test runs."""
    FIXTURES_DIR.mkdir(exist_ok=True)
    FIXTURE_LOG.write_bytes(_make_minimal_v14_log())


@pytest.fixture
def sample_log_bytes() -> bytes:
    """Return the minimal v14 log as raw bytes (fixture must already exist)."""
    return FIXTURE_LOG.read_bytes()


@pytest.fixture(autouse=True)
def _isolate_keychain_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect the keychain cache to a temp dir so tests never hit the real fs."""
    cache = tmp_path / "keychains"
    cache.mkdir()
    monkeypatch.setattr("pydjirecord.keychain.api._cache_dir", lambda: cache)
