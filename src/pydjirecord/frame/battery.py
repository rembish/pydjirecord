"""Frame battery sub-field."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FrameBattery:
    """Normalized battery frame data."""

    charge_level: int = 0
    voltage: float = 0.0
    current: float = 0.0
    design_capacity: int = 0
    current_capacity: int = 0
    full_capacity: int = 0
    cell_num: int = 0
    is_cell_voltage_estimated: bool = True
    cell_voltages: list[float] = field(default_factory=list)
    cell_voltage_deviation: float = 0.0
    max_cell_voltage_deviation: float = 0.0
    temperature: float = 0.0
    min_temperature: float = 0.0
    max_temperature: float = 0.0
    number_of_discharges: int = 0
    lifetime_remaining: int = 0
