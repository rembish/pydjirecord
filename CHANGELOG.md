# Changelog

All notable changes to this project will be documented in this file.

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
