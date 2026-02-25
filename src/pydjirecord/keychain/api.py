"""DJI keychain API client."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from ..error import ApiError, ApiKeyError
from .feature_point import FeaturePoint

_ENDPOINT = "https://dev.dji.com/openapi/v1/flight-records/keychains"
_TIMEOUT = 30.0
_CACHE_TTL = 30 * 24 * 3600  # 30 days in seconds
_CACHE_MAX_ENTRIES = 2048

_log = logging.getLogger(__name__)


def _cache_dir() -> Path:
    """Return the keychain cache directory, creating it if needed."""
    base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    d = base / "pydjirecord" / "keychains"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_key(body: dict[str, Any]) -> str:
    """Compute SHA-256 hex digest of the canonical JSON request body."""
    raw = json.dumps(body, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()


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

    def fetch(self, api_key: str, *, cache: bool = True, verify: bool = True) -> list[list[KeychainFeaturePoint]]:
        """Fetch decoded keychains from DJI API.

        When *cache* is ``True`` (default), responses are cached locally
        under ``$XDG_CACHE_HOME/pydjirecord/keychains/`` so that
        repeated parses of the same log file skip the network round-trip.

        Raises :class:`ApiKeyError` if *api_key* is ``None`` or empty.
        """
        if not api_key:
            raise ApiKeyError("DJI API key is required for v13+ log decryption")
        body = self.to_dict()
        key = _cache_key(body)

        # Try reading from cache
        if cache:
            try:
                cache_file = _cache_dir() / f"{key}.json"
                age = time.time() - cache_file.stat().st_mtime
                if age < _CACHE_TTL:
                    data = json.loads(cache_file.read_text(encoding="utf-8"))
                    _log.debug("keychain cache hit: %s", key[:12])
                    return _parse_data(data)
                _log.debug("keychain cache expired: %s", key[:12])
            except Exception:
                pass  # cache miss or corrupt — fall through to API

        # API call
        try:
            resp = httpx.post(
                _ENDPOINT,
                json=body,
                headers={"Api-Key": api_key, "Content-Type": "application/json"},
                timeout=_TIMEOUT,
                verify=verify,
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

        # Write to cache
        if cache:
            try:
                cache_path = _cache_dir() / f"{key}.json"
                cache_path.write_text(json.dumps(data), encoding="utf-8")
                _log.debug("keychain cache write: %s", key[:12])
                _evict_cache(cache_path.parent)
            except Exception:
                _log.debug("keychain cache write failed: %s", key[:12])

        return _parse_data(data)


def _evict_cache(cache_dir: Path) -> None:
    """Remove expired entries and cap total cache size."""
    try:
        entries = sorted(cache_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
    except OSError:
        return

    now = time.time()
    remaining: list[Path] = []
    for p in entries:
        try:
            if now - p.stat().st_mtime >= _CACHE_TTL:
                p.unlink()
                _log.debug("keychain cache evict (expired): %s", p.name[:12])
            else:
                remaining.append(p)
        except OSError:
            pass

    # LRU cap: remove oldest entries beyond the limit
    over = len(remaining) - _CACHE_MAX_ENTRIES
    if over > 0:
        for p in remaining[:over]:
            try:
                p.unlink()
                _log.debug("keychain cache evict (lru): %s", p.name[:12])
            except OSError:
                pass


def _parse_data(data: object) -> list[list[KeychainFeaturePoint]]:
    """Convert raw API ``data`` array into :class:`KeychainFeaturePoint` lists.

    Expects ``list[list[dict[str, str]]]``.  Raises :class:`ApiError` if the
    payload shape does not match.
    """
    if not isinstance(data, list):
        raise ApiError(f"Unexpected API data type: expected list, got {type(data).__name__}")
    keychains: list[list[KeychainFeaturePoint]] = []
    for group in data:
        if not isinstance(group, list):
            raise ApiError(f"Unexpected keychain group type: expected list, got {type(group).__name__}")
        kc_group: list[KeychainFeaturePoint] = []
        for entry in group:
            if not isinstance(entry, dict):
                raise ApiError(f"Unexpected keychain entry type: expected dict, got {type(entry).__name__}")
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
