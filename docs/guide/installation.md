# Installation

## Requirements

- Python 3.10+

## From PyPI

```bash
pip install pydjirecord
```

To also parse VirtualStick (type 33) records, install the optional protobuf extra:

```bash
pip install 'pydjirecord[proto]'
```

## From source

```bash
git clone https://github.com/rembish/pydjirecord.git
cd pydjirecord
make install
```

This creates a virtualenv at `.venv/` and installs the package in editable mode with dev dependencies.
