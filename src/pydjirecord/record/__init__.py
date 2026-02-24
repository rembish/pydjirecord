"""Record types parsed from binary log stream."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Any

from .app_gps import AppGPS
from .app_serious_warn import AppSeriousWarn
from .app_tip import AppTip
from .app_warn import AppWarn
from .camera import Camera
from .center_battery import CenterBattery
from .component_serial import ComponentSerial
from .custom import Custom
from .firmware import Firmware
from .gimbal import Gimbal
from .home import Home
from .key_storage import KeyStorage
from .mc_params import MCParams
from .ofdm import OFDM
from .osd import OSD
from .rc import RC
from .rc_display_field import RCDisplayField
from .rc_gps import RCGPS, RCGPSTime
from .recover import Recover
from .smart_battery import SmartBattery
from .smart_battery_group import (
    SmartBatteryDynamic,
    SmartBatteryGroup,
    SmartBatterySingleVoltage,
    SmartBatteryStatic,
    parse_smart_battery_group,
)

__all__ = [
    "OFDM",
    "OSD",
    "RC",
    "AppGPS",
    "AppSeriousWarn",
    "AppTip",
    "AppWarn",
    "Camera",
    "CenterBattery",
    "ComponentSerial",
    "Custom",
    "Firmware",
    "Gimbal",
    "Home",
    "KeyStorage",
    "MCParams",
    "RCGPS",
    "RCDisplayField",
    "RCGPSTime",
    "Record",
    "Recover",
    "SmartBattery",
    "SmartBatteryDynamic",
    "SmartBatteryGroup",
    "SmartBatterySingleVoltage",
    "SmartBatteryStatic",
    "parse_record",
]

# Magic byte → record type name
RECORD_TYPES: dict[int, str] = {
    1: "OSD",
    2: "Home",
    3: "Gimbal",
    4: "RC",
    5: "Custom",
    6: "MCTripodState",
    7: "CenterBattery",
    8: "SmartBattery",
    9: "AppTip",
    10: "AppWarn",
    11: "RCGPS",
    13: "Recover",
    14: "AppGPS",
    15: "Firmware",
    19: "MCParams",
    22: "SmartBatteryGroup",
    24: "AppSeriousWarn",
    25: "Camera",
    33: "VirtualStick",
    40: "ComponentSerial",
    49: "OFDM",
    50: "KeyStorageRecover",
    56: "KeyStorage",
    62: "RCDisplayField",
}


@dataclass
class Record:
    """A parsed record from the binary log stream."""

    record_type: int
    data: Any  # Parsed struct or raw bytes


def parse_record(
    magic: int,
    data: bytes,
    version: int,
    *,
    product_type: Any = None,
) -> Record:
    """Parse record data based on magic byte.

    Returns a Record with either a parsed struct or raw bytes for unknown types.
    """
    from ..layout.details import ProductType

    if product_type is None:
        product_type = ProductType.NONE

    parsed: Any
    try:
        if magic == 1:
            parsed = OSD.from_bytes(data, version)
        elif magic == 2:
            parsed = Home.from_bytes(data, version)
        elif magic == 3:
            parsed = Gimbal.from_bytes(data, version)
        elif magic == 4:
            parsed = RC.from_bytes(data, version, product_type)
        elif magic == 5:
            parsed = Custom.from_bytes(data)
        elif magic == 7:
            parsed = CenterBattery.from_bytes(data, version)
        elif magic == 8:
            parsed = SmartBattery.from_bytes(data)
        elif magic == 9:
            parsed = AppTip.from_bytes(data)
        elif magic == 10:
            parsed = AppWarn.from_bytes(data)
        elif magic == 11:
            parsed = RCGPS.from_bytes(data)
        elif magic == 13:
            parsed = Recover.from_bytes(data, version)
        elif magic == 14:
            parsed = AppGPS.from_bytes(data)
        elif magic == 15:
            parsed = Firmware.from_bytes(data)
        elif magic == 19:
            parsed = MCParams.from_bytes(data)
        elif magic == 22:
            parsed = parse_smart_battery_group(data)
        elif magic == 24:
            parsed = AppSeriousWarn.from_bytes(data)
        elif magic == 25:
            parsed = Camera.from_bytes(data)
        elif magic == 40:
            parsed = ComponentSerial.from_bytes(data)
        elif magic == 49:
            parsed = OFDM.from_bytes(data)
        elif magic == 50:
            # KeyStorageRecover: sentinel, no payload to parse
            parsed = data
        elif magic == 56:
            parsed = KeyStorage.from_bytes(data)
        elif magic == 62:
            parsed = RCDisplayField.from_bytes(data)
        else:
            parsed = data
    except (EOFError, struct.error, ValueError, IndexError):
        parsed = data

    return Record(record_type=magic, data=parsed)
