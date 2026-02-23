"""KeyStorage record — encrypted keychain data."""

from __future__ import annotations

from dataclasses import dataclass

from .._binary import BinaryReader


@dataclass
class KeyStorage:
    """KeyStorage record with encrypted feature point data."""

    feature_point: int
    data: bytes

    @classmethod
    def from_bytes(cls, data: bytes, version: int = 0) -> KeyStorage:
        r = BinaryReader(data)
        feature_point = r.read_u16()
        data_length = r.read_u16()
        payload = r.read_bytes(data_length)
        return cls(feature_point=feature_point, data=payload)
