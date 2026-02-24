"""Shared utility functions."""

from __future__ import annotations

# CRC64 Jones polynomial (bit-reversed), matching the Rust ``crc64`` crate v2.0
_CRC64_POLY = 0x95AC9329AC4BC9B5
_MASK64 = 0xFFFFFFFFFFFFFFFF


def _build_crc64_table() -> list[int]:
    table: list[int] = []
    for i in range(256):
        crc = i
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ _CRC64_POLY
            else:
                crc >>= 1
        table.append(crc)
    return table


_CRC64_TABLE = _build_crc64_table()


def crc64(seed: int, data: bytes) -> int:
    """Compute CRC64 checksum (Jones polynomial, matches Rust ``crc64`` crate v2.0)."""
    crc = seed & _MASK64
    for byte in data:
        index = (crc ^ byte) & 0xFF
        crc = _CRC64_TABLE[index] ^ (crc >> 8)
    return crc & _MASK64


def sub_byte_field(byte: int, mask: int) -> int:
    """Extract and right-align bits selected by *mask* from *byte*."""
    byte &= mask
    while mask and not (mask & 1):
        byte >>= 1
        mask >>= 1
    return byte


def pad_with_zeros(data: bytes, min_length: int) -> bytes:
    """Pad *data* with zero bytes to reach *min_length*."""
    if len(data) >= min_length:
        return data
    return data + b"\x00" * (min_length - len(data))


def append_message(original: str, message: str) -> str:
    """Append *message* to *original* with ``'; '`` separator."""
    if original:
        return f"{original}; {message}"
    return message


_EARTH_RADIUS_M = 6_371_000.0  # metres, matching C++ kEarthRadiusKm * 1000


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two WGS-84 coordinates.

    Implements the same Vincenty spherical formula used by the DJI C++ reference
    library (``DistanceEarth`` in ``FlightRecordMaths.cpp``).  Inputs are in
    decimal degrees; output is in metres.
    """
    import math

    lat1r = math.radians(lat1)
    lon1r = math.radians(lon1)
    lat2r = math.radians(lat2)
    lon2r = math.radians(lon2)

    d_lon = abs(lon1r - lon2r)
    a = (math.cos(lat2r) * math.sin(d_lon)) ** 2
    b = math.cos(lat1r) * math.sin(lat2r) - math.sin(lat1r) * math.cos(lat2r) * math.cos(d_lon)
    e = math.sqrt(a + b**2)
    h = math.sin(lat1r) * math.sin(lat2r) + math.cos(lat1r) * math.cos(lat2r) * math.cos(d_lon)
    return _EARTH_RADIUS_M * math.atan2(e, h)
