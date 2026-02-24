"""Tests for keychain and feature point mapping."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from pydjirecord.error import ApiError, ApiKeyError
from pydjirecord.keychain import FeaturePoint, Keychain, feature_point_for_record
from pydjirecord.keychain.api import (
    EncodedKeychainFeaturePoint,
    KeychainFeaturePoint,
    KeychainsRequest,
    _parse_feature_point_value,
)


class TestFeaturePointMapping:
    def test_osd_maps_to_base(self) -> None:
        assert feature_point_for_record(1, 13) == FeaturePoint.BASE
        assert feature_point_for_record(1, 14) == FeaturePoint.BASE

    def test_gimbal_v13_base_v14_gimbal(self) -> None:
        assert feature_point_for_record(3, 13) == FeaturePoint.BASE
        assert feature_point_for_record(3, 14) == FeaturePoint.GIMBAL

    def test_rc_v13_base_v14_rc(self) -> None:
        assert feature_point_for_record(4, 13) == FeaturePoint.BASE
        assert feature_point_for_record(4, 14) == FeaturePoint.RC

    def test_camera_v13_base_v14_camera(self) -> None:
        assert feature_point_for_record(25, 13) == FeaturePoint.BASE
        assert feature_point_for_record(25, 14) == FeaturePoint.CAMERA

    def test_battery_v13_base_v14_battery(self) -> None:
        assert feature_point_for_record(7, 13) == FeaturePoint.BASE
        assert feature_point_for_record(7, 14) == FeaturePoint.BATTERY

    def test_keystorage_plaintext(self) -> None:
        assert feature_point_for_record(56, 14) == FeaturePoint.PLAINTEXT
        assert feature_point_for_record(50, 14) == FeaturePoint.PLAINTEXT

    def test_app_tip_dji_fly_custom(self) -> None:
        assert feature_point_for_record(9, 14) == FeaturePoint.DJI_FLY_CUSTOM
        assert feature_point_for_record(10, 14) == FeaturePoint.DJI_FLY_CUSTOM

    # Bug fixes verified against C++ flight_record_feature_point_map.cpp

    def test_type49_airlink_not_agriculture(self) -> None:
        """AgricultureOFDMRadioSignalPush(49) → AirLinkFeature in both versions."""
        assert feature_point_for_record(49, 13) == FeaturePoint.AIR_LINK
        assert feature_point_for_record(49, 14) == FeaturePoint.AIR_LINK

    def test_type45_agriculture_not_rc(self) -> None:
        """RTKDifferenceDataType(45) → AgricultureFeature in both versions."""
        assert feature_point_for_record(45, 13) == FeaturePoint.AGRICULTURE
        assert feature_point_for_record(45, 14) == FeaturePoint.AGRICULTURE

    def test_type53_flight_hub(self) -> None:
        """FlightHubInfoDataType(53) → FlightHubFeature in both versions."""
        assert feature_point_for_record(53, 13) == FeaturePoint.FLIGHT_HUB
        assert feature_point_for_record(53, 14) == FeaturePoint.FLIGHT_HUB

    def test_type11_v13_base_v14_rc(self) -> None:
        """RCPushGPSFlightRecordDataType(11): v13→Base, v14→RC."""
        assert feature_point_for_record(11, 13) == FeaturePoint.BASE
        assert feature_point_for_record(11, 14) == FeaturePoint.RC

    def test_type29_v13_base_v14_rc(self) -> None:
        """AppSpecialControlJoyStickDataType(29): v13→Base, v14→RC."""
        assert feature_point_for_record(29, 13) == FeaturePoint.BASE
        assert feature_point_for_record(29, 14) == FeaturePoint.RC

    def test_type33_v13_base_v14_rc(self) -> None:
        """AppVirtualStickDataType(33): v13→Base, v14→RC."""
        assert feature_point_for_record(33, 13) == FeaturePoint.BASE
        assert feature_point_for_record(33, 14) == FeaturePoint.RC

    def test_type40_base_not_after_sales(self) -> None:
        """HealthGroupDataType(40) → BaseFeature in both versions."""
        assert feature_point_for_record(40, 13) == FeaturePoint.BASE
        assert feature_point_for_record(40, 14) == FeaturePoint.BASE


class TestFeaturePointEnum:
    def test_known_values(self) -> None:
        assert FeaturePoint.BASE == 1
        assert FeaturePoint.PLAINTEXT == 8
        assert FeaturePoint.SECURITY == 15

    def test_api_name(self) -> None:
        assert "Base" in FeaturePoint.BASE.api_name
        assert "Plaintext" in FeaturePoint.PLAINTEXT.api_name

    def test_unknown_value(self) -> None:
        fp = FeaturePoint(99)
        assert fp.value == 99
        assert "UNKNOWN" in fp.name


class TestKeychain:
    def test_empty(self) -> None:
        kc = Keychain.empty()
        assert kc.get(1) is None

    def test_from_feature_points(self) -> None:
        import base64

        key = base64.b64encode(b"\x00" * 32).decode()
        iv = base64.b64encode(b"\x00" * 16).decode()
        fps = [KeychainFeaturePoint(feature_point=1, aes_key=key, aes_iv=iv)]
        kc = Keychain.from_feature_points(fps)
        assert kc.get(1) is not None
        result_iv, result_key = kc.get(1)
        assert len(result_key) == 32
        assert len(result_iv) == 16

    def test_update_iv(self) -> None:
        import base64

        key = base64.b64encode(b"\x00" * 32).decode()
        iv = base64.b64encode(b"\x00" * 16).decode()
        fps = [KeychainFeaturePoint(feature_point=1, aes_key=key, aes_iv=iv)]
        kc = Keychain.from_feature_points(fps)
        new_iv = b"\xff" * 16
        kc.update_iv(1, new_iv)
        result_iv, result_key = kc.get(1)
        assert result_iv == new_iv
        assert result_key == b"\x00" * 32


class TestApiSerialization:
    def test_encoded_feature_point_field_names(self) -> None:
        """Ensure JSON field names match the DJI API contract."""
        efp = EncodedKeychainFeaturePoint(feature_point=1, aes_ciphertext="dGVzdA==")
        d = efp.to_dict()
        assert "featurePoint" in d
        assert "aesCiphertext" in d
        assert d["featurePoint"] == "FR_Standardization_Feature_Base_1"
        assert d["aesCiphertext"] == "dGVzdA=="

    def test_keychains_request_structure(self) -> None:
        efp = EncodedKeychainFeaturePoint(feature_point=8, aes_ciphertext="YWJj")
        req = KeychainsRequest(version=2, department=3, keychains=[[efp]])
        body = req.to_dict()
        assert body["version"] == 2
        assert body["department"] == 3
        assert "keychainsArray" in body
        assert len(body["keychainsArray"]) == 1
        assert body["keychainsArray"][0][0]["aesCiphertext"] == "YWJj"


# ---------------------------------------------------------------------------
# _parse_feature_point_value
# ---------------------------------------------------------------------------


class TestParseFeaturePointValue:
    def test_standard_name_returns_trailing_int(self) -> None:
        assert _parse_feature_point_value("FR_Standardization_Feature_Base_1") == 1

    def test_unknown_suffix_returns_plaintext_default(self) -> None:
        assert _parse_feature_point_value("no_number_here_xyz") == 8

    def test_empty_string_returns_plaintext_default(self) -> None:
        assert _parse_feature_point_value("") == 8


# ---------------------------------------------------------------------------
# KeychainsRequest.fetch  (httpx monkeypatched — no real network calls)
# ---------------------------------------------------------------------------


def _mock_response(status_code: int, json_data: object = None, text: str = "") -> MagicMock:
    """Build a minimal httpx.Response-like mock."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.text = text
    return resp


class TestFetch:
    @pytest.fixture()
    def req(self) -> KeychainsRequest:
        efp = EncodedKeychainFeaturePoint(feature_point=1, aes_ciphertext="dGVzdA==")
        return KeychainsRequest(version=2, department=3, keychains=[[efp]])

    def test_http_error_raises_api_error(self, monkeypatch: pytest.MonkeyPatch, req: KeychainsRequest) -> None:
        monkeypatch.setattr(httpx, "post", MagicMock(side_effect=httpx.ConnectError("timeout")))
        with pytest.raises(ApiError, match="Network error"):
            req.fetch("key")

    def test_403_raises_api_key_error(self, monkeypatch: pytest.MonkeyPatch, req: KeychainsRequest) -> None:
        monkeypatch.setattr(httpx, "post", MagicMock(return_value=_mock_response(403)))
        with pytest.raises(ApiKeyError):
            req.fetch("key")

    def test_non_200_raises_api_error(self, monkeypatch: pytest.MonkeyPatch, req: KeychainsRequest) -> None:
        monkeypatch.setattr(httpx, "post", MagicMock(return_value=_mock_response(500, text="oops")))
        with pytest.raises(ApiError, match="500"):
            req.fetch("key")

    def test_result_code_nonzero_raises_api_error(self, monkeypatch: pytest.MonkeyPatch, req: KeychainsRequest) -> None:
        body = {"result": {"code": 1, "msg": "bad key"}, "data": None}
        monkeypatch.setattr(httpx, "post", MagicMock(return_value=_mock_response(200, body)))
        with pytest.raises(ApiError, match="bad key"):
            req.fetch("key")

    def test_missing_data_returns_empty(self, monkeypatch: pytest.MonkeyPatch, req: KeychainsRequest) -> None:
        body: dict = {"data": None}
        monkeypatch.setattr(httpx, "post", MagicMock(return_value=_mock_response(200, body)))
        assert req.fetch("key") == []

    def test_success_parses_keychains(self, monkeypatch: pytest.MonkeyPatch, req: KeychainsRequest) -> None:
        body = {
            "data": [
                [
                    {
                        "featurePoint": "FR_Standardization_Feature_Base_1",
                        "aesKey": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
                        "aesIv": "AAAAAAAAAAAAAAAAAAAAAA==",
                    }
                ]
            ]
        }
        monkeypatch.setattr(httpx, "post", MagicMock(return_value=_mock_response(200, body)))
        result = req.fetch("key")
        assert len(result) == 1
        assert len(result[0]) == 1
        assert result[0][0].feature_point == 1
        assert result[0][0].aes_key == "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
