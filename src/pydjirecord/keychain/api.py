"""DJI keychain API client."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from ..error import ApiError, ApiKeyError
from .feature_point import FeaturePoint

_ENDPOINT = "https://dev.dji.com/openapi/v1/flight-records/keychains"
_TIMEOUT = 30.0


@dataclass
class EncodedKeychainFeaturePoint:
    """Encoded (encrypted) feature point data from KeyStorage records."""

    feature_point: int
    aes_ciphertext: str  # base64-encoded

    def to_dict(self) -> dict[str, Any]:
        fp = FeaturePoint(self.feature_point)
        return {
            "featurePoint": fp.api_name,
            "aesCiphertext": self.aes_ciphertext,
        }


@dataclass
class KeychainFeaturePoint:
    """Decoded feature point with AES key and IV."""

    feature_point: int
    aes_key: str  # base64-encoded
    aes_iv: str  # base64-encoded


@dataclass
class KeychainsRequest:
    """Request body for the DJI keychains API."""

    version: int = 0
    department: int = 3  # Default: DJIFly
    keychains: list[list[EncodedKeychainFeaturePoint]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "department": self.department,
            "keychainsArray": [[fp.to_dict() for fp in group] for group in self.keychains],
        }

    def fetch(self, api_key: str) -> list[list[KeychainFeaturePoint]]:
        """Fetch decoded keychains from DJI API."""
        body = self.to_dict()
        try:
            resp = httpx.post(
                _ENDPOINT,
                json=body,
                headers={"Api-Key": api_key, "Content-Type": "application/json"},
                timeout=_TIMEOUT,
            )
        except httpx.HTTPError as exc:
            raise ApiError(f"Network error: {exc}") from exc

        if resp.status_code == 403:
            raise ApiKeyError("Invalid DJI API key (403)")
        if resp.status_code != 200:
            raise ApiError(f"DJI API returned status {resp.status_code}: {resp.text}")

        result = resp.json()
        if "result" in result and result["result"].get("code", 0) != 0:
            msg = result["result"].get("msg", "Unknown error")
            raise ApiError(f"DJI API error: {msg}")

        data = result.get("data")
        if data is None:
            return []

        keychains: list[list[KeychainFeaturePoint]] = []
        for group in data:
            kc_group: list[KeychainFeaturePoint] = []
            for entry in group:
                kc_group.append(
                    KeychainFeaturePoint(
                        feature_point=_parse_feature_point_value(entry.get("featurePoint", "")),
                        aes_key=entry.get("aesKey", ""),
                        aes_iv=entry.get("aesIv", ""),
                    )
                )
            keychains.append(kc_group)
        return keychains


def _parse_feature_point_value(name: str) -> int:
    """Parse feature point integer from API name string."""
    # Format: "FR_Standardization_Feature_Base_1"
    try:
        return int(name.rsplit("_", 1)[-1])
    except (ValueError, IndexError):
        return 8  # Plaintext default
