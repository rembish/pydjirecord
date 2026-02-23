"""Main DJI log parser entry point."""

from __future__ import annotations

import base64
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ._binary import BinaryReader
from .decoder import record_decode
from .error import KeychainRequiredError, MissingAuxiliaryDataError
from .frame.builder import records_to_frames
from .keychain import (
    Keychain,
    KeychainFeaturePoint,
    KeychainsRequest,
)
from .keychain.api import EncodedKeychainFeaturePoint
from .layout.auxiliary import AuxiliaryInfo, AuxiliaryVersion, parse_auxiliary
from .layout.details import Details
from .layout.prefix import Prefix
from .record import Record, parse_record
from .record.key_storage import KeyStorage
from .utils import pad_with_zeros

if TYPE_CHECKING:
    from .frame import Frame


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
        """Parse header, details, and auxiliary blocks from raw log bytes."""
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

    def keychains_request(self) -> KeychainsRequest:
        """Build a KeychainsRequest by parsing KeyStorage records.

        For v13+, this iterates the record stream with an empty keychain
        to extract the encoded feature points needed for the API call.
        """
        req = KeychainsRequest()

        if self.version < 13:
            return req

        # Read auxiliary version block to get version/department
        detail_offset = self.prefix.detail_offset()
        detail_data = pad_with_zeros(self.inner[detail_offset:], 400)
        reader = BinaryReader(detail_data)

        # Skip first auxiliary (Info)
        parse_auxiliary(reader)

        # Get version from second auxiliary block
        aux2 = parse_auxiliary(reader)
        if isinstance(aux2, AuxiliaryVersion):
            req.version = aux2.version
            from .layout.auxiliary import Department

            if isinstance(aux2.department, Department) and aux2.department.name.startswith("UNKNOWN"):
                req.department = int(Department.DJI_FLY)
            else:
                req.department = int(aux2.department)

        # Extract KeyStorage records
        records_start = self.prefix.records_offset()
        records_end = self.prefix.records_end_offset(len(self.inner))
        pos = records_start

        current_group: list[EncodedKeychainFeaturePoint] = []

        while pos < records_end:
            try:
                magic = self.inner[pos]
                length = int.from_bytes(self.inner[pos + 1 : pos + 3], "little")
                data = self.inner[pos + 3 : pos + 3 + length]
                end_byte = self.inner[pos + 3 + length] if pos + 3 + length < len(self.inner) else 0
                pos = pos + 3 + length + 1
            except (IndexError, ValueError):
                break

            if end_byte != 0xFF:
                break

            if magic == 56:
                # KeyStorage record — decode with XOR only (Plaintext feature)
                from .decoder import xor_decode

                decoded = xor_decode(data, 56) if self.version >= 7 else data
                try:
                    ks = KeyStorage.from_bytes(decoded)
                    current_group.append(
                        EncodedKeychainFeaturePoint(
                            feature_point=ks.feature_point,
                            aes_ciphertext=base64.b64encode(ks.data).decode("ascii"),
                        )
                    )
                except (EOFError, ValueError):
                    pass
            elif magic == 50:
                # KeyStorageRecover — start a new keychain group
                req.keychains.append(current_group)
                current_group = []

        req.keychains.append(current_group)
        return req

    def fetch_keychains(self, api_key: str) -> list[list[KeychainFeaturePoint]]:
        """Fetch decoded keychains from DJI API.

        Only needed for v13+ logs. Returns empty list for older versions.
        """
        if self.version < 13:
            return []
        return self.keychains_request().fetch(api_key)

    def records(
        self,
        keychains: list[list[KeychainFeaturePoint]] | None = None,
    ) -> list[Record]:
        """Parse and decrypt all records from the binary stream.

        For v13+ logs, *keychains* must be provided (from :meth:`fetch_keychains`).
        """
        if self.version >= 13 and keychains is None:
            raise KeychainRequiredError("Keychains required for v13+ logs")

        # Build keychain deque
        kc_deque: deque[Keychain] = deque()
        if keychains:
            for kc_list in keychains:
                kc_deque.append(Keychain.from_feature_points(kc_list))

        keychain = kc_deque.popleft() if kc_deque else Keychain.empty()

        records_start = self.prefix.records_offset()
        records_end = self.prefix.records_end_offset(len(self.inner))
        pos = records_start
        result: list[Record] = []

        while pos < records_end:
            try:
                magic = self.inner[pos]
                length = int.from_bytes(self.inner[pos + 1 : pos + 3], "little")
                raw_data = self.inner[pos + 3 : pos + 3 + length]
                end_pos = pos + 3 + length
                end_byte = self.inner[end_pos] if end_pos < len(self.inner) else 0
                pos = end_pos + 1
            except (IndexError, ValueError):
                break

            if end_byte != 0xFF:
                break

            # Decrypt
            decoded = record_decode(raw_data, magic, self.version, keychain)

            # Parse
            record = parse_record(magic, decoded, self.version, product_type=self.details.product_type)

            # Handle keychain switching
            if magic == 50:
                keychain = kc_deque.popleft() if kc_deque else Keychain.empty()

            result.append(record)

        return result

    def frames(
        self,
        keychains: list[list[KeychainFeaturePoint]] | None = None,
    ) -> list[Frame]:
        """Parse records and convert to normalized frames.

        For v13+ logs, *keychains* must be provided (from :meth:`fetch_keychains`).
        """
        recs = self.records(keychains)
        return records_to_frames(recs, self.details)
