"""Frame app sub-field."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FrameApp:
    """Normalized app messages frame data."""

    tip: str = ""
    warn: str = ""
