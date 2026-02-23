"""Binary layout parsing for DJI log files."""

from .auxiliary import AuxiliaryInfo, AuxiliaryVersion, Department, parse_auxiliary
from .details import Details, Platform, ProductType
from .prefix import Prefix

__all__ = [
    "AuxiliaryInfo",
    "AuxiliaryVersion",
    "Department",
    "Details",
    "Platform",
    "Prefix",
    "ProductType",
    "parse_auxiliary",
]
