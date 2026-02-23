"""App warning record."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AppWarn:
    """App warning record."""

    message: str

    @classmethod
    def from_bytes(cls, data: bytes, version: int = 0) -> AppWarn:
        message = data.split(b"\x00", 1)[0].decode("utf-8", errors="replace").strip()
        return cls(message=message)
