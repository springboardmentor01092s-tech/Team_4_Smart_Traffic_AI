"""
app/models/__init__.py

Import all ORM models here so that Alembic's env.py can discover them
via Base.metadata when generating migration scripts.

Backend Developer #2: Add your model imports here when you create new tables.
Example:
    from app.models.traffic import TrafficCamera  # noqa: F401
    from app.models.alert import Alert  # noqa: F401
"""

from app.models.user import User, UserRole  # noqa: F401

# ── Business modules (Backend Developer #2) ───────────────────────────────────
from app.models.camera import CameraStatus, TrafficCamera  # noqa: F401
from app.models.segment import SegmentStatus, TrafficSegment  # noqa: F401
from app.models.reading import TrafficReading  # noqa: F401

__all__ = ["User", "UserRole", "TrafficCamera", "CameraStatus", "TrafficSegment", "SegmentStatus", "TrafficReading"]
