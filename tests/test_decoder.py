"""Tests for the XOR and AES decoder."""

from pydjirecord.decoder import aes_decode, record_decode, xor_decode
from pydjirecord.keychain import Keychain
from pydjirecord.keychain.api import KeychainFeaturePoint


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


class TestAesDecode:
    def test_padding_error_returns_raw_decrypt(self) -> None:
        """Padding error fallback must not re-use the consumed cipher object.

        Before the fix, aes_decode called cipher.decrypt(data) inside unpad(),
        and on ValueError called cipher.decrypt(data) again on the *same*
        stateful CBC cipher object, producing garbage.  The fix decrypts once,
        stores the result, then unpad's that buffer.
        """
        from Crypto.Cipher import AES

        key = b"\x01" * 32
        iv = b"\x02" * 16
        # Encrypt \xff * 16 so decrypting gives bytes where the last byte
        # is 0xFF (= 255), which is not a valid PKCS7 padding length for a
        # 16-byte block — triggering the fallback path.
        ciphertext = AES.new(key, AES.MODE_CBC, iv).encrypt(b"\xff" * 16)

        result, _ = aes_decode(ciphertext, iv, key)

        # Must equal the raw decryption of a fresh cipher, not garbage
        expected = AES.new(key, AES.MODE_CBC, iv).decrypt(ciphertext)
        assert result == expected

    def test_roundtrip(self) -> None:
        """Encrypt then decrypt with AES-256-CBC should recover plaintext."""
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad

        key = b"\x01" * 32
        iv = b"\x02" * 16
        plaintext = b"Hello AES world!"

        cipher = AES.new(key, AES.MODE_CBC, iv)
        ciphertext = cipher.encrypt(pad(plaintext, AES.block_size))

        result, next_iv = aes_decode(ciphertext, iv, key)
        assert result == plaintext
        assert next_iv == ciphertext[-16:]

    def test_next_iv_is_last_ciphertext_block(self) -> None:
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad

        key = b"\xaa" * 32
        iv = b"\xbb" * 16
        plaintext = b"A" * 48  # 3 blocks

        cipher = AES.new(key, AES.MODE_CBC, iv)
        ciphertext = cipher.encrypt(pad(plaintext, AES.block_size))

        _, next_iv = aes_decode(ciphertext, iv, key)
        assert next_iv == ciphertext[-16:]


class TestRecordDecode:
    def test_v6_returns_raw(self) -> None:
        data = b"\x00\x01\x02\x03"
        assert record_decode(data, record_type=1, version=6, keychain=None) == data

    def test_v10_xor_only(self) -> None:
        data = bytes(range(20))
        result = record_decode(data, record_type=1, version=10, keychain=None)
        assert result == xor_decode(data, 1)

    def test_v14_plaintext_skips_aes(self) -> None:
        """Plaintext feature point records (magic 56) skip AES even for v14."""
        import base64

        key_b64 = base64.b64encode(b"\x00" * 32).decode()
        iv_b64 = base64.b64encode(b"\x00" * 16).decode()
        fps = [KeychainFeaturePoint(feature_point=1, aes_key=key_b64, aes_iv=iv_b64)]
        kc = Keychain.from_feature_points(fps)

        data = bytes(range(20))
        # record_type=56 (KeyStorage) maps to PLAINTEXT — no AES
        result = record_decode(data, record_type=56, version=14, keychain=kc)
        assert result == xor_decode(data, 56)

    def test_v14_aes_strips_last_byte_before_decrypt(self) -> None:
        """record_decode must strip the last XOR-decoded byte before AES.

        Rust passes (size - 2) to AesDecoder: first byte consumed by XOR,
        last byte excluded from AES content.  If the last byte is NOT
        stripped, the data won't be 16-byte aligned and AES will raise.
        """
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad

        aes_key = b"\x11" * 32
        aes_iv = b"\x22" * 16

        # Build a valid AES-CBC ciphertext (must be multiple of 16)
        inner_plaintext = b"record-payload!!"  # exactly 16 bytes
        cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
        aes_ciphertext = cipher.encrypt(pad(inner_plaintext, AES.block_size))
        # aes_ciphertext is 32 bytes (16 plaintext + 16 PKCS7 padding)

        # Simulate what record_decode receives:
        # After XOR decode, the output is (aes_content || last_byte),
        # where aes_content must be 16-byte aligned.
        # So decoded = aes_ciphertext + one_trailing_byte
        xor_decoded_payload = aes_ciphertext + b"\xff"  # 33 bytes

        # Reverse-engineer the raw wire bytes: xor_decode(raw, type) == xor_decoded_payload
        # xor_decode strips byte 0 and XORs the rest, so we need to build raw data
        # such that XOR-decoding produces our desired payload.
        record_type = 1  # OSD → maps to BASE feature point
        first_byte = 0x42
        from pydjirecord.utils import crc64

        seed = (first_byte + record_type) & 0xFF
        key_input = ((0x123456789ABCDEF0 * first_byte) & 0xFFFFFFFFFFFFFFFF).to_bytes(8, "little")
        xor_key = crc64(seed, key_input).to_bytes(8, "little")

        encoded = bytearray(len(xor_decoded_payload))
        for i, b in enumerate(xor_decoded_payload):
            encoded[i] = b ^ xor_key[i % 8]
        raw_data = bytes([first_byte]) + bytes(encoded)

        # Set up keychain with our AES key for BASE feature point
        import base64

        fps = [
            KeychainFeaturePoint(
                feature_point=1,
                aes_key=base64.b64encode(aes_key).decode(),
                aes_iv=base64.b64encode(aes_iv).decode(),
            )
        ]
        kc = Keychain.from_feature_points(fps)

        # This would raise "Data must be padded to 16 byte boundary"
        # if the last byte is not stripped before AES decryption.
        result = record_decode(raw_data, record_type=record_type, version=14, keychain=kc)
        assert result == inner_plaintext


class TestMalformedKeychainThroughDecode:
    """End-to-end: malformed keychain entries must not crash record_decode().

    When a keychain entry has bad base64, wrong key length, or wrong IV
    length, the invalid entry is skipped during Keychain construction.
    record_decode() should fall back to XOR-only decryption (no AES) for
    the affected feature point, rather than crashing inside AES.
    """

    def _xor_only(self, data: bytes, record_type: int) -> bytes:
        """Expected result when AES is skipped."""
        return xor_decode(data, record_type)

    def test_invalid_base64_falls_back_to_xor(self) -> None:
        fps = [KeychainFeaturePoint(feature_point=1, aes_key="!!!bad!!!", aes_iv="!!!bad!!!")]
        kc = Keychain.from_feature_points(fps)

        data = bytes(range(20))
        result = record_decode(data, record_type=1, version=14, keychain=kc)
        assert result == self._xor_only(data, 1)

    def test_wrong_key_length_falls_back_to_xor(self) -> None:
        import base64

        fps = [
            KeychainFeaturePoint(
                feature_point=1,
                aes_key=base64.b64encode(b"\x00" * 16).decode(),  # 16 bytes, not 32
                aes_iv=base64.b64encode(b"\x00" * 16).decode(),
            )
        ]
        kc = Keychain.from_feature_points(fps)

        data = bytes(range(20))
        result = record_decode(data, record_type=1, version=14, keychain=kc)
        assert result == self._xor_only(data, 1)

    def test_wrong_iv_length_falls_back_to_xor(self) -> None:
        import base64

        fps = [
            KeychainFeaturePoint(
                feature_point=1,
                aes_key=base64.b64encode(b"\x00" * 32).decode(),
                aes_iv=base64.b64encode(b"\x00" * 8).decode(),  # 8 bytes, not 16
            )
        ]
        kc = Keychain.from_feature_points(fps)

        data = bytes(range(20))
        result = record_decode(data, record_type=1, version=14, keychain=kc)
        assert result == self._xor_only(data, 1)

    def test_empty_keychain_falls_back_to_xor(self) -> None:
        kc = Keychain.from_feature_points([])

        data = bytes(range(20))
        result = record_decode(data, record_type=1, version=14, keychain=kc)
        assert result == self._xor_only(data, 1)
