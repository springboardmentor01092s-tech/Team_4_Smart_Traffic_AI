"""
app/dependencies/routes.py

Dependency injection factory for the Routes module.

Constructs RouteService with its three required repositories:
  - RouteRepository   (primary entity access)
  - SegmentRepository (segment existence validation)
  - ReadingRepository (latest readings for /traffic endpoint)

Follows the exact factory pattern used by all existing modules.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.reading_repository import ReadingRepository
from app.repositories.route_repository import RouteRepository
from app.repositories.segment_repository import SegmentRepository
from app.services.route_service import RouteService


async def get_route_service(db: AsyncSession = Depends(get_db)) -> RouteService:
    """DI factory: constructs and returns a fully wired RouteService."""
    return RouteService(
        RouteRepository(db),
        SegmentRepository(db),
        ReadingRepository(db),
    )
