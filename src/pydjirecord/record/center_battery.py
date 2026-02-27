"""Center battery record."""

from __future__ import annotations

from dataclasses import dataclass

from .._binary import BinaryReader


@dataclass
class CenterBattery:
    """Center battery record."""

    relative_capacity: int
    voltage: float
    current_capacity: int
    full_capacity: int
    life: int
    number_of_discharges: int
    current: float
    voltage_cell1: float
    voltage_cell2: float
    voltage_cell3: float
    voltage_cell4: float
    voltage_cell5: float
    voltage_cell6: float
    serial_number: int
    temperature: float

    @classmethod
    def from_bytes(cls, data: bytes, version: int) -> CenterBattery:
        """Parse center battery record from binary data."""
        r = BinaryReader(data)
        relative_capacity = r.read_u8()
        voltage = r.read_u16() / 1000.0
        current_capacity = r.read_u16()
        full_capacity = r.read_u16()
        life = r.read_u8()
        number_of_discharges = r.read_u16()
        _error_type = r.read_u32()
        current = r.read_i16() / 1000.0

        voltage_cell1 = r.read_u16() / 1000.0
        voltage_cell2 = r.read_u16() / 1000.0
        voltage_cell3 = r.read_u16() / 1000.0
        voltage_cell4 = r.read_u16() / 1000.0
        voltage_cell5 = r.read_u16() / 1000.0
        voltage_cell6 = r.read_u16() / 1000.0

        serial_number = r.read_u16()
        _product_date = r.read_u16()

        temperature = 0.0
        if version >= 8:
            temperature = r.read_u16() / 10.0 - 273.15

        return cls(
            relative_capacity=relative_capacity,
            voltage=voltage,
            current_capacity=current_capacity,
            full_capacity=full_capacity,
            life=life,
            number_of_discharges=number_of_discharges,
            current=current,
            voltage_cell1=voltage_cell1,
            voltage_cell2=voltage_cell2,
            voltage_cell3=voltage_cell3,
            voltage_cell4=voltage_cell4,
            voltage_cell5=voltage_cell5,
            voltage_cell6=voltage_cell6,
            serial_number=serial_number,
            temperature=temperature,
        )
