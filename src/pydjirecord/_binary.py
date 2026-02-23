"""Low-level little-endian binary reader."""

from __future__ import annotations

import io
import struct
from typing import cast


class BinaryReader:
    """Little-endian binary reader wrapping a bytes buffer."""

    __slots__ = ("_stream",)

    def __init__(self, data: bytes | bytearray | memoryview) -> None:
        self._stream = io.BytesIO(bytes(data))

    def read_u8(self) -> int:
        return cast("int", struct.unpack("<B", self._read(1))[0])

    def read_u16(self) -> int:
        return cast("int", struct.unpack("<H", self._read(2))[0])

    def read_i32(self) -> int:
        return cast("int", struct.unpack("<i", self._read(4))[0])

    def read_u64(self) -> int:
        return cast("int", struct.unpack("<Q", self._read(8))[0])

    def read_i64(self) -> int:
        return cast("int", struct.unpack("<q", self._read(8))[0])

    def read_f32(self) -> float:
        return cast("float", struct.unpack("<f", self._read(4))[0])

    def read_f64(self) -> float:
        return cast("float", struct.unpack("<d", self._read(8))[0])

    def read_bytes(self, n: int) -> bytes:
        return self._read(n)

    def read_string(self, n: int) -> str:
        """Read *n* bytes as a null-terminated UTF-8 string."""
        raw = self._read(n)
        return raw.split(b"\x00", 1)[0].decode("utf-8", errors="replace")

    def read_i32_array(self, count: int) -> list[int]:
        return [cast("int", v) for v in struct.unpack(f"<{count}i", self._read(4 * count))]

    def read_f64_array(self, count: int) -> list[float]:
        return [cast("float", v) for v in struct.unpack(f"<{count}d", self._read(8 * count))]

    # -- position helpers --------------------------------------------------

    def tell(self) -> int:
        return self._stream.tell()

    def seek(self, pos: int) -> None:
        self._stream.seek(pos)

    def skip(self, n: int) -> None:
        self._stream.seek(n, io.SEEK_CUR)

    # -- internal ----------------------------------------------------------

    def _read(self, n: int) -> bytes:
        data = self._stream.read(n)
        if data is None or len(data) < n:
            raise EOFError(f"Expected {n} bytes, got {len(data) if data else 0}")
        return data
