"""Tests for the BinaryReader helper."""

import struct

import pytest

from pydjirecord._binary import BinaryReader


def test_read_integers() -> None:
    data = struct.pack("<BHiQq", 0xAB, 0x1234, -42, 0xDEADBEEFCAFEBABE, -999)
    r = BinaryReader(data)
    assert r.read_u8() == 0xAB
    assert r.read_u16() == 0x1234
    assert r.read_i32() == -42
    assert r.read_u64() == 0xDEADBEEFCAFEBABE
    assert r.read_i64() == -999


def test_read_floats() -> None:
    data = struct.pack("<fd", 3.14, 2.718281828)
    r = BinaryReader(data)
    assert r.read_f32() == pytest.approx(3.14, abs=1e-5)
    assert r.read_f64() == pytest.approx(2.718281828, abs=1e-9)


def test_read_string_null_terminated() -> None:
    raw = b"hello\x00\x00\x00\x00\x00"  # 10 bytes
    r = BinaryReader(raw)
    assert r.read_string(10) == "hello"


def test_read_string_full() -> None:
    raw = b"abcdefghij"  # 10 bytes, no null
    r = BinaryReader(raw)
    assert r.read_string(10) == "abcdefghij"


def test_read_bytes() -> None:
    r = BinaryReader(b"\x01\x02\x03\x04")
    assert r.read_bytes(3) == b"\x01\x02\x03"


def test_seek_and_tell() -> None:
    r = BinaryReader(b"\x00" * 20)
    assert r.tell() == 0
    r.skip(5)
    assert r.tell() == 5
    r.seek(15)
    assert r.tell() == 15


def test_read_arrays() -> None:
    data = struct.pack("<4i", 1, -2, 3, -4)
    data += struct.pack("<2d", 1.5, 2.5)
    r = BinaryReader(data)
    assert r.read_i32_array(4) == [1, -2, 3, -4]
    assert r.read_f64_array(2) == pytest.approx([1.5, 2.5])


def test_eof_raises() -> None:
    r = BinaryReader(b"\x00\x01")
    r.read_u16()
    with pytest.raises(EOFError):
        r.read_u8()
