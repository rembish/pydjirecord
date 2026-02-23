"""Main DJI log parser entry point."""

from __future__ import annotations

from dataclasses import dataclass

from ._binary import BinaryReader
from .error import MissingAuxiliaryDataError
from .layout.auxiliary import AuxiliaryInfo, AuxiliaryVersion, parse_auxiliary
from .layout.details import Details
from .layout.prefix import Prefix
from .utils import pad_with_zeros


@dataclass
class DJILog:
    """Parsed DJI flight log.

    Use :meth:`from_bytes` to construct.  After construction the
    ``version`` and ``details`` attributes are available for all log
    versions without decryption.
    """

    inner: bytes
    prefix: Prefix
    version: int
    details: Details

    # Populated for v13+ during from_bytes
    auxiliary_version: AuxiliaryVersion | None = None

    @classmethod
    def from_bytes(cls, data: bytes) -> DJILog:
        """Parse header, details, and auxiliary blocks from raw log bytes.

        Records and frames are **not** decoded here — call
        ``records()`` / ``frames()`` separately (to be implemented).
        """
        prefix = Prefix.from_bytes(data[:100])
        version = prefix.version

        detail_offset = prefix.detail_offset()
        detail_data = pad_with_zeros(data[detail_offset:], 400)
        reader = BinaryReader(detail_data)

        auxiliary_version: AuxiliaryVersion | None = None

        if version < 13:
            details = Details.from_bytes(detail_data, version)
        else:
            # First auxiliary block: Info (contains encrypted Details)
            aux = parse_auxiliary(reader)
            if not isinstance(aux, AuxiliaryInfo):
                raise MissingAuxiliaryDataError("Info")
            info_data = pad_with_zeros(aux.info_data, 400)
            details = Details.from_bytes(info_data, version)

        # Recover records offset for v13+ when it's zero
        if prefix.records_offset() == 0 and version >= 13:
            aux2 = parse_auxiliary(reader)
            if isinstance(aux2, AuxiliaryVersion):
                auxiliary_version = aux2
            prefix.recover_detail_offset(reader.tell() + detail_offset)

        return cls(
            inner=data,
            prefix=prefix,
            version=version,
            details=details,
            auxiliary_version=auxiliary_version,
        )
