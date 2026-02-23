"""Tests for utility functions."""

from pydjirecord.utils import append_message, crc64, pad_with_zeros, sub_byte_field


class TestCrc64:
    def test_empty_data(self) -> None:
        assert crc64(0, b"") == 0

    def test_deterministic(self) -> None:
        val = crc64(42, b"\x01\x02\x03\x04")
        assert val == crc64(42, b"\x01\x02\x03\x04")

    def test_seed_matters(self) -> None:
        assert crc64(0, b"test") != crc64(1, b"test")

    def test_known_value(self) -> None:
        # CRC64-Jones (Rust crc64 crate v2.0) check value for b"123456789"
        result = crc64(0, b"123456789")
        assert result == 0xE9C6D914C4B8D9CA


class TestSubByteField:
    def test_high_bits(self) -> None:
        # 0b10101100, mask 0b11100000 -> extract top 3 bits = 0b101 = 5
        assert sub_byte_field(0b10101100, 0b11100000) == 0b101

    def test_low_bits(self) -> None:
        assert sub_byte_field(0b10101100, 0b00001111) == 0b1100

    def test_single_bit(self) -> None:
        assert sub_byte_field(0b10000000, 0b10000000) == 1
        assert sub_byte_field(0b00000000, 0b10000000) == 0

    def test_full_byte(self) -> None:
        assert sub_byte_field(0xAB, 0xFF) == 0xAB


class TestPadWithZeros:
    def test_no_padding_needed(self) -> None:
        assert pad_with_zeros(b"hello", 3) == b"hello"

    def test_exact_length(self) -> None:
        assert pad_with_zeros(b"abc", 3) == b"abc"

    def test_padding_added(self) -> None:
        assert pad_with_zeros(b"ab", 5) == b"ab\x00\x00\x00"


class TestAppendMessage:
    def test_empty_original(self) -> None:
        assert append_message("", "new") == "new"

    def test_non_empty_original(self) -> None:
        assert append_message("first", "second") == "first; second"
