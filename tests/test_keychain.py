"""Tests for keychain and feature point mapping."""

from __future__ import annotations

from pydjirecord.keychain import FeaturePoint, Keychain, feature_point_for_record
from pydjirecord.keychain.api import (
    EncodedKeychainFeaturePoint,
    KeychainFeaturePoint,
    KeychainsRequest,
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
