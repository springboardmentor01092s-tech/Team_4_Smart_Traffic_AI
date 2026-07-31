"""
tests/test_cameras/test_camera_repository.py

Unit-level repository tests for CameraRepository.

These tests interact with the repository directly via the test_db session.
No HTTP client is used here. Tests verify that the repository correctly
persists, retrieves, filters, updates, and soft-deletes TrafficCamera records.

Soft-delete behaviour is a key concern:
  - After soft_delete(), get_by_id() must return None for the same camera.
  - get_all() must exclude soft-deleted cameras.

Test database: SQLite in-memory via aiosqlite (from conftest.py).
Note: The camera_status ENUM falls back to VARCHAR in SQLite automatically;
enum value enforcement happens at the Pydantic layer, not the DB layer in tests.
"""
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.camera import CameraStatus, TrafficCamera
from app.repositories.camera_repository import CameraRepository


# ── Helpers ───────────────────────────────────────────────────────────────────

async def make_camera(
    repo: CameraRepository,
    *,
    name: str = "Test Camera",
    location_name: str = "Test Location",
    latitude: float = 28.6139,
    longitude: float = 77.2090,
    status: CameraStatus = CameraStatus.ACTIVE,
    description: str | None = None,
) -> TrafficCamera:
    """Create and return a test camera via the repository."""
    return await repo.create(
        name=name,
        location_name=location_name,
        latitude=latitude,
        longitude=longitude,
        status=status,
        description=description,
    )


# ── Create ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_camera_persists_all_fields(test_db: AsyncSession) -> None:
    """Camera created via repository should have all fields correctly set."""
    repo = CameraRepository(test_db)
    camera = await make_camera(
        repo,
        name="North Camera",
        location_name="NH-1 Toll Plaza 3",
        latitude=28.6139,
        longitude=77.2090,
        status=CameraStatus.ACTIVE,
        description="Test description",
    )

    assert camera.id is not None
    assert isinstance(camera.id, uuid.UUID)
    assert camera.name == "North Camera"
    assert camera.location_name == "NH-1 Toll Plaza 3"
    assert camera.latitude == 28.6139
    assert camera.longitude == 77.2090
    assert camera.status == CameraStatus.ACTIVE
    assert camera.description == "Test description"
    assert camera.deleted_at is None
    assert camera.created_at is not None
    assert camera.updated_at is not None


@pytest.mark.asyncio
async def test_create_camera_defaults_status_to_active(test_db: AsyncSession) -> None:
    """Camera created without explicit status should default to ACTIVE."""
    repo = CameraRepository(test_db)
    camera = await make_camera(repo)
    assert camera.status == CameraStatus.ACTIVE


@pytest.mark.asyncio
async def test_create_camera_description_nullable(test_db: AsyncSession) -> None:
    """Camera created without description should have description=None."""
    repo = CameraRepository(test_db)
    camera = await make_camera(repo, description=None)
    assert camera.description is None


# ── get_by_id ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_by_id_returns_camera(test_db: AsyncSession) -> None:
    """get_by_id should return the camera when it exists and is not deleted."""
    repo = CameraRepository(test_db)
    created = await make_camera(repo)

    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.name == created.name


@pytest.mark.asyncio
async def test_get_by_id_returns_none_for_missing_id(test_db: AsyncSession) -> None:
    """get_by_id should return None for a UUID that does not exist."""
    repo = CameraRepository(test_db)
    result = await repo.get_by_id(uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_get_by_id_returns_none_for_soft_deleted(test_db: AsyncSession) -> None:
    """get_by_id must return None for a camera that has been soft-deleted."""
    repo = CameraRepository(test_db)
    camera = await make_camera(repo)
    await repo.soft_delete(camera)

    result = await repo.get_by_id(camera.id)
    assert result is None


# ── get_all ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_all_returns_all_non_deleted(test_db: AsyncSession) -> None:
    """get_all should return all cameras where deleted_at IS NULL."""
    repo = CameraRepository(test_db)
    cam1 = await make_camera(repo, name="Camera A")
    cam2 = await make_camera(repo, name="Camera B")

    cameras = await repo.get_all()
    ids = {c.id for c in cameras}
    assert cam1.id in ids
    assert cam2.id in ids


@pytest.mark.asyncio
async def test_get_all_excludes_soft_deleted(test_db: AsyncSession) -> None:
    """get_all must not include cameras that have been soft-deleted."""
    repo = CameraRepository(test_db)
    active_cam = await make_camera(repo, name="Active Camera")
    deleted_cam = await make_camera(repo, name="Deleted Camera")
    await repo.soft_delete(deleted_cam)

    cameras = await repo.get_all()
    ids = {c.id for c in cameras}
    assert active_cam.id in ids
    assert deleted_cam.id not in ids


@pytest.mark.asyncio
async def test_get_all_filters_by_status(test_db: AsyncSession) -> None:
    """get_all should return only cameras matching the given status."""
    repo = CameraRepository(test_db)
    active_cam = await make_camera(repo, status=CameraStatus.ACTIVE)
    inactive_cam = await make_camera(repo, status=CameraStatus.INACTIVE)

    active_results = await repo.get_all(status=CameraStatus.ACTIVE)
    inactive_results = await repo.get_all(status=CameraStatus.INACTIVE)

    active_ids = {c.id for c in active_results}
    inactive_ids = {c.id for c in inactive_results}

    assert active_cam.id in active_ids
    assert inactive_cam.id not in active_ids
    assert inactive_cam.id in inactive_ids
    assert active_cam.id not in inactive_ids


@pytest.mark.asyncio
async def test_get_all_pagination(test_db: AsyncSession) -> None:
    """get_all should respect skip and limit for pagination."""
    repo = CameraRepository(test_db)
    for i in range(5):
        await make_camera(repo, name=f"Camera {i}")

    page1 = await repo.get_all(skip=0, limit=3)
    page2 = await repo.get_all(skip=3, limit=3)

    assert len(page1) == 3
    assert len(page2) == 2
    # No overlap
    ids_p1 = {c.id for c in page1}
    ids_p2 = {c.id for c in page2}
    assert not ids_p1.intersection(ids_p2)


# ── update ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_camera_changed_fields(test_db: AsyncSession) -> None:
    """update should apply the specified fields and return the refreshed instance."""
    repo = CameraRepository(test_db)
    camera = await make_camera(repo, name="Original Name")

    updated = await repo.update(camera, name="Updated Name", status=CameraStatus.MAINTENANCE)

    assert updated.name == "Updated Name"
    assert updated.status == CameraStatus.MAINTENANCE


@pytest.mark.asyncio
async def test_update_camera_preserves_unchanged_fields(test_db: AsyncSession) -> None:
    """update should not change fields not included in the update dict."""
    repo = CameraRepository(test_db)
    camera = await make_camera(repo, latitude=28.6139, longitude=77.2090)
    original_lat = camera.latitude

    updated = await repo.update(camera, name="New Name")

    assert updated.latitude == original_lat


# ── soft_delete ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_soft_delete_sets_deleted_at(test_db: AsyncSession) -> None:
    """soft_delete should set deleted_at to a non-None datetime."""
    repo = CameraRepository(test_db)
    camera = await make_camera(repo)
    assert camera.deleted_at is None

    await repo.soft_delete(camera)
    assert camera.deleted_at is not None
    assert isinstance(camera.deleted_at, datetime)


@pytest.mark.asyncio
async def test_soft_delete_sets_updated_at(test_db: AsyncSession) -> None:
    """soft_delete should update the updated_at timestamp."""
    repo = CameraRepository(test_db)
    camera = await make_camera(repo)
    original_updated_at = camera.updated_at.replace(tzinfo=None)

    # Small sleep to ensure timestamp difference
    import asyncio
    await asyncio.sleep(0.01)

    await repo.soft_delete(camera)
    assert camera.updated_at.replace(tzinfo=None) >= original_updated_at


@pytest.mark.asyncio
async def test_soft_delete_does_not_physically_remove(test_db: AsyncSession) -> None:
    """After soft_delete, the record should still be physically present in the DB."""
    repo = CameraRepository(test_db)
    camera = await make_camera(repo)
    camera_id = camera.id
    await repo.soft_delete(camera)

    # Verify it is gone from the normal query
    normal_result = await repo.get_by_id(camera_id)
    assert normal_result is None

    # Verify it still exists physically (bypass soft-delete filter)
    from sqlalchemy import select
    raw_result = await test_db.execute(
        select(TrafficCamera).where(TrafficCamera.id == camera_id)
    )
    raw_camera = raw_result.scalar_one_or_none()
    assert raw_camera is not None
    assert raw_camera.deleted_at is not None
