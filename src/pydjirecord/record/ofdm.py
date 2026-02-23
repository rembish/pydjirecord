"""OFDM signal record."""

from __future__ import annotations

from dataclasses import dataclass

from ..utils import sub_byte_field


@dataclass
class OFDM:
    """OFDM radio signal record."""

    signal_percent: int
    is_up: bool

    @classmethod
    def from_bytes(cls, data: bytes, version: int = 0) -> OFDM:
        bp = data[0] if data else 0
        signal_percent = sub_byte_field(bp, 0x7F)
        is_up = bool(sub_byte_field(bp, 0x80))
        return cls(signal_percent=signal_percent, is_up=is_up)
