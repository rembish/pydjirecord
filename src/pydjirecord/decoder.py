"""XOR and AES decryption for DJI log records."""

from __future__ import annotations

from .utils import crc64

_XOR_MAGIC: int = 0x123456789ABCDEF0
_MASK64 = 0xFFFFFFFFFFFFFFFF


def xor_decode(data: bytes, record_type: int) -> bytes:
    """XOR-decode *data* using a CRC64-derived 8-byte key.

    The first byte is consumed for key derivation and excluded from the output.
    This matches the Rust ``XorDecoder::new`` behaviour.
    """
    if len(data) < 1:
        return data

    first_byte = data[0]

    # Wrapping arithmetic matching Rust u8/u64 overflow semantics
    seed = (first_byte + record_type) & 0xFF
    key_input = ((_XOR_MAGIC * first_byte) & _MASK64).to_bytes(8, "little")
    key = crc64(seed, key_input).to_bytes(8, "little")

    result = bytearray(len(data) - 1)
    for i in range(len(result)):
        result[i] = data[i + 1] ^ key[i % 8]

    return bytes(result)
