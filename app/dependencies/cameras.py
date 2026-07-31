"""
app/dependencies/cameras.py

FastAPI Depends() factory for CameraService.

Pattern mirrors app/dependencies/auth.py exactly:
  - One function per service.
  - Accepts db: AsyncSession = Depends(get_db).
  - Constructs and returns the service with its repository injected.
  - No business logic here.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.camera_repository import CameraRepository
from app.services.camera_service import CameraService


def get_camera_service(db: AsyncSession = Depends(get_db)) -> CameraService:
    """
    FastAPI dependency that constructs a CameraService for the current request.

    Injects:
      - CameraRepository(db) as the sole repository dependency.

    Usage in a router:
        @router.get("/cameras")
        async def list_cameras(service: CameraService = Depends(get_camera_service)):
            ...
    """
    return CameraService(CameraRepository(db))
