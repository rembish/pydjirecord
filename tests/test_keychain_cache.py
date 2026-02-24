"""Tests for keychain API response caching."""

from __future__ import annotations

import json
import os
import time
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import httpx
import pytest

from pydjirecord.keychain.api import (
    EncodedKeychainFeaturePoint,
    KeychainsRequest,
    _cache_key,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def req() -> KeychainsRequest:
    efp = EncodedKeychainFeaturePoint(feature_point=1, aes_ciphertext="dGVzdA==")
    return KeychainsRequest(version=2, department=3, keychains=[[efp]])


_SAMPLE_DATA = [
    [
        {
            "featurePoint": "FR_Standardization_Feature_Base_1",
            "aesKey": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "aesIv": "AAAAAAAAAAAAAAAAAAAAAA==",
        }
    ]
]


def _api_response(data: object = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"data": data}
    return resp


class TestCacheHit:
    def test_returns_cached_without_http(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, req: KeychainsRequest
    ) -> None:
        # Pre-populate cache
        key = _cache_key(req.to_dict())
        cache_dir = tmp_path / "keychains"
        (cache_dir / f"{key}.json").write_text(json.dumps(_SAMPLE_DATA))

        mock_post = MagicMock()
        monkeypatch.setattr(httpx, "post", mock_post)

        result = req.fetch("key", cache=True)

        mock_post.assert_not_called()
        assert len(result) == 1
        assert result[0][0].feature_point == 1


class TestCacheMiss:
    def test_calls_api_and_writes_cache(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, req: KeychainsRequest
    ) -> None:
        monkeypatch.setattr(httpx, "post", MagicMock(return_value=_api_response(_SAMPLE_DATA)))

        result = req.fetch("key", cache=True)

        assert len(result) == 1
        assert result[0][0].feature_point == 1

        # Verify cache file was written
        key = _cache_key(req.to_dict())
        cache_file = tmp_path / "keychains" / f"{key}.json"
        assert cache_file.exists()
        assert json.loads(cache_file.read_text()) == _SAMPLE_DATA


class TestCorruptCache:
    def test_falls_back_to_api(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, req: KeychainsRequest) -> None:
        # Write corrupt data
        key = _cache_key(req.to_dict())
        cache_dir = tmp_path / "keychains"
        (cache_dir / f"{key}.json").write_text("NOT VALID JSON {{{{")

        monkeypatch.setattr(httpx, "post", MagicMock(return_value=_api_response(_SAMPLE_DATA)))

        result = req.fetch("key", cache=True)

        assert len(result) == 1
        assert result[0][0].feature_point == 1


class TestCacheDisabled:
    def test_bypasses_cache(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, req: KeychainsRequest) -> None:
        # Pre-populate cache
        key = _cache_key(req.to_dict())
        cache_dir = tmp_path / "keychains"
        (cache_dir / f"{key}.json").write_text(json.dumps(_SAMPLE_DATA))

        mock_post = MagicMock(return_value=_api_response(_SAMPLE_DATA))
        monkeypatch.setattr(httpx, "post", mock_post)

        result = req.fetch("key", cache=False)

        mock_post.assert_called_once()
        assert len(result) == 1


class TestCacheExpired:
    def test_expired_cache_calls_api(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, req: KeychainsRequest
    ) -> None:
        # Write cache file and backdate its mtime past the TTL
        key = _cache_key(req.to_dict())
        cache_file = tmp_path / "keychains" / f"{key}.json"
        cache_file.write_text(json.dumps(_SAMPLE_DATA))
        expired_time = time.time() - 31 * 24 * 3600  # 31 days ago
        os.utime(cache_file, (expired_time, expired_time))

        mock_post = MagicMock(return_value=_api_response(_SAMPLE_DATA))
        monkeypatch.setattr(httpx, "post", mock_post)

        result = req.fetch("key", cache=True)

        mock_post.assert_called_once()
        assert len(result) == 1


class TestCacheKey:
    def test_deterministic(self, req: KeychainsRequest) -> None:
        body = req.to_dict()
        assert _cache_key(body) == _cache_key(body)

    def test_different_bodies_different_keys(self) -> None:
        a = {"version": 1, "department": 3, "keychainsArray": []}
        b = {"version": 2, "department": 3, "keychainsArray": []}
        assert _cache_key(a) != _cache_key(b)
