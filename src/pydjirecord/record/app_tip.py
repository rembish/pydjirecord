"""App tip record."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AppTip:
    """App tip notification record."""

    message: str

    @classmethod
    def from_bytes(cls, data: bytes, version: int = 0) -> AppTip:
        """Parse app tip record from binary data."""
        message = data.split(b"\x00", 1)[0].decode("utf-8", errors="replace").strip()
        return cls(message=message)
