"""Camera record."""

from __future__ import annotations

import enum
from dataclasses import dataclass

from .._binary import BinaryReader
from ..utils import sub_byte_field


class SDCardState(enum.IntEnum):
    NORMAL = 0
    NO_CARD = 1
    INVALID_CARD = 2
    WRITE_PROTECTED = 3
    UNFORMATTED = 4
    FORMATTING = 5
    ILLEGAL_FILE_SYS = 6
    FULL = 8
    LOW_SPEED = 9
    INDEX_MAX = 11
    INITIALIZE = 12
    SUGGEST_FORMAT = 13
    REPAIRING = 14

    @classmethod
    def _missing_(cls, value: object) -> SDCardState | None:
        if not isinstance(value, int):
            return None
        obj = int.__new__(cls, value)
        obj._name_ = f"UNKNOWN_{value}"
        obj._value_ = value
        return obj


class CameraWorkMode(enum.IntEnum):
    CAPTURE = 0
    RECORDING = 1
    PLAYBACK = 2
    TRANSCODE = 3
    TUNING = 4
    POWER_SAVE = 5
    DOWNLOAD = 6
    XCODE_PLAYBACK = 7
    BROADCAST = 8

    @classmethod
    def _missing_(cls, value: object) -> CameraWorkMode | None:
        if not isinstance(value, int):
            return None
        obj = int.__new__(cls, value)
        obj._name_ = f"UNKNOWN_{value}"
        obj._value_ = value
        return obj


@dataclass
class Camera:
    """Camera record."""

    is_shooting_single_photo: bool
    is_recording: bool
    has_sd_card: bool
    sd_card_state: SDCardState
    work_mode: CameraWorkMode = CameraWorkMode.CAPTURE
    sd_card_total_capacity: int = 0
    sd_card_remain_capacity: int = 0
    remain_photo_num: int = 0
    remain_video_timer: int = 0
    record_time: int = 0
    camera_type: int = 0

    @classmethod
    def from_bytes(cls, data: bytes, version: int = 0) -> Camera:
        r = BinaryReader(data)
        bp1 = r.read_u8()
        is_shooting_single_photo = bool(sub_byte_field(bp1, 0x38))
        is_recording = bool(sub_byte_field(bp1, 0xC0))

        bp2 = r.read_u8()
        has_sd_card = bool(sub_byte_field(bp2, 0x02))
        sd_card_state = SDCardState(sub_byte_field(bp2, 0x3C))

        # Extended fields (bytes 2-23) — guard for short records.
        work_mode = CameraWorkMode.CAPTURE
        sd_card_total_capacity = 0
        sd_card_remain_capacity = 0
        remain_photo_num = 0
        remain_video_timer = 0
        record_time = 0
        camera_type = 0

        if len(data) >= 24:
            _bp3 = r.read_u8()
            _bp4 = r.read_u8()
            work_mode = CameraWorkMode(r.read_u8())
            sd_card_total_capacity = r.read_u32()
            sd_card_remain_capacity = r.read_u32()
            remain_photo_num = r.read_u32()
            remain_video_timer = r.read_u32()
            record_time = r.read_u16()
            camera_type = r.read_u8()

        return cls(
            is_shooting_single_photo=is_shooting_single_photo,
            is_recording=is_recording,
            has_sd_card=has_sd_card,
            sd_card_state=sd_card_state,
            work_mode=work_mode,
            sd_card_total_capacity=sd_card_total_capacity,
            sd_card_remain_capacity=sd_card_remain_capacity,
            remain_photo_num=remain_photo_num,
            remain_video_timer=remain_video_timer,
            record_time=record_time,
            camera_type=camera_type,
        )
