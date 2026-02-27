# pydjirecord

Python parser for DJI drone flight log files (`.txt` binary format).

Supports all log format versions 1 through 14, including XOR encoding (v7–12) and AES-256-CBC encryption (v13–14) with per-feature-point keys fetched from the DJI API.

## Quick start

```bash
pip install pydjirecord
```

```python
from pydjirecord import DJILog

log = DJILog.from_bytes(open("flight.txt", "rb").read())
print(log.details.aircraft_name, log.details.total_distance)
```

See the [Installation](guide/installation.md) guide for more options and the [Library usage](guide/library.md) guide for detailed examples.

## CLI

```bash
djirecord flight.txt --json -o flight.json --api-key YOUR_KEY
```

See [CLI usage](guide/cli.md) for all export formats.

## Links

- [GitHub repository](https://github.com/rembish/pydjirecord)
- [PyPI package](https://pypi.org/project/pydjirecord/)
- [API Reference](api/djilog.md)
