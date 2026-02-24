"""Helpers for discovering local DJI sample logs for tests."""

from __future__ import annotations

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_EXAMPLES_DIR = _REPO_ROOT / "examples"
_PATTERN = "DJIFlightRecord_*.txt"


def discover_log_files() -> list[Path]:
    """Discover DJI sample logs.

    Resolution order:
    1. ``$DJI_LOGS_DIR`` if set and contains matching files.
    2. Repository ``examples/`` directory.
    """
    custom_dir = os.environ.get("DJI_LOGS_DIR")
    if custom_dir:
        custom_files = sorted(Path(custom_dir).expanduser().glob(_PATTERN))
        if custom_files:
            return custom_files

    return sorted(_DEFAULT_EXAMPLES_DIR.glob(_PATTERN))
