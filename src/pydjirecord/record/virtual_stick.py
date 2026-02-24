"""Record type 33 – VirtualStick (AppVirtualStickDataType).

The payload is a protobuf-encoded ``VirtualStickFlightControlData`` message::

    message VirtualStickFlightControlData {
        float pitch                     = 1;
        float roll                      = 2;
        float yaw                       = 3;
        float verticalThrottle          = 4;
        int32 verticalControlMode       = 5;
        int32 rollPitchControlMode      = 6;
        int32 yawControlMode            = 7;
        int32 rollPitchCoordinateSystem = 8;
    }

Parsing requires the ``protobuf`` package (``pip install 'pydjirecord[proto]'``).
"""

from __future__ import annotations

from dataclasses import dataclass

_PROTOBUF_AVAILABLE = False
_VS_MSG_CLASS = None

try:
    from google.protobuf import descriptor_pb2 as _dpb2
    from google.protobuf import descriptor_pool as _dpool
    from google.protobuf import message_factory as _mfactory

    def _build_vs_class() -> type:  # type: ignore[return]
        fdp = _dpb2.FileDescriptorProto()
        fdp.name = "virtual_stick.proto"
        fdp.syntax = "proto3"
        mdp = fdp.message_type.add()
        mdp.name = "VirtualStickFlightControlData"

        for i, name in enumerate(["pitch", "roll", "yaw", "vertical_throttle"], 1):
            f = mdp.field.add()
            f.name = name
            f.number = i
            f.type = _dpb2.FieldDescriptorProto.TYPE_FLOAT
            f.label = _dpb2.FieldDescriptorProto.LABEL_OPTIONAL

        for i, name in enumerate(
            ["vertical_control_mode", "roll_pitch_control_mode", "yaw_control_mode", "roll_pitch_coordinate_system"],
            5,
        ):
            f = mdp.field.add()
            f.name = name
            f.number = i
            f.type = _dpb2.FieldDescriptorProto.TYPE_INT32
            f.label = _dpb2.FieldDescriptorProto.LABEL_OPTIONAL

        pool = _dpool.DescriptorPool()
        pool.Add(fdp)
        desc = pool.FindMessageTypeByName("VirtualStickFlightControlData")
        return _mfactory.GetMessageClass(desc)  # type: ignore[return-value]

    _VS_MSG_CLASS = _build_vs_class()
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
        if not _PROTOBUF_AVAILABLE or _VS_MSG_CLASS is None:
            raise ImportError("protobuf package required for VirtualStick parsing: pip install 'pydjirecord[proto]'")
        msg = _VS_MSG_CLASS()
        msg.ParseFromString(data)  # type: ignore[attr-defined]
        return cls(
            pitch=float(msg.pitch),  # type: ignore[attr-defined]
            roll=float(msg.roll),  # type: ignore[attr-defined]
            yaw=float(msg.yaw),  # type: ignore[attr-defined]
            vertical_throttle=float(msg.vertical_throttle),  # type: ignore[attr-defined]
            vertical_control_mode=int(msg.vertical_control_mode),  # type: ignore[attr-defined]
            roll_pitch_control_mode=int(msg.roll_pitch_control_mode),  # type: ignore[attr-defined]
            yaw_control_mode=int(msg.yaw_control_mode),  # type: ignore[attr-defined]
            roll_pitch_coordinate_system=int(msg.roll_pitch_coordinate_system),  # type: ignore[attr-defined]
        )
