"""Feature point enum and record type mapping."""

from __future__ import annotations

import enum


class FeaturePoint(enum.IntEnum):
    """Feature point types for AES keychain selection."""

    BASE = 1
    VISION = 2
    WAYPOINT = 3
    AGRICULTURE = 4
    AIR_LINK = 5
    AFTER_SALES = 6
    DJI_FLY_CUSTOM = 7
    PLAINTEXT = 8
    FLIGHT_HUB = 9
    GIMBAL = 10
    RC = 11
    CAMERA = 12
    BATTERY = 13
    FLY_SAFE = 14
    SECURITY = 15

    @classmethod
    def _missing_(cls, value: object) -> FeaturePoint | None:
        if not isinstance(value, int):
            return None
        obj = int.__new__(cls, value)
        obj._name_ = f"UNKNOWN_{value}"
        obj._value_ = value
        return obj

    @property
    def api_name(self) -> str:
        """Name used in DJI API serialization."""
        names: dict[int, str] = {
            1: "FR_Standardization_Feature_Base_1",
            2: "FR_Standardization_Feature_Vision_2",
            3: "FR_Standardization_Feature_Waypoint_3",
            4: "FR_Standardization_Feature_Agriculture_4",
            5: "FR_Standardization_Feature_AirLink_5",
            6: "FR_Standardization_Feature_AfterSales_6",
            7: "FR_Standardization_Feature_DJIFlyCustom_7",
            8: "FR_Standardization_Feature_Plaintext_8",
            9: "FR_Standardization_Feature_FlightHub_9",
            10: "FR_Standardization_Feature_Gimbal_10",
            11: "FR_Standardization_Feature_RC_11",
            12: "FR_Standardization_Feature_Camera_12",
            13: "FR_Standardization_Feature_Battery_13",
            14: "FR_Standardization_Feature_FlySafe_14",
            15: "FR_Standardization_Feature_Security_15",
        }
        return names.get(self.value, f"FR_Standardization_Feature_Unknown_{self.value}")


def feature_point_for_record(record_type: int, version: int) -> FeaturePoint:
    """Map a record type (magic byte) to its FeaturePoint for key selection."""
    # Plaintext records — never encrypted
    if record_type in (50, 56):
        return FeaturePoint.PLAINTEXT

    # Security
    if record_type == 55:
        return FeaturePoint.SECURITY

    # Vision
    if record_type in (17, 18):
        return FeaturePoint.VISION

    # Waypoint
    if record_type in (31, 32, 34, 35, 36, 38, 39):
        return FeaturePoint.WAYPOINT

    # Agriculture
    if record_type in (21, 41, 43, 44, 46, 47, 48, 49):
        return FeaturePoint.AGRICULTURE

    # RC-only records (always RC regardless of version)
    if record_type in (45, 62):
        return FeaturePoint.RC

    # DJI Fly Custom (app messages)
    if record_type in (5, 9, 10, 20, 24, 30, 54):
        return FeaturePoint.DJI_FLY_CUSTOM

    # Version-dependent: v14 specializes, v13 consolidates to Base
    if version >= 14:
        # Gimbal
        if record_type == 3:
            return FeaturePoint.GIMBAL
        # RC
        if record_type in (4, 11, 29, 33):
            return FeaturePoint.RC
        # Camera
        if record_type == 25:
            return FeaturePoint.CAMERA
        # Battery
        if record_type in (7, 8, 22):
            return FeaturePoint.BATTERY
        # Fly Safe
        if record_type in (28, 51, 52, 53):
            return FeaturePoint.FLY_SAFE

    # After Sales
    if record_type in (12, 16, 19, 22, 23, 26, 27, 28, 40, 51, 52, 53, 93, 102, 103, 113):
        return FeaturePoint.AFTER_SALES

    # Base — default for OSD(1), Home(2), Gimbal(3), RC(4), CenterBattery(7),
    # SmartBattery(8), Camera(25), and others
    if record_type in (1, 2, 3, 4, 6, 7, 8, 13, 14, 15, 25, 40, 58, 59, 63):
        return FeaturePoint.BASE

    # Default to Plaintext for unknown record types
    return FeaturePoint.PLAINTEXT
