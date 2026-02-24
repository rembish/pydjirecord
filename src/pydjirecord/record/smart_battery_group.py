"""Smart battery group record (multi-battery)."""

from __future__ import annotations

from dataclasses import dataclass, field

from .._binary import BinaryReader


@dataclass
class SmartBatteryStatic:
    """Static battery info."""

    index: int
    designed_capacity: int
    loop_times: int
    full_voltage: int
    serial_number: int
    version_number: bytes
    battery_life: int
    battery_type: int


@dataclass
class SmartBatteryDynamic:
    """Dynamic battery telemetry."""

    index: int
    current_voltage: float
    current_current: float
    full_capacity: int
    remained_capacity: int
    temperature: float
    cell_count: int
    capacity_percent: int
    battery_state: int


@dataclass
class SmartBatterySingleVoltage:
    """Per-cell voltage data."""

    index: int
    cell_count: int
    cell_voltages: list[float] = field(default_factory=list)


SmartBatteryGroup = SmartBatteryStatic | SmartBatteryDynamic | SmartBatterySingleVoltage


def parse_smart_battery_group(data: bytes, version: int = 0) -> SmartBatteryGroup:
    """Parse a SmartBatteryGroup record by magic sub-type byte."""
    r = BinaryReader(data)
    magic = r.read_u8()

    if magic == 1:
        index = r.read_u8()
        designed_capacity = r.read_u32()
        loop_times = r.read_u16()
        full_voltage = r.read_u32()
        _unknown = r.read_u16()
        serial_number = r.read_u16()
        r.skip(10)
        r.skip(5)
        version_number = r.read_bytes(8)
        battery_life = r.read_u8()
        battery_type = r.read_u8()
        return SmartBatteryStatic(
            index=index,
            designed_capacity=designed_capacity,
            loop_times=loop_times,
            full_voltage=full_voltage,
            serial_number=serial_number,
            version_number=version_number,
            battery_life=battery_life,
            battery_type=battery_type,
        )

    if magic == 2:
        index = r.read_u8()
        current_voltage = r.read_i32() / 1000.0
        # abs() matches the Rust reference (smart_battery_group.rs:51).
        # DJI always reports discharge as negative; abs() normalises to a
        # magnitude-only value.  Charge/discharge direction is available
        # via battery_state flags if needed.
        current_current = abs(r.read_i32()) / 1000.0
        full_capacity = r.read_u32()
        remained_capacity = r.read_u32()
        temperature = r.read_i16() / 10.0
        cell_count = r.read_u8()
        capacity_percent = r.read_u8()
        battery_state = r.read_u64()
        return SmartBatteryDynamic(
            index=index,
            current_voltage=current_voltage,
            current_current=current_current,
            full_capacity=full_capacity,
            remained_capacity=remained_capacity,
            temperature=temperature,
            cell_count=cell_count,
            capacity_percent=capacity_percent,
            battery_state=battery_state,
        )

    if magic == 3:
        index = r.read_u8()
        cell_count = r.read_u8()
        cell_voltages = [r.read_u16() / 1000.0 for _ in range(cell_count)]
        return SmartBatterySingleVoltage(index=index, cell_count=cell_count, cell_voltages=cell_voltages)

    # Unknown sub-type, return minimal static entry
    return SmartBatteryStatic(
        index=0,
        designed_capacity=0,
        loop_times=0,
        full_voltage=0,
        serial_number=0,
        version_number=b"",
        battery_life=0,
        battery_type=0,
    )
