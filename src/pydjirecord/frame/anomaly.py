"""Flight anomaly detection and severity classification."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field

from ..record.osd import FlightAction


class FlightSeverity(enum.IntEnum):
    """Severity level for a flight."""

    GREEN = 0
    AMBER = 1
    RED = 2


RED_ACTIONS: frozenset[FlightAction] = frozenset(
    {
        FlightAction.OUT_OF_CONTROL_GO_HOME,
        FlightAction.BATTERY_FORCE_LANDING,
        FlightAction.SERIOUS_LOW_VOLTAGE_LANDING,
        FlightAction.MOTORBLOCK_LANDING,
        FlightAction.FAKE_BATTERY_LANDING,
        FlightAction.RTH_COMING_OBSTACLE_LANDING,
        FlightAction.IMU_ERROR_RTH,
        FlightAction.MC_PROTECT_GO_HOME,
    }
)

AMBER_ACTIONS: frozenset[FlightAction] = frozenset(
    {
        FlightAction.WARNING_POWER_GO_HOME,
        FlightAction.WARNING_POWER_LANDING,
        FlightAction.SMART_POWER_GO_HOME,
        FlightAction.SMART_POWER_LANDING,
        FlightAction.LOW_VOLTAGE_LANDING,
        FlightAction.LOW_VOLTAGE_GO_HOME,
        FlightAction.AVOID_GROUND_LANDING,
        FlightAction.AIRPORT_AVOID_LANDING,
        FlightAction.TOO_CLOSE_GO_HOME_LANDING,
        FlightAction.TOO_FAR_GO_HOME_LANDING,
        FlightAction.APP_REQUEST_FORCE_LANDING,
    }
)


@dataclass
class FlightAnomaly:
    """Flight anomaly detection result."""

    severity: FlightSeverity = FlightSeverity.GREEN
    actions: list[FlightAction] = field(default_factory=list)
    motor_blocked: bool = False
    max_descent_speed: float = 0.0
    final_altitude: float = 0.0
    gps_degraded_ratio: float = 0.0
