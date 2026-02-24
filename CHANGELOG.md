# Changelog

All notable changes to this project will be documented in this file.

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
