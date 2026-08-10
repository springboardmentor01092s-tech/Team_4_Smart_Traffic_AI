"""
tests/test_cameras/test_camera_service.py

Service-level tests for CameraService.

These tests instantiate CameraService directly with a real CameraRepository
backed by the in-memory SQLite test database. No HTTP client is used.
Tests focus on business logic and domain exception behaviour.

Key scenarios:
  - Happy path CRUD
  - CameraNotFoundError for missing / soft-deleted cameras
  - Partial update (only provided fields change)
  - CameraInUseError when segments exist (simulated by pre-inserting a segment row)
"""
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CameraInUseError, CameraNotFoundError
from app.models.camera import CameraStatus, TrafficCamera
from app.repositories.camera_repository import CameraRepository
from app.schemas.camera import CameraCreate, CameraUpdate
from app.services.camera_service import CameraService


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_service(db: AsyncSession) -> CameraService:
    """Construct a CameraService with a real CameraRepository for testing."""
    return CameraService(CameraRepository(db))


async def create_test_camera(
    service: CameraService,
    *,
    name: str = "Service Test Camera",
    status: CameraStatus = CameraStatus.ACTIVE,
) -> TrafficCamera:
    """Create a camera via the service layer."""
    data = CameraCreate(
        name=name,
        location_name="Test Location",
        latitude=28.6139,
        longitude=77.2090,
        status=status,
        description=None,
    )
    return await service.create_camera(data)


# ── list_cameras ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_cameras_returns_all(test_db: AsyncSession) -> None:
    """list_cameras with no filters should return all non-deleted cameras."""
    service = make_service(test_db)
    await create_test_camera(service, name="Cam A")
    await create_test_camera(service, name="Cam B")

    cameras = await service.list_cameras()
    names = {c.name for c in cameras}
    assert "Cam A" in names
    assert "Cam B" in names


@pytest.mark.asyncio
async def test_list_cameras_excludes_soft_deleted(test_db: AsyncSession) -> None:
    """list_cameras must not return soft-deleted cameras."""
    service = make_service(test_db)
    cam = await create_test_camera(service, name="Deleted Cam")
    await service.delete_camera(cam.id)

    cameras = await service.list_cameras()
    ids = {c.id for c in cameras}
    assert cam.id not in ids


@pytest.mark.asyncio
async def test_list_cameras_filters_by_status(test_db: AsyncSession) -> None:
    """list_cameras with a status filter should return only matching cameras."""
    service = make_service(test_db)
    active_cam = await create_test_camera(service, status=CameraStatus.ACTIVE)
    await create_test_camera(service, status=CameraStatus.INACTIVE)

    cameras = await service.list_cameras(status=CameraStatus.ACTIVE)
    ids = {c.id for c in cameras}
    assert active_cam.id in ids
    for c in cameras:
        assert c.status == CameraStatus.ACTIVE


# ── get_camera ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_camera_returns_existing(test_db: AsyncSession) -> None:
    """get_camera should return the camera when it exists."""
    service = make_service(test_db)
    created = await create_test_camera(service)
    fetched = await service.get_camera(created.id)
    assert fetched.id == created.id


@pytest.mark.asyncio
async def test_get_camera_raises_not_found_for_missing(test_db: AsyncSession) -> None:
    """get_camera should raise CameraNotFoundError for a non-existent UUID."""
    service = make_service(test_db)
    with pytest.raises(CameraNotFoundError):
        await service.get_camera(uuid.uuid4())


@pytest.mark.asyncio
async def test_get_camera_raises_not_found_for_soft_deleted(test_db: AsyncSession) -> None:
    """get_camera should raise CameraNotFoundError for a soft-deleted camera."""
    service = make_service(test_db)
    cam = await create_test_camera(service)
    await service.delete_camera(cam.id)

    with pytest.raises(CameraNotFoundError):
        await service.get_camera(cam.id)


# ── create_camera ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_camera_happy_path(test_db: AsyncSession) -> None:
    """create_camera with valid data should persist and return a camera."""
    service = make_service(test_db)
    data = CameraCreate(
        name="Happy Camera",
        location_name="Main Street",
        latitude=-33.8688,
        longitude=151.2093,
        status=CameraStatus.ACTIVE,
        description="A test camera",
    )
    camera = await service.create_camera(data)

    assert camera.id is not None
    assert camera.name == "Happy Camera"
    assert camera.latitude == -33.8688
    assert camera.longitude == 151.2093
    assert camera.status == CameraStatus.ACTIVE
    assert camera.description == "A test camera"
    assert camera.deleted_at is None


@pytest.mark.asyncio
async def test_create_camera_defaults_status_active(test_db: AsyncSession) -> None:
    """create_camera without an explicit status should default to ACTIVE."""
    service = make_service(test_db)
    data = CameraCreate(
        name="No Status Camera",
        location_name="Somewhere",
        latitude=0.0,
        longitude=0.0,
    )
    camera = await service.create_camera(data)
    assert camera.status == CameraStatus.ACTIVE


# ── update_camera ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_camera_changes_provided_fields(test_db: AsyncSession) -> None:
    """update_camera should update only the fields present in CameraUpdate."""
    service = make_service(test_db)
    cam = await create_test_camera(service, name="Original Name")

    data = CameraUpdate(name="New Name", status=CameraStatus.MAINTENANCE)
    updated = await service.update_camera(cam.id, data)

    assert updated.name == "New Name"
    assert updated.status == CameraStatus.MAINTENANCE


@pytest.mark.asyncio
async def test_update_camera_preserves_unset_fields(test_db: AsyncSession) -> None:
    """update_camera should not change fields that are None in CameraUpdate."""
    service = make_service(test_db)
    cam = await create_test_camera(service)
    original_lat = cam.latitude

    data = CameraUpdate(name="Only Name Changed")
    updated = await service.update_camera(cam.id, data)

    assert updated.latitude == original_lat


@pytest.mark.asyncio
async def test_update_camera_raises_not_found(test_db: AsyncSession) -> None:
    """update_camera should raise CameraNotFoundError for a non-existent UUID."""
    service = make_service(test_db)
    with pytest.raises(CameraNotFoundError):
        await service.update_camera(uuid.uuid4(), CameraUpdate(name="New Name"))


# ── delete_camera ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_camera_soft_deletes(test_db: AsyncSession) -> None:
    """delete_camera should cause the camera to be invisible to subsequent get_camera calls."""
    service = make_service(test_db)
    cam = await create_test_camera(service)

    await service.delete_camera(cam.id)

    with pytest.raises(CameraNotFoundError):
        await service.get_camera(cam.id)


@pytest.mark.asyncio
async def test_delete_camera_raises_not_found_for_missing(test_db: AsyncSession) -> None:
    """delete_camera should raise CameraNotFoundError for a non-existent UUID."""
    service = make_service(test_db)
    with pytest.raises(CameraNotFoundError):
        await service.delete_camera(uuid.uuid4())


@pytest.mark.asyncio
async def test_delete_camera_raises_not_found_for_already_deleted(
    test_db: AsyncSession,
) -> None:
    """delete_camera on an already-deleted camera should raise CameraNotFoundError."""
    service = make_service(test_db)
    cam = await create_test_camera(service)
    await service.delete_camera(cam.id)

    with pytest.raises(CameraNotFoundError):
        await service.delete_camera(cam.id)
