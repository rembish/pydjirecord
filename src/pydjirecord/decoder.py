"""XOR and AES decryption for DJI log records."""

from __future__ import annotations

from .keychain import FeaturePoint, Keychain, feature_point_for_record
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


def aes_decode(data: bytes, iv: bytes, key: bytes) -> tuple[bytes, bytes]:
    """AES-256-CBC decrypt *data*, returning (plaintext, next_iv).

    The next_iv is the last 16 bytes of the ciphertext (before decryption),
    used for IV chaining between records of the same feature point.
    """
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad

    # Next IV = last AES block of ciphertext
    block_size = AES.block_size  # 16
    next_iv = data[-block_size:] if len(data) >= block_size else iv

    cipher = AES.new(key, AES.MODE_CBC, iv)
    try:
        plaintext = unpad(cipher.decrypt(data), block_size)
    except ValueError:
        # Padding error — return decrypted without unpad
        plaintext = cipher.decrypt(data)

    return plaintext, next_iv


def record_decode(
    data: bytes,
    record_type: int,
    version: int,
    keychain: Keychain | None,
) -> bytes:
    """Decode record data: XOR for v7-12, XOR+AES for v13+.

    Returns decoded bytes ready for struct parsing.
    """
    if version <= 6:
        return data

    # XOR decode (v7+)
    decoded = xor_decode(data, record_type)

    if version < 13 or keychain is None:
        return decoded

    # AES decode (v13+)
    fp = feature_point_for_record(record_type, version)
    if fp == FeaturePoint.PLAINTEXT:
        return decoded

    pair = keychain.get(fp.value)
    if pair is None:
        return decoded

    iv, key = pair

    # Rust: AesDecoder reads (size - 2) bytes from XorDecoder.
    # xor_decode already consumed the first byte, so we drop the last byte
    # to match the Rust "size - 2" (firstChar + lastChar excluded).
    aes_content = decoded[:-1] if len(decoded) > 0 else decoded
    if len(aes_content) < 16 or len(aes_content) % 16 != 0:
        return decoded

    plaintext, next_iv = aes_decode(aes_content, iv, key)
    keychain.update_iv(fp.value, next_iv)
    return plaintext
