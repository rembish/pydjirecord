"""Record type 33 – VirtualStick (AppVirtualStickDataType).

The payload is a protobuf-encoded ``VirtualStickFlightControlData`` message.
The canonical definition lives in ``src/pydjirecord/proto/virtual_stick.proto``;
``virtual_stick_pb2.py`` is generated from it and committed alongside.

Parsing requires the ``protobuf`` package (``pip install 'pydjirecord[proto]'``).

To regenerate ``virtual_stick_pb2.py`` after editing the ``.proto`` file::

    python -m grpc_tools.protoc \\
        -I src/pydjirecord/proto \\
        --python_out=src/pydjirecord/record \\
        src/pydjirecord/proto/virtual_stick.proto
"""

from __future__ import annotations

from dataclasses import dataclass

_PROTOBUF_AVAILABLE = False

try:
    from .virtual_stick_pb2 import VirtualStickFlightControlData as _VSMsg  # type: ignore[import-untyped]

    _PROTOBUF_AVAILABLE = True
except Exception:
    pass


@dataclass
class VirtualStick:
    """Parsed VirtualStick (type 33) record."""

    pitch: float
    roll: float
    yaw: float
    vertical_throttle: float
    vertical_control_mode: int
    roll_pitch_control_mode: int
    yaw_control_mode: int
    roll_pitch_coordinate_system: int

    @classmethod
    def from_bytes(cls, data: bytes) -> VirtualStick:
        if not _PROTOBUF_AVAILABLE:
            raise ImportError("protobuf package required for VirtualStick parsing: pip install 'pydjirecord[proto]'")
        msg = _VSMsg()  # type: ignore[possibly-undefined]
        msg.ParseFromString(data)
        return cls(
            pitch=float(msg.pitch),
            roll=float(msg.roll),
            yaw=float(msg.yaw),
            vertical_throttle=float(msg.vertical_throttle),
            vertical_control_mode=int(msg.vertical_control_mode),
            roll_pitch_control_mode=int(msg.roll_pitch_control_mode),
            yaw_control_mode=int(msg.yaw_control_mode),
            roll_pitch_coordinate_system=int(msg.roll_pitch_coordinate_system),
        )
