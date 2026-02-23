"""Tests for the XOR decoder."""

from pydjirecord.decoder import xor_decode


def test_empty_data() -> None:
    assert xor_decode(b"", record_type=0) == b""


def test_single_byte_returns_empty() -> None:
    # First byte is key-derivation byte, no payload
    assert xor_decode(b"\x42", record_type=1) == b""


def test_decode_is_deterministic() -> None:
    data = bytes(range(20))
    a = xor_decode(data, record_type=5)
    b = xor_decode(data, record_type=5)
    assert a == b


def test_different_record_type_different_output() -> None:
    data = bytes(range(20))
    a = xor_decode(data, record_type=1)
    b = xor_decode(data, record_type=2)
    assert a != b


def test_roundtrip_with_known_key() -> None:
    """XOR is its own inverse — re-encoding decoded data with the same
    key byte prefix should recover the original payload."""
    original_payload = b"Hello, DJI!"
    key_byte = b"\x07"
    record_type = 3

    # Encode: first compute the key, then XOR the payload
    from pydjirecord.utils import crc64

    first_byte = key_byte[0]
    magic = 0x123456789ABCDEF0
    seed = (first_byte + record_type) & 0xFF
    key_input = ((magic * first_byte) & 0xFFFFFFFFFFFFFFFF).to_bytes(8, "little")
    key = crc64(seed, key_input).to_bytes(8, "little")

    encoded = bytearray(len(original_payload))
    for i, b in enumerate(original_payload):
        encoded[i] = b ^ key[i % 8]

    # The wire format is: key_byte + encoded
    wire = key_byte + bytes(encoded)
    decoded = xor_decode(wire, record_type=record_type)
    assert decoded == original_payload
