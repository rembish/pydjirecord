# pydjirecord

Python parser for DJI drone flight log files (`.txt` binary format).

Supports all log format versions 1 through 14, including XOR encoding (v7-12) and AES-256-CBC encryption (v13-14) with per-feature-point keys fetched from the DJI API.

## Acknowledgments

This project is a Python rewrite of [dji-log-parser](https://github.com/lvauvillier/dji-log-parser) by [Luc Vauvillier](https://github.com/lvauvillier). The Rust implementation is the authoritative reference for parsing logic, binary layouts, and encryption details. Thank you for the excellent work and for making it open source.

Binary struct layouts and feature-point mappings are cross-referenced against the official DJI C++ parsing library: [dji-sdk/FlightRecordParsingLib](https://github.com/dji-sdk/FlightRecordParsingLib).

## Requirements

- Python 3.10+

## Installation

```bash
pip install pydjirecord
```

To also parse VirtualStick (type 33) records, install the optional protobuf extra:

```bash
pip install 'pydjirecord[proto]'
```

Or from source:

```bash
git clone https://github.com/rembish/pydjirecord.git
cd pydjirecord
make install
```

## CLI Usage

The package installs a `djirecord` command:

```bash
djirecord FILE [--json | --raw | --geojson | --kml | --csv] [-o FILE] [--api-key KEY]
```

### Flight info (default)

With no format flag, prints a human-readable summary. When an API key is available (or the log doesn't need one), frames are decrypted automatically and corrected values are shown for coordinates, distance, photos, and video time:

```bash
djirecord flight.txt                    # header-only for v13+
djirecord flight.txt --api-key KEY      # decrypts frames, shows corrected values
```

```
Log version:  14

Aircraft:     Mavic Air 2
Product type: MAVIC_AIR2
Aircraft SN:  ABC123
...

Flight stats:
  Distance:   4523.1 m
  Duration:   8m 42s
  Max height: 119.8 m
  Frames:     4362

Photos:       62
Video time:   1m 13s
```

### Export formats

```bash
# JSON to stdout (details-only for v13+ without API key)
djirecord flight.txt --json

# JSON with frames to file
djirecord flight.txt --json -o flight.json --api-key YOUR_KEY

# Raw records as JSON
djirecord flight.txt --raw --api-key YOUR_KEY

# GeoJSON track
djirecord flight.txt --geojson -o track.geojson --api-key YOUR_KEY

# KML track
djirecord flight.txt --kml -o track.kml --api-key YOUR_KEY

# CSV telemetry
djirecord flight.txt --csv -o telemetry.csv --api-key YOUR_KEY
```

Format flags are mutually exclusive. Output defaults to stdout (`-o -`).

### API key

Logs version 13 and above use AES-256-CBC encryption. To decrypt them, provide a DJI API key via:

- `--api-key KEY` argument
- `DJI_API_KEY` environment variable
- `.env` file in the current directory

```bash
# .env file
DJI_API_KEY=your_key_here
```

## Library Usage

```python
from pydjirecord import DJILog

# Parse a flight log
data = open("flight.txt", "rb").read()
log = DJILog.from_bytes(data)

# Access flight metadata (no decryption needed)
print(log.version)
print(log.details.aircraft_name)
print(log.details.total_distance)

# Decrypt and iterate frames (v13+ needs keychains from the DJI API)
keychains = log.fetch_keychains("YOUR_API_KEY") if log.version >= 13 else None
frames = log.frames(keychains)

for frame in frames:
    print(frame.osd.latitude, frame.osd.longitude, frame.osd.altitude)
    print(frame.battery.voltage, frame.battery.charge_level, frame.battery.lifetime_remaining)
    print(frame.gimbal.pitch, frame.gimbal.yaw)

# Raw records
records = log.records(keychains)
```

### Accurate flight statistics

Several header fields (`capture_num`, `video_time`, `total_distance`, `latitude`/`longitude`) are unreliable. `FrameDetails` corrects them automatically when you pass decoded frames:

```python
from pydjirecord import DJILog
from pydjirecord.frame.details import FrameDetails

data = open("flight.txt", "rb").read()
log = DJILog.from_bytes(data)
keychains = log.fetch_keychains("YOUR_API_KEY") if log.version >= 13 else None
frames = log.frames(keychains)

# FrameDetails computes all corrected values from frames automatically
details = FrameDetails.from_details(log.details, frames)

print(details.latitude)       # from header, or first valid OSD GPS fix if header is 0,0
print(details.longitude)      # same
print(details.total_distance) # cumulative GPS track length from frames
print(details.photo_num)      # computed from Camera remain_photo_num delta
print(details.video_time)     # computed from Camera record_time segments
```

The individual `compute_*` functions are also available if you need them directly:

```python
from pydjirecord.frame.builder import compute_coordinates, compute_photo_num, compute_video_time

lat, lon = compute_coordinates(frames)                            # first valid GPS fix
distance = frames[-1].osd.cumulative_distance if frames else 0.0  # GPS track length
photos = compute_photo_num(frames)                                # remain_photo_num delta
video_seconds = compute_video_time(frames)                        # sum of record_time segments
```

### Flight anomaly detection

`FrameDetails` automatically classifies flight anomalies when frames are provided:

```python
details = FrameDetails.from_details(log.details, frames)

if details.anomaly and details.anomaly.severity != FlightSeverity.GREEN:
    print(f"Severity: {details.anomaly.severity.name}")
    print(f"Actions:  {[a.name for a in details.anomaly.actions]}")
    print(f"Motor blocked: {details.anomaly.motor_blocked}")
    print(f"Max descent:   {details.anomaly.max_descent_speed:.1f} m/s")
```

Or call the function directly:

```python
from pydjirecord.frame.builder import compute_flight_anomalies
from pydjirecord.frame.anomaly import FlightSeverity

anomaly = compute_flight_anomalies(frames)
if anomaly.severity == FlightSeverity.RED:
    print("Critical flight anomaly detected")
```

Severity levels: **RED** (loss of control, forced landing, motor failure, freefall), **AMBER** (low battery RTH, GPS degradation, negative final altitude), **GREEN** (normal flight).

## Known Limitations

### Header field caveats

The `Details` header block is readable without decryption. Most fields are reliable, but some are not (verified across 585 real flight logs):

| Field | Status | Notes |
|-------|--------|-------|
| `details.latitude` / `details.longitude` | Unreliable | Zero in ~20 % of flights (116 of 585 tested logs) despite being real outdoor flights with GPS. The DJI app fails to write takeoff coordinates to the header. When frames are available, `FrameDetails` falls back to the first valid OSD GPS fix. |
| `details.total_distance` | Approximate | Stored in the binary as kilometres; converted to metres on parse. Matches frame-computed distance within float32 precision in 95%+ of logs. A small number carry stale values from prior flights. The DJI C++ library ignores this field and recomputes from the GPS track. Prefer `frames[-1].osd.cumulative_distance` when decrypted frames are available. |
| `details.max_height` | Reliable | Matches frame-computed maximum within 1-2 m in all tested logs. |
| `details.max_horizontal_speed` | Reliable | Matches frame-computed maximum in all tested logs. |
| `details.capture_num` | Broken | Always 0 for DJI Fly app logs. When frames are available, `FrameDetails.photo_num` is computed from Camera `remain_photo_num` delta and is accurate. |
| `details.video_time` | Unreliable | Not per-flight recording duration. The ratio to actual in-frame recording time ranges from 1x to over 100x with no consistent unit. When frames are available, `FrameDetails.video_time` is computed from Camera `record_time` segments and is accurate. |

### Network access required for decryption

Version 13 and 14 logs use AES-256-CBC encryption. Decryption requires fetching per-flight keys from the DJI API over HTTPS:

```
https://dev.dji.com/...
```

In **air-gapped or network-restricted environments** (corporate firewalls, secured laptops), `log.fetch_keychains()` will raise a network error. In that case:

- `log.details` (the unencrypted header) is still fully readable.
- `log.version`, `log.details.aircraft_name`, `log.details.start_time`, etc. work without a network call.
- `djirecord flight.txt --json` works without a key and returns a details-only JSON object (no frame data).
- Frame-level telemetry and the frame-bearing export formats (`--raw`, `--csv`, `--geojson`, `--kml`, and `--json` with frames) require the decryption keys and will fail without network access.

## Encryption

| Version | Encryption |
|---------|-----------|
| 1-6     | None |
| 7-12    | XOR (CRC64-derived key) |
| 13-14   | XOR + AES-256-CBC (per-feature-point keys from DJI API) |

## Status

The core parsing pipeline, frame builder, and all export formats work. Record types not covered by the upstream binary spec are returned as raw bytes.

**Testing coverage**:

The author has format version 14 logs from Mavic Air 2 and Mini 4 Pro (RC2). Older format versions (v1-12) are tested only through crafted binary data in unit tests, not with real flight logs. **If you have DJI flight logs from older drones or older DJI app versions (format versions 1 through 12), please consider contributing them** — even a single short flight per version would help verify the parsing and decryption paths end-to-end.

## Development

```bash
make install        # create venv and install with dev deps
make check          # format + lint + typecheck + test
make format         # ruff format + autofix
make lint           # ruff check
make typecheck      # mypy strict
make integration    # integration + mutation-regression tests, no coverage floor
make test           # pytest with coverage
make build          # build sdist and wheel into dist/
```

Run tests across all supported Python versions with tox (requires the interpreters to be installed):

```bash
.venv/bin/tox                  # all versions
.venv/bin/tox -e py310,py312   # specific versions
```

Run a single test:

```bash
.venv/bin/pytest tests/test_cli.py::TestJsonOutput -xvs
```

Run integration and mutation-regression tests against a private local corpus
without committing logs into the repo:

```bash
make integration DJI_LOGS_DIR=/path/to/your/logs
```

The `integration` target passes `--no-cov` so partial runs don't trip the
coverage floor. Equivalent manual invocation:

```bash
DJI_LOGS_DIR=/path/to/your/logs .venv/bin/pytest -m integration --no-cov -xvs tests/test_djilog.py tests/test_mutation_regression.py
```

## License

[MIT](LICENSE)
