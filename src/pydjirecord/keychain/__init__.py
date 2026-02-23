"""Keychain management for AES decryption (v13+ logs)."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING

from .api import EncodedKeychainFeaturePoint, KeychainFeaturePoint, KeychainsRequest
from .feature_point import FeaturePoint, feature_point_for_record

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "EncodedKeychainFeaturePoint",
    "FeaturePoint",
    "Keychain",
    "KeychainFeaturePoint",
    "KeychainsRequest",
    "feature_point_for_record",
]


class Keychain:
    """Maps FeaturePoint → (iv, key) for AES decryption.

    The IV is updated after each record decryption (IV chaining).
    """

    def __init__(self) -> None:
        self._map: dict[int, tuple[bytes, bytes]] = {}

    @classmethod
    def empty(cls) -> Keychain:
        return cls()

    @classmethod
    def from_feature_points(cls, entries: Sequence[KeychainFeaturePoint]) -> Keychain:
        kc = cls()
        for entry in entries:
            iv = base64.b64decode(entry.aes_iv)
            key = base64.b64decode(entry.aes_key)
            kc._map[entry.feature_point] = (iv, key)
        return kc

    def get(self, fp: int) -> tuple[bytes, bytes] | None:
        """Get (iv, key) for a feature point, or None."""
        return self._map.get(fp)

    def update_iv(self, fp: int, iv: bytes) -> None:
        """Update IV for a feature point (IV chaining after decryption)."""
        if fp in self._map:
            self._map[fp] = (iv, self._map[fp][1])
