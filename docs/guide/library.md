# Library usage

## Basic parsing

```python
from pydjirecord import DJILog

# Parse a flight log
data = open("flight.txt", "rb").read()
log = DJILog.from_bytes(data)

# Access flight metadata (no decryption needed)
print(log.version)
print(log.details.aircraft_name)
print(log.details.total_distance)
```

## Decrypting frames

Version 13+ logs require AES keys fetched from the DJI API:

```python
# Decrypt and iterate frames (v13+ needs keychains from the DJI API)
keychains = log.fetch_keychains("YOUR_API_KEY") if log.version >= 13 else None
# Pass verify=False if you get a TLS certificate error:
# keychains = log.fetch_keychains("YOUR_API_KEY", verify=False)
frames = log.frames(keychains)

for frame in frames:
    print(frame.osd.latitude, frame.osd.longitude, frame.osd.altitude)
    print(frame.battery.voltage, frame.battery.charge_level, frame.battery.lifetime_remaining)
    print(frame.gimbal.pitch, frame.gimbal.yaw)
```

## Raw records

```python
records = log.records(keychains)
```

## Accurate flight statistics

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

## Flight anomaly detection

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
