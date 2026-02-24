"""Frame camera sub-field."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..record.camera import SDCardState


@dataclass
class FrameCamera:
    """Normalized camera frame data."""

    is_photo: bool = False
    is_video: bool = False
    sd_card_is_inserted: bool = False
    sd_card_state: SDCardState | None = None
    record_time: int = 0
