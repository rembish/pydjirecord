"""App serious warning record."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AppSeriousWarn:
    """App serious warning record."""

    message: str

    @classmethod
    def from_bytes(cls, data: bytes, version: int = 0) -> AppSeriousWarn:
        """Parse app serious warning record from binary data."""
        message = data.split(b"\x00", 1)[0].decode("utf-8", errors="replace").strip()
        return cls(message=message)
