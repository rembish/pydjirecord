"""Exception hierarchy for pydjirecord."""


class DJILogError(Exception):
    """Base exception for pydjirecord."""


class ParseError(DJILogError):
    """Error parsing binary data."""


class MissingAuxiliaryDataError(DJILogError):
    """Required auxiliary block not found."""

    def __init__(self, block_type: str) -> None:
        super().__init__(f"Missing auxiliary data: {block_type}")
        self.block_type = block_type


class KeychainRequiredError(DJILogError):
    """Keychains required for v13+ logs."""


class ApiKeyError(DJILogError):
    """Invalid DJI API key."""


class ApiError(DJILogError):
    """DJI API returned an error."""
