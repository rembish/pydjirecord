"""Frame custom sub-field."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class FrameCustom:
    """Custom frame data — timestamp."""

    date_time: datetime = field(default_factory=lambda: datetime(1970, 1, 1, tzinfo=UTC))
