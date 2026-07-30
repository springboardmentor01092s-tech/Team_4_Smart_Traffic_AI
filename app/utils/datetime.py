"""
app/utils/datetime.py

Pure UTC datetime utilities.

No I/O. No framework dependencies. Fully unit-testable.
"""
from datetime import UTC, datetime


def utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


def utc_from_timestamp(ts: float) -> datetime:
    """Convert a Unix timestamp (float) to a timezone-aware UTC datetime."""
    return datetime.fromtimestamp(ts, tz=UTC)
