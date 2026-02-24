# Changelog

All notable changes to this project will be documented in this file.

## [0.7.0] - 2026-02-24

### Added

- `FrameOSD.cumulative_distance` — running GPS track length in metres,
  accumulated by the frame builder using the same Vincenty spherical formula
  as the DJI C++ reference library (`DistanceEarth` / `CoordinateIsValid`).
  A position is counted only when `is_gps_valid` is `True` and
  `gps_level >= 3`.  This is the authoritative distance figure; use it in
  preference to `Details.total_distance`.
- `haversine_distance(lat1, lon1, lat2, lon2)` utility function in
  `pydjirecord.utils` — great-circle distance in metres from decimal-degree
  coordinates, matching `kEarthRadiusKm = 6371 km` from the C++ reference.
- Croatia integration fixture (`examples/DJIFlightRecord_2024-09-01_[14-55-49].txt`,
  v14, 390 KB, 45.47°N 16.39°E) — integration tests now run on every
  checkout instead of being silently skipped.
- `integration` pytest marker registered in `pyproject.toml`; `test_djilog.py`
  documented with instructions for adding further fixtures.

### Fixed

- **CRITICAL**: `aes_decode()` called `cipher.decrypt()` twice on the same
  stateful CBC object when `unpad()` raised `ValueError`, producing corrupted
  plaintext.  Fixed by decrypting once and unpadding the stored result.
- **Final frame always dropped**: the frame builder only appended a frame on
  the arrival of the *next* OSD record, so the last frame was always lost.
  Added an end-of-loop flush.
- **`--raw` silent downgrade**: `--raw` on v13+ without an API key fell
  through to a details-only JSON export instead of exiting with an error.
  Behaviour now matches all other frame-based exports.
- `virtual_stick.py` import block narrowed from bare `except Exception` to
  `except ImportError`.
- README clone URL corrected to `rembish/pydjirecord`; added cross-reference
  to `dji-sdk/FlightRecordParsingLib`; `fetch_keychains` comment updated.

### Changed

- `Details.total_distance` now documented as unreliable (the DJI C++ library
  ignores the header value and recomputes distance from the GPS track).
- `FrameOSD` class docstring clarifies `height` (AGL) vs `altitude`
  (absolute) and the semantics of `cumulative_distance`.
- Integration test `test_details_has_start_time`: `year == 2021` →
  `year >= 2017` so the assertion holds for any real-world log.
- `examples/` removed from `.gitignore`.

## [0.6.5] - 2026-02-24

### Fixed

- **CRITICAL-1**: `aes_decode()` was calling `cipher.decrypt(data)` a second time on the
  already-consumed CBC cipher object when `unpad()` raised `ValueError`, producing corrupted
  plaintext instead of the raw decryption. Fixed by decrypting once, storing the result, and
  unpadding the stored bytes.
- **HIGH-1**: The final telemetry frame was always dropped because frames were appended only
  when the *next* OSD record arrived. Added an end-of-loop flush so every OSD record produces
  exactly one frame.
- **HIGH-2**: `--raw` on v13+ logs without an API key silently fell through to the
  details-only JSON export. `--raw` now consistently requires a key on v13+ and exits with
  an error, matching the behaviour of all other frame-based exports.
- **MEDIUM-1**: `virtual_stick.py` caught all exceptions during protobuf import, hiding
  real runtime errors. Narrowed to `ImportError` only.
- **LOW-1**: README clone URL corrected to `https://github.com/rembish/pydjirecord.git`;
  `fetch_keychains` code comment updated to show `if log.version >= 13 else None`.

### Added

- README: cross-reference to [dji-sdk/FlightRecordParsingLib](https://github.com/dji-sdk/FlightRecordParsingLib)
  as the official DJI C++ source of truth for binary layouts and feature-point mappings.
- `tests/test_decoder.py`: `TestAesDecode.test_padding_error_returns_raw_decrypt` — regression
  test ensuring the CRITICAL-1 fix holds (padding-error fallback returns the single decrypt
  result, not a re-decrypted garbage value).
- `tests/test_cli.py`: `--raw` added to the `TestExportsRequireApiKey` parametrised check so
  v13+ raw export without a key is asserted to exit 1.
- `tests/test_djilog.py`: `pytestmark = pytest.mark.integration` and module-level docstring
  explaining how to populate the `examples/` directory.
- `pyproject.toml`: `integration` marker registered under `[tool.pytest.ini_options]`.

## [0.6.4] - 2026-02-24

### Added

- `.github/workflows/ci.yml` — GitHub Actions CI with three jobs:
  - **checks**: ruff format + lint, mypy strict (Python 3.12)
  - **test**: tox matrix across Python 3.10–3.14 (`fail-fast: false`,
    `allow-prereleases: true` for 3.14)
  - **build**: sdist + wheel via `python -m build`, artifacts uploaded;
    PyPI publish step stubbed out with a TODO for when the account is recovered
- `[tool.tox]` config in `pyproject.toml` (`envlist = py310..py314`,
  `isolated_build = true`, installs `[proto]` extras so VirtualStick tests run)
- `tox>=4.0` added to `[dev]` optional dependencies

## [0.6.3] - 2026-02-24

### Changed

- Lower `requires-python` from `>=3.12` to `>=3.10` — the code uses no 3.11/3.12-only
  features; the binding constraint is `python-dotenv>=1.0` which requires 3.9, and
  Python 3.9 is already EOL, making 3.10 the sensible floor
- Replace `from datetime import UTC` (3.11+) with `timezone.utc` in
  `record/custom.py`, `frame/custom.py`, and `layout/details.py`
- Update ruff `target-version` and mypy `python_version` to `py310` / `3.10`
- Dependency minimums (`httpx>=0.27`, `pycryptodome>=3.20`, `python-dotenv>=1.0`)
  are all justified and unchanged

## [0.6.2] - 2026-02-24

### Changed

- README Status section cleaned up: removed stale TODOs for record types and CLI
  features that have since been implemented or lack upstream documentation
- Drop `setuptools-scm` from build-system requirements (unused; static version is
  set directly in `pyproject.toml`)
- Add `build>=1.0` to `[dev]` optional dependencies so `make build` works out of
  the box after `make install`

## [0.6.1] - 2026-02-24

### Changed

- `virtual_stick_pb2.py` is now generated from `src/pydjirecord/proto/virtual_stick.proto`
  (the canonical `.proto` definition); the hand-rolled `descriptor_pb2` boilerplate has
  been removed. Regenerate with `grpcio-tools` after editing the `.proto` file.
- `[proto]` optional dependency tightened to `protobuf>=6.0` (generated code requires
  a 6.x runtime)
- `grpcio-tools>=1.60` added to `[dev]` optional dependencies for proto regeneration

## [0.6.0] - 2026-02-24

### Added

- Record type 33 (`VirtualStick`) parser — decodes the protobuf-encoded
  `VirtualStickFlightControlData` message (pitch, roll, yaw, verticalThrottle as
  floats; verticalControlMode, rollPitchControlMode, yawControlMode,
  rollPitchCoordinateSystem as int32). Requires the optional `protobuf` extra
  (`pip install 'pydjirecord[proto]'`); without it, type 33 records are returned
  as raw bytes.
- `[proto]` optional dependency group in `pyproject.toml` (`protobuf>=4.21`)

## [0.5.0] - 2026-02-24

### Added

- Record type 11 (`RCGPS`) parser — `dji_rc_gps_info_push` struct (30 bytes):
  latitude/longitude (int32 × 1e-7 → degrees), velocity X/Y (raw int32),
  satellite count, accuracy, validity flags, and embedded timestamp
- CLI flags `--api-custom-department INT` and `--api-custom-version INT` to
  override the department and version sent to the DJI keychain API

## [0.4.0] - 2026-02-24

### Fixed

- Feature point mapping bugs verified against C++ `flight_record_feature_point_map.cpp`:
  - Type 49 (`AgricultureOFDMRadioSignalPush`) now maps to `AIR_LINK` instead of `AGRICULTURE`
  - Type 45 (`RTKDifferenceDataType`) now maps to `AGRICULTURE` instead of `RC`
  - Type 53 (`FlightHubInfoDataType`) now maps to `FLIGHT_HUB` in all versions instead of `FLY_SAFE`/`AFTER_SALES`
  - Types 11, 29, 33 now map to `BASE` for v13 logs (previously fell through to `PLAINTEXT`, breaking AES decryption)
  - Type 40 (`HealthGroupDataType`) now correctly maps to `BASE` (was shadowed by `AFTER_SALES`)
- Record type 6 renamed from `"Deform"` to `"MCTripodState"` to match C++ enum name

### Changed

- Test fixtures no longer depend on a personal example file; a minimal valid v14 binary is now generated programmatically in `tests/fixtures/`

## [0.3.0] - 2026-02-23

### Added

- New record types: AppGPS (14), Firmware (15), MCParams (19), ComponentSerial (40)
- Missing bitfield extractions in SmartBattery: `low_warning_go_home`, `serious_low_warning_landing`
- Missing field in Home: `aircraft_head_direction`
- Derived horizontal speed fields in frame OSD: `h_speed`, `h_speed_max`
- `OSD.hSpeed` and `OSD.hSpeedMax` columns in CSV export
- Tests for all new record types and fields

## [0.2.1] - 2026-02-23

### Fixed

- Frame builder bugs identified from upstream issues
- Added `python-dotenv` as a runtime dependency

## [0.2.0] - 2026-02-23

### Changed

- Renamed CLI entry point to `djirecord`
- Redesigned format/output CLI arguments
- Added `.env` file support for `DJI_API_KEY`

### Added

- README and MIT LICENSE

## [0.1.0] - 2026-02-23

### Added

- Initial release: DJI flight log parser library and CLI
- Binary format parsing for versions 1-14
- XOR and AES-256-CBC decryption
- 20+ record types (OSD, Home, Gimbal, RC, Battery, Camera, etc.)
- Frame builder with normalized output
- JSON, CSV, GeoJSON, KML export formats
- Keychain API integration for v13+ logs
