# CLI usage

The package installs a `djirecord` command:

```bash
djirecord FILE [--json | --raw | --geojson | --kml | --csv | --hardware] [-o FILE] [--api-key KEY] [--no-cache] [--no-verify]
```

## Flight info (default)

With no format flag, prints a human-readable summary. When an API key is available (or the log doesn't need one), frames are decrypted automatically and corrected values are shown:

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

## Export formats

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

## Hardware report

```bash
djirecord flight.txt --hardware --api-key YOUR_KEY
```

```
AIRCRAFT
  Model:          DJI Mini 4 Pro
  Product type:   MINI4_PRO
  Serial:         1581F6Z9C23CP003

CAMERA
  Serial:         6TVQLBJ0M209BS
  SD card:        inserted

REMOTE CONTROLLER
  Serial:         6UZBLCN021016H
  Downlink:       min 0%, avg 80%
  Uplink:         min 1%, avg 85%

BATTERY
  Serial:         7BVPLBVDA104J3
  Design cap:     2590 mAh
  Charge cycles:  3
  Charge:         99% -> 81% (used 18%)
  Temperature:    29.5 - 39.2 C
  Cells:          2, deviation 4 mV

FLIGHT CONTROLLER
  Failsafe:       GO_HOME
  Obstacle avd:   ON
```

Shows aircraft, camera, RC (signal quality, pilot GPS if available), battery health (design capacity, charge cycles, voltage range, cell deviation), firmware versions, flight controller settings, and component serials. Works without an API key (header-only mode) but shows more with decrypted frames.

## Options

**`--no-cache`** skips the local keychain cache and always makes a fresh API call.

**`--no-verify`** disables TLS certificate verification for the DJI API request. Use this if the request fails with a certificate error on your system (e.g. corporate proxies or custom CA stores).

Keychains are cached locally after the first successful fetch, so `--no-verify` is only needed once per unique log file.
