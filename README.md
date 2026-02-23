# pydjirecord

Python parser for DJI drone flight log files (`.txt` binary format).

Supports all log format versions 1 through 14, including XOR encoding (v7-12) and AES-256-CBC encryption (v13-14) with per-feature-point keys fetched from the DJI API.

## Acknowledgments

This project is a Python rewrite of [dji-log-parser](https://github.com/lvauvillier/dji-log-parser) by [Luc Vauvillier](https://github.com/lvauvillier). The Rust implementation is the authoritative reference for parsing logic, binary layouts, and encryption details. Thank you for the excellent work and for making it open source.

## Requirements

- Python 3.12+

## Installation

```bash
pip install pydjirecord
```

Or from source:

```bash
git clone https://github.com/example/pydjirecord.git
cd pydjirecord
make install
```

## CLI Usage

The package installs a `djirecord` command:

```bash
djirecord FILE [--json | --raw | --geojson | --kml | --csv] [-o FILE] [--api-key KEY]
```

### Flight info (default)

With no format flag, prints a human-readable summary:

```bash
djirecord flight.txt
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

# Decrypt and iterate frames (v13+ needs keychains)
keychains = log.fetch_keychains("YOUR_API_KEY")  # None for v1-12
frames = log.frames(keychains)

for frame in frames:
    print(frame.osd.latitude, frame.osd.longitude, frame.osd.altitude)
    print(frame.battery.voltage, frame.battery.charge_level)
    print(frame.gimbal.pitch, frame.gimbal.yaw)

# Raw records
records = log.records(keychains)
```

## Encryption

| Version | Encryption |
|---------|-----------|
| 1-6     | None |
| 7-12    | XOR (CRC64-derived key) |
| 13-14   | XOR + AES-256-CBC (per-feature-point keys from DJI API) |

## Development

```bash
make install        # create venv and install with dev deps
make check          # format + lint + typecheck + test
make format         # ruff format + autofix
make lint           # ruff check
make typecheck      # mypy strict
make test           # pytest with coverage
```

Run a single test:

```bash
.venv/bin/pytest tests/test_cli.py::TestJsonOutput -xvs
```

## License

[MIT](LICENSE)
