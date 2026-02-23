"""OSD (On-Screen Display) record — primary flight telemetry."""

from __future__ import annotations

import enum
import math
from dataclasses import dataclass

from .._binary import BinaryReader
from ..utils import sub_byte_field


class FlightMode(enum.IntEnum):
    MANUAL = 0
    ATTI = 1
    ATTI_COURSE_LOCK = 2
    ATTI_HOVER = 3
    HOVER = 4
    GPS_BLAKE = 5
    GPS_ATTI = 6
    GPS_COURSE_LOCK = 7
    GPS_HOME_LOCK = 8
    GPS_HOT_POINT = 9
    ASSISTED_TAKEOFF = 10
    AUTO_TAKEOFF = 11
    AUTO_LANDING = 12
    ATTI_LANDING = 13
    GPS_WAYPOINT = 14
    GO_HOME = 15
    CLICK_GO = 16
    JOYSTICK = 17
    GPS_ATTI_WRISTBAND = 18
    CINEMATIC = 19
    ATTI_LIMITED = 23
    DRAW = 24
    GPS_FOLLOW_ME = 25
    ACTIVE_TRACK = 26
    TAP_FLY = 27
    PANO = 28
    FARMING = 29
    FPV = 30
    GPS_SPORT = 31
    GPS_NOVICE = 32
    CONFIRM_LANDING = 33
    TERRAIN_TRACKING = 35
    NAVI_ADV_GO_HOME = 36
    NAVI_ADV_LANDING = 37
    TRIPOD = 38
    TRACK_HEADLOCK = 39
    ENGINE_START = 41
    GPS_GENTLE = 43

    @classmethod
    def _missing_(cls, value: object) -> FlightMode | None:
        if not isinstance(value, int):
            return None
        obj = int.__new__(cls, value)
        obj._name_ = f"UNKNOWN_{value}"
        obj._value_ = value
        return obj


class AppCommand(enum.IntEnum):
    AUTO_FLY = 1
    AUTO_LANDING = 2
    HOME_POINT_NOW = 3
    HOME_POINT_HOT = 4
    HOME_POINT_LOCK = 5
    GO_HOME = 6
    START_MOTOR = 7
    STOP_MOTOR = 8
    CALIBRATION = 9
    DEFORM_PROTEC_CLOSE = 10
    DEFORM_PROTEC_OPEN = 11
    DROP_GO_HOME = 12
    DROP_TAKE_OFF = 13
    DROP_LANDING = 14
    DYNAMIC_HOME_POINT_OPEN = 15
    DYNAMIC_HOME_POINT_CLOSE = 16
    FOLLOW_FUNCTION_OPEN = 17
    FOLLOW_FUNCTION_CLOSE = 18
    IOC_OPEN = 19
    IOC_CLOSE = 20
    DROP_CALIBRATION = 21
    PACK_MODE = 22
    UNPACK_MODE = 23
    ENTER_MANUAL_MODE = 24
    STOP_DEFORM = 25
    DOWN_DEFORM = 28
    UP_DEFORM = 29
    FORCE_LANDING = 30
    FORCE_LANDING2 = 31

    @classmethod
    def _missing_(cls, value: object) -> AppCommand | None:
        if not isinstance(value, int):
            return None
        obj = int.__new__(cls, value)
        obj._name_ = f"UNKNOWN_{value}"
        obj._value_ = value
        return obj


class GroundOrSky(enum.IntEnum):
    GROUND = 0
    SKY = 2

    @classmethod
    def _missing_(cls, value: object) -> GroundOrSky | None:
        if not isinstance(value, int):
            return None
        if value in (0, 1):
            return cls.GROUND
        if value in (2, 3):
            return cls.SKY
        obj = int.__new__(cls, value)
        obj._name_ = f"UNKNOWN_{value}"
        obj._value_ = value
        return obj


class GoHomeStatus(enum.IntEnum):
    STANDBY = 0
    PREASCENDING = 1
    ALIGN = 2
    ASCENDING = 3
    CRUISE = 4
    BRAKING = 5
    BYPASSING = 6

    @classmethod
    def _missing_(cls, value: object) -> GoHomeStatus | None:
        if not isinstance(value, int):
            return None
        obj = int.__new__(cls, value)
        obj._name_ = f"UNKNOWN_{value}"
        obj._value_ = value
        return obj


class BatteryType(enum.IntEnum):
    NON_SMART = 1
    SMART = 2

    @classmethod
    def _missing_(cls, value: object) -> BatteryType | None:
        if not isinstance(value, int):
            return None
        obj = int.__new__(cls, value)
        obj._name_ = f"UNKNOWN_{value}"
        obj._value_ = value
        return obj


class FlightAction(enum.IntEnum):
    NONE = 0
    WARNING_POWER_GO_HOME = 1
    WARNING_POWER_LANDING = 2
    SMART_POWER_GO_HOME = 3
    SMART_POWER_LANDING = 4
    LOW_VOLTAGE_LANDING = 5
    LOW_VOLTAGE_GO_HOME = 6
    SERIOUS_LOW_VOLTAGE_LANDING = 7
    RC_ONEKEY_GO_HOME = 8
    RC_ASSISTANT_TAKEOFF = 9
    RC_AUTO_TAKEOFF = 10
    RC_AUTO_LANDING = 11
    APP_AUTO_GO_HOME = 12
    APP_AUTO_LANDING = 13
    APP_AUTO_TAKEOFF = 14
    OUT_OF_CONTROL_GO_HOME = 15
    API_AUTO_TAKEOFF = 16
    API_AUTO_LANDING = 17
    API_AUTO_GO_HOME = 18
    AVOID_GROUND_LANDING = 19
    AIRPORT_AVOID_LANDING = 20
    TOO_CLOSE_GO_HOME_LANDING = 21
    TOO_FAR_GO_HOME_LANDING = 22
    APP_WP_MISSION = 23
    WP_AUTO_TAKEOFF = 24
    GO_HOME_AVOID = 25
    P_GO_HOME_FINISH = 26
    VERT_LOW_LIMIT_LANDING = 27
    BATTERY_FORCE_LANDING = 28
    MC_PROTECT_GO_HOME = 29
    MOTORBLOCK_LANDING = 30
    APP_REQUEST_FORCE_LANDING = 31
    FAKE_BATTERY_LANDING = 32
    RTH_COMING_OBSTACLE_LANDING = 33
    IMU_ERROR_RTH = 34

    @classmethod
    def _missing_(cls, value: object) -> FlightAction | None:
        if not isinstance(value, int):
            return None
        obj = int.__new__(cls, value)
        obj._name_ = f"UNKNOWN_{value}"
        obj._value_ = value
        return obj


class MotorStartFailedCause(enum.IntEnum):
    NONE = 0
    COMPASS_ERROR = 1
    ASSISTANT_PROTECTED = 2
    DEVICE_LOCKED = 3
    DISTANCE_LIMIT = 4
    IMU_NEED_CALIBRATION = 5
    IMU_SN_ERROR = 6
    IMU_WARNING = 7
    COMPASS_CALIBRATING = 8
    ATTI_ERROR = 9
    NOVICE_PROTECTED = 10
    BATTERY_CELL_ERROR = 11
    BATTERY_COMMUNITE_ERROR = 12
    SERIOUS_LOW_VOLTAGE = 13
    SERIOUS_LOW_POWER = 14
    LOW_VOLTAGE = 15
    TEMPURE_VOL_LOW = 16
    SMART_LOW_TO_LAND = 17
    BATTERY_NOT_READY = 18
    SIMULATOR_MODE = 19
    PACK_MODE = 20
    ATTITUDE_ABNORMAL = 21
    UN_ACTIVE = 22
    FLY_FORBIDDEN_ERROR = 23
    BIAS_ERROR = 24
    ESC_ERROR = 25
    IMU_INIT_ERROR = 26
    SYSTEM_UPGRADE = 27
    SIMULATOR_STARTED = 28
    IMU_ING_ERROR = 29
    ATTI_ANGLE_OVER = 30
    GYROSCOPE_ERROR = 31
    ACCELERATOR_ERROR = 32
    COMPASS_FAILED = 33
    BAROMETER_ERROR = 34
    BAROMETER_NEGATIVE = 35
    COMPASS_BIG = 36
    GYROSCOPE_BIAS_BIG = 37
    ACCELERATOR_BIAS_BIG = 38
    COMPASS_NOISE_BIG = 39
    BAROMETER_NOISE_BIG = 40
    INVALID_SN = 41
    FLASH_OPERATING = 44
    GPS_DISCONNECT = 45
    SD_CARD_EXCEPTION = 47
    IMU_NO_CONNECTION = 61
    RC_CALIBRATION = 62
    RC_CALIBRATION_EXCEPTION = 63
    RC_CALIBRATION_UNFINISHED = 64
    RC_CALIBRATION_EXCEPTION2 = 65
    RC_CALIBRATION_EXCEPTION3 = 66
    AIRCRAFT_TYPE_MISMATCH = 67
    FOUND_UNFINISHED_MODULE = 68
    CYRO_ABNORMAL = 70
    BARO_ABNORMAL = 71
    COMPASS_ABNORMAL = 72
    GPS_ABNORMAL = 73
    NS_ABNORMAL = 74
    TOPOLOGY_ABNORMAL = 75
    RC_NEED_CALI = 76
    INVALID_FLOAT = 77
    M600_BAT_TOO_LITTLE = 78
    M600_BAT_AUTH_ERR = 79
    M600_BAT_COMM_ERR = 80
    M600_BAT_DIF_VOLT_LARGE_1 = 81
    M600_BAT_DIF_VOLT_LARGE_2 = 82
    INVALID_VERSION = 83
    GIMBAL_GYRO_ABNORMAL = 84
    GIMBAL_ESC_PITCH_NON_DATA = 85
    GIMBAL_ESC_ROLL_NON_DATA = 86
    GIMBAL_ESC_YAW_NON_DATA = 87
    GIMBAL_FIRMW_IS_UPDATING = 88
    GIMBAL_DISORDER = 89
    GIMBAL_PITCH_SHOCK = 90
    GIMBAL_ROLL_SHOCK = 91
    GIMBAL_YAW_SHOCK = 92
    IMU_CALIBRATION_FINISHED = 93
    BATT_VERSION_ERROR = 101
    RTK_BAD_SIGNAL = 102
    RTK_DEVIATION_ERROR = 103
    ESC_CALIBRATING = 112
    GPS_SIGN_INVALID = 113
    GIMBAL_IS_CALIBRATING = 114
    LOCK_BY_APP = 115
    START_FLY_HEIGHT_ERROR = 116
    ESC_VERSION_NOT_MATCH = 117
    IMU_ORI_NOT_MATCH = 118
    STOP_BY_APP = 119
    COMPASS_IMU_ORI_NOT_MATCH = 120
    BATTERY_OVER_TEMPERATURE = 123
    BATTERY_INSTALL_ERROR = 124
    BE_IMPACT = 125

    @classmethod
    def _missing_(cls, value: object) -> MotorStartFailedCause | None:
        if not isinstance(value, int):
            return None
        obj = int.__new__(cls, value)
        obj._name_ = f"UNKNOWN_{value}"
        obj._value_ = value
        return obj


class NonGPSCause(enum.IntEnum):
    ALREADY = 0
    FORBID = 1
    GPS_NUM_NON_ENOUGH = 2
    GPS_HDOP_LARGE = 3
    GPS_POSITION_NON_MATCH = 4
    SPEED_ERROR_LARGE = 5
    YAW_ERROR_LARGE = 6
    COMPASS_ERROR_LARGE = 7

    @classmethod
    def _missing_(cls, value: object) -> NonGPSCause | None:
        if not isinstance(value, int):
            return None
        obj = int.__new__(cls, value)
        obj._name_ = f"UNKNOWN_{value}"
        obj._value_ = value
        return obj


class DroneType(enum.IntEnum):
    NONE = 0
    INSPIRE1 = 1
    PHANTOM3_ADVANCED = 2
    PHANTOM3_PRO = 3
    PHANTOM3_STANDARD = 4
    OPEN_FRAME = 5
    ACE_ONE = 6
    WKM = 7
    NAZA = 8
    A2 = 9
    A3 = 10
    PHANTOM4 = 11
    MATRICE600 = 14
    PHANTOM3_4K = 15
    MAVIC_PRO = 16
    INSPIRE2 = 17
    PHANTOM4_PRO = 18
    N3 = 20
    SPARK = 21
    MATRICE600_PRO = 23
    MAVIC_AIR = 24
    MATRICE200 = 25
    PHANTOM4_ADVANCED = 27
    MATRICE210 = 28
    PHANTOM3_SE = 29
    MATRICE210_RTK = 30
    PHANTOM4_PRO_V2 = 36
    MAVIC2 = 41
    MAVIC2_ENTERPRISE = 51
    MAVIC_AIR2 = 58
    MATRICE300_RTK = 60
    MINI2 = 63
    MAVIC3_ENTERPRISE = 77
    MAVIC3_PRO = 84
    MATRICE350_RTK = 89
    MINI4_PRO = 93
    AVATA2 = 94

    @classmethod
    def _missing_(cls, value: object) -> DroneType | None:
        if not isinstance(value, int):
            return None
        obj = int.__new__(cls, value)
        obj._name_ = f"UNKNOWN_{value}"
        obj._value_ = value
        return obj


class ImuInitFailReason(enum.IntEnum):
    MONITOR_ERROR = 0
    COLLECTING_DATA = 1
    ACCE_DEAD = 3
    COMPASS_DEAD = 4
    BAROMETER_DEAD = 5
    BAROMETER_NEGATIVE = 6
    COMPASS_MOD_TOO_LARGE = 7
    GYRO_BIAS_TOO_LARGE = 8
    ACCE_BIAS_TOO_LARGE = 9
    COMPASS_NOISE_TOO_LARGE = 10
    BAROMETER_NOISE_TOO_LARGE = 11
    WAITING_MC_STATIONARY = 12
    ACCE_MOVE_TOO_LARGE = 13
    MC_HEADER_MOVED = 14
    MC_VIBRATED = 15

    @classmethod
    def _missing_(cls, value: object) -> ImuInitFailReason | None:
        if not isinstance(value, int):
            return None
        obj = int.__new__(cls, value)
        obj._name_ = f"UNKNOWN_{value}"
        obj._value_ = value
        return obj


@dataclass
class OSD:
    """OSD record — primary flight telemetry data."""

    longitude: float
    latitude: float
    altitude: float
    speed_x: float
    speed_y: float
    speed_z: float
    pitch: float
    roll: float
    yaw: float
    flight_mode: FlightMode
    rc_outcontrol: bool
    app_command: AppCommand
    can_ioc_work: bool
    ground_or_sky: GroundOrSky
    is_motor_up: bool
    is_swave_work: bool
    go_home_status: GoHomeStatus
    is_vision_used: bool
    voltage_warning: int
    is_imu_preheated: bool
    is_gps_valid: bool
    is_compass_error: bool
    wave_error: bool
    gps_level: int
    battery_type: BatteryType
    is_out_of_limit: bool
    is_go_home_height_modified: bool
    is_propeller_catapult: bool
    is_motor_blocked: bool
    is_not_enough_force: bool
    is_barometer_dead_in_air: bool
    is_vibrating: bool
    is_acceletor_over_range: bool
    gps_num: int
    flight_action: FlightAction
    motor_start_failed_cause: MotorStartFailedCause
    non_gps_cause: NonGPSCause
    battery: int
    s_wave_height: float
    fly_time: float
    drone_type: DroneType
    imu_init_fail_reason: ImuInitFailReason

    @classmethod
    def from_bytes(cls, data: bytes, version: int) -> OSD:
        r = BinaryReader(data)
        longitude = math.degrees(r.read_f64())
        latitude = math.degrees(r.read_f64())
        altitude = r.read_i16() / 10.0
        speed_x = r.read_i16() / 10.0
        speed_y = r.read_i16() / 10.0
        speed_z = r.read_i16() / 10.0
        pitch = r.read_i16() / 10.0
        roll = r.read_i16() / 10.0
        yaw = r.read_i16() / 10.0

        bp1 = r.read_u8()
        flight_mode = FlightMode(sub_byte_field(bp1, 0x7F))
        rc_outcontrol = bool(sub_byte_field(bp1, 0x80))

        app_command = AppCommand(r.read_u8())

        bp2 = r.read_u8()
        can_ioc_work = bool(sub_byte_field(bp2, 0x01))
        ground_or_sky = GroundOrSky(sub_byte_field(bp2, 0x06))
        is_motor_up = bool(sub_byte_field(bp2, 0x08))
        is_swave_work = bool(sub_byte_field(bp2, 0x10))
        go_home_status = GoHomeStatus(sub_byte_field(bp2, 0xE0))

        bp3 = r.read_u8()
        is_vision_used = bool(sub_byte_field(bp3, 0x01))
        voltage_warning = sub_byte_field(bp3, 0x06)
        is_imu_preheated = bool(sub_byte_field(bp3, 0x10))
        is_gps_valid = bool(sub_byte_field(bp3, 0x80))

        bp4 = r.read_u8()
        is_compass_error = bool(sub_byte_field(bp4, 0x01))
        wave_error = bool(sub_byte_field(bp4, 0x02))
        gps_level = sub_byte_field(bp4, 0x3C)
        battery_type = BatteryType(sub_byte_field(bp4, 0xC0))

        bp5 = r.read_u8()
        is_out_of_limit = bool(sub_byte_field(bp5, 0x01))
        is_go_home_height_modified = bool(sub_byte_field(bp5, 0x02))
        is_propeller_catapult = bool(sub_byte_field(bp5, 0x04))
        is_motor_blocked = bool(sub_byte_field(bp5, 0x08))
        is_not_enough_force = bool(sub_byte_field(bp5, 0x10))
        is_barometer_dead_in_air = bool(sub_byte_field(bp5, 0x20))
        is_vibrating = bool(sub_byte_field(bp5, 0x40))
        is_acceletor_over_range = bool(sub_byte_field(bp5, 0x80))

        gps_num = r.read_u8()
        flight_action = FlightAction(r.read_u8())
        motor_start_failed_cause = MotorStartFailedCause(r.read_u8())

        bp6 = r.read_u8()
        non_gps_cause = NonGPSCause(sub_byte_field(bp6, 0x0F))

        battery = r.read_u8()
        s_wave_height = r.read_u8() / 10.0
        fly_time = r.read_u16() / 10.0
        _motor_revolution = r.read_u8()
        _unknown = r.read_u16()
        _version_c = r.read_u8()

        drone_type = DroneType(r.read_u8() if version >= 2 else 0)
        imu_init_fail_reason = ImuInitFailReason(r.read_u8() if version >= 3 else 0)

        return cls(
            longitude=longitude,
            latitude=latitude,
            altitude=altitude,
            speed_x=speed_x,
            speed_y=speed_y,
            speed_z=speed_z,
            pitch=pitch,
            roll=roll,
            yaw=yaw,
            flight_mode=flight_mode,
            rc_outcontrol=rc_outcontrol,
            app_command=app_command,
            can_ioc_work=can_ioc_work,
            ground_or_sky=ground_or_sky,
            is_motor_up=is_motor_up,
            is_swave_work=is_swave_work,
            go_home_status=go_home_status,
            is_vision_used=is_vision_used,
            voltage_warning=voltage_warning,
            is_imu_preheated=is_imu_preheated,
            is_gps_valid=is_gps_valid,
            is_compass_error=is_compass_error,
            wave_error=wave_error,
            gps_level=gps_level,
            battery_type=battery_type,
            is_out_of_limit=is_out_of_limit,
            is_go_home_height_modified=is_go_home_height_modified,
            is_propeller_catapult=is_propeller_catapult,
            is_motor_blocked=is_motor_blocked,
            is_not_enough_force=is_not_enough_force,
            is_barometer_dead_in_air=is_barometer_dead_in_air,
            is_vibrating=is_vibrating,
            is_acceletor_over_range=is_acceletor_over_range,
            gps_num=gps_num,
            flight_action=flight_action,
            motor_start_failed_cause=motor_start_failed_cause,
            non_gps_cause=non_gps_cause,
            battery=battery,
            s_wave_height=s_wave_height,
            fly_time=fly_time,
            drone_type=drone_type,
            imu_init_fail_reason=imu_init_fail_reason,
        )
