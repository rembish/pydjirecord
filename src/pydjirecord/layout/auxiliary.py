"""Auxiliary block parsing (v13+ log files)."""

from __future__ import annotations

import enum
from dataclasses import dataclass

from .._binary import BinaryReader
from ..decoder import xor_decode
from ..error import ParseError

# ---------------------------------------------------------------------------
# Department enum
# ---------------------------------------------------------------------------


class Department(enum.IntEnum):
    """DJI department that produced the log."""

    SDK = 1
    DJIGO = 2
    DJI_FLY = 3
    AGRICULTURAL_MACHINERY = 4
    TERRA = 5
    DJI_GLASSES = 6
    DJI_PILOT = 7
    GS_PRO = 8

    @classmethod
    def _missing_(cls, value: object) -> Department | None:
        if not isinstance(value, int):
            return None
        obj = int.__new__(cls, value)
        obj._name_ = f"UNKNOWN_{value}"
        obj._value_ = value
        return obj


# ---------------------------------------------------------------------------
# Auxiliary data structures
# ---------------------------------------------------------------------------


@dataclass
class AuxiliaryInfo:
    """Auxiliary Info block (magic 0): contains XOR-encrypted Details data."""

    version_data: int
    info_data: bytes
    signature_data: bytes

    @classmethod
    def from_bytes(cls, data: bytes) -> AuxiliaryInfo:
        """Parse from XOR-decoded bytes."""
        r = BinaryReader(data)
        version_data = r.read_u8()
        info_length = r.read_u16()
        info_data = r.read_bytes(info_length)
        signature_length = r.read_u16()
        signature_data = r.read_bytes(signature_length)
        return cls(
            version_data=version_data,
            info_data=info_data,
            signature_data=signature_data,
        )


@dataclass
class AuxiliaryVersion:
    """Auxiliary Version block (magic 1): department and version metadata."""

    version: int
    department: Department

    @classmethod
    def from_bytes(cls, data: bytes) -> AuxiliaryVersion:
        """Parse version block from raw bytes."""
        r = BinaryReader(data)
        version = r.read_u16()
        department = Department(r.read_u8())
        return cls(version=version, department=department)


# ---------------------------------------------------------------------------
# Parsing entry point
# ---------------------------------------------------------------------------


def parse_auxiliary(reader: BinaryReader) -> AuxiliaryInfo | AuxiliaryVersion:
    """Read one Auxiliary block from *reader*.

    Layout::

        magic : u8   (0 = Info, 1 = Version)
        size  : u16  (byte count of payload)
        data  : [u8; size]
    """
    magic = reader.read_u8()
    size = reader.read_u16()
    raw = reader.read_bytes(size)

    if magic == 0:
        decoded = xor_decode(raw, record_type=0)
        return AuxiliaryInfo.from_bytes(decoded)
    if magic == 1:
        return AuxiliaryVersion.from_bytes(raw)

    raise ParseError(f"Unknown auxiliary magic byte: {magic}")
