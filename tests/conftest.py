from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture
def examples_dir() -> Path:
    return EXAMPLES_DIR


@pytest.fixture
def sample_log(examples_dir: Path) -> bytes:
    """Load the smallest example log file as bytes."""
    log_file = examples_dir / "DJIFlightRecord_2021-05-25_[18-31-35].txt"
    return log_file.read_bytes()
