"""DJI log file header (prefix) parsing."""

from __future__ import annotations

from dataclasses import dataclass

from .._binary import BinaryReader

_OLD_PREFIX_SIZE = 12
_PREFIX_SIZE = 100


@dataclass
class Prefix:
    """Log file header containing version and offset information.

    Binary layout (100 bytes, little-endian)::

        detail_offset : u64
        detail_length : u16
        version       : u8
        unknown       : u8
        encrypt_magic : u64
        reserved      : [u8; 80]
    """

    _detail_offset: int
    version: int

    @classmethod
    def from_bytes(cls, data: bytes) -> Prefix:
        """Parse prefix from the first 100 bytes of a log file."""
        reader = BinaryReader(data)
        detail_offset = reader.read_u64()
        _detail_length = reader.read_u16()
        version = reader.read_u8()
        return cls(_detail_offset=detail_offset, version=version)

    def recover_detail_offset(self, offset: int) -> None:
        """Override detail_offset (used for v13+ when original is zero)."""
        self._detail_offset = offset

    def detail_offset(self) -> int:
        """Byte offset where the details/auxiliary section starts."""
        if self.version < 12:
            return self._detail_offset
        return _PREFIX_SIZE

    def records_offset(self) -> int:
        """Byte offset where records begin."""
        if self.version < 6:
            return _OLD_PREFIX_SIZE
        if self.version < 12:
            return _PREFIX_SIZE
        if self.version == 12:
            return _PREFIX_SIZE + 436
        return self._detail_offset

    def records_end_offset(self, file_size: int) -> int:
        """Byte offset where records end."""
        if self.version < 12:
            return self._detail_offset
        return file_size
