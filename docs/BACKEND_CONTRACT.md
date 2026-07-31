# Backend Contract — For Backend Developer #2

> This document defines the integration rules between the Authentication
> foundation (Backend Dev #1) and future business modules (Backend Dev #2).
>
> **Read this before writing a single line of code.**

---

## What This Contract Guarantees

Backend Dev #1 guarantees that:

1. The `User` ORM model will remain stable (no field renames, no type changes without notice)
2. The `UserRole` enum will always include `ADMIN`, `TRAFFIC_CONTROLLER`, `PUBLIC_USER`
3. The `get_current_user` dependency will always return a valid, DB-loaded `User` instance
4. The `require_role()` factory will always raise `PermissionDeniedError` (HTTP 403) for unauthorized roles
5. The `/api/v1/auth/*` and `/api/v1/users/me` routes will never be renamed
6. The `app/core/` package will remain stable — no breaking changes to public APIs

---

## What You MAY Do

✅ Add new model files to `app/models/`
✅ Add new schema files to `app/schemas/`
✅ Add new repositories to `app/repositories/`
✅ Add new services to `app/services/`
✅ Add new routers to `app/routers/`
✅ Register your routers in `app/routers/__init__.py` (the marked extension block)
✅ Create new Alembic migrations for your tables
✅ Import and use `User`, `UserRole`, `get_current_user`, `require_role` in your modules

---

## What You MUST NOT Do

❌ Modify any file in `app/core/` without explicit agreement with Dev #1
❌ Modify `app/models/user.py` or `app/models/__init__.py`
❌ Modify `app/routers/auth.py` or `app/routers/users.py`
❌ Modify `app/dependencies/auth.py`
❌ Add business logic to `app/core/`
❌ Create migrations that modify the `users` table

---

## How to Use Authentication in Your Modules

### Import the dependencies

```python
from app.dependencies.auth import get_current_user, require_role
from app.models.user import User, UserRole
```

### Pattern 1: Route that needs the current user

```python
from fastapi import APIRouter, Depends
from app.dependencies.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/traffic", tags=["Traffic"])

@router.get("/my-alerts")
async def my_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AlertRead]:
    return await alert_service.get_alerts_for_user(current_user.id, db)
```

### Pattern 2: Route locked to specific roles

```python
@router.post(
    "/cameras",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.TRAFFIC_CONTROLLER))]
)
async def add_camera(data: CameraCreate, db: AsyncSession = Depends(get_db)) -> CameraRead:
    ...
```

### Pattern 3: Admin-only route (no user object needed)

```python
@router.delete(
    "/cameras/{camera_id}",
    dependencies=[Depends(require_role(UserRole.ADMIN))]
)
async def delete_camera(camera_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    ...
```

### Pattern 4: Role-conditional logic

```python
@router.get("/analytics")
async def get_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsRead:
    if current_user.role == UserRole.ADMIN:
        return await analytics_service.get_full_report(db)
    elif current_user.role == UserRole.TRAFFIC_CONTROLLER:
        return await analytics_service.get_controller_report(db)
    else:
        return await analytics_service.get_public_report(db)
```

---

## User Model Reference

```python
class User(Base):
    id: uuid.UUID          # Primary key — use str(user.id) for strings
    full_name: str
    email: str             # Lowercase, unique
    hashed_password: str   # NEVER read or expose this field
    role: UserRole         # "ADMIN" | "TRAFFIC_CONTROLLER" | "PUBLIC_USER"
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
```

### Creating Foreign Keys to User

```python
# In your model:
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID

class TrafficAlert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Optional relationship:
    creator: Mapped[User | None] = relationship("User", lazy="select")
```

---

## Registering Your Router

In `app/routers/__init__.py`, find the marked extension block inside `get_api_router()`:

```python
    # ──────────────────────────────────────────────────────────────────────────
    # FUTURE MODULE ROUTERS — Backend Developer #2 adds here
    # Example:
    #   from app.routers.traffic import router as traffic_router
    #   api_router.include_router(traffic_router)
    # ──────────────────────────────────────────────────────────────────────────
```

Add your router import and `include_router` call inside this block.

---

## Exception Handling

Reuse or subclass the existing exception hierarchy:

```python
from app.core.exceptions import AppBaseException

class TrafficCameraNotFoundError(AppBaseException):
    def __init__(self, camera_id: uuid.UUID) -> None:
        super().__init__(f"Traffic camera {camera_id} not found.")
```

Then register a handler in `app/core/exceptions.py`'s `register_exception_handlers()`:

```python
async def traffic_camera_not_found_handler(request, exc):
    return _error_response(request, 404, exc.message, "CAMERA_NOT_FOUND")

# In register_exception_handlers():
app.add_exception_handler(TrafficCameraNotFoundError, traffic_camera_not_found_handler)
```

---

## Alembic Migration Workflow

```bash
# 1. Create your model in app/models/your_model.py
# 2. Import it in app/models/__init__.py
# 3. Generate the migration
alembic revision --autogenerate -m "add_traffic_cameras_table"

# 4. Review the generated file in alembic/versions/
# 5. Apply it
alembic upgrade head
```

> ⚠️ Never run `alembic downgrade` on the `0001_create_users_table` migration in production.

---

## Environment Variables

You may add your own environment variables to `.env`. The `Settings` class
uses `extra="ignore"` so unknown keys are safely ignored.

Add your settings to `app/core/config.py` as new fields on `Settings`:

```python
# Example (discuss with Dev #1 before adding):
traffic_api_key: str = Field(default="", description="External traffic data API key")
prediction_model_path: str = Field(default="models/", description="Path to ML model files")
```

---

## API Versioning

All routes use the `/api/v1` prefix (configured via `API_V1_PREFIX` in `.env`).
Your routes should follow the same convention:

```python
# Your router prefix:
router = APIRouter(prefix="/traffic", tags=["Traffic"])

# Final URL will be: /api/v1/traffic/...
```

---

## Authentication Module Status

**Status: FROZEN**

Authentication & User Management is considered complete.

Future modifications should be limited to:
- Bug fixes
- Security updates
- Dependency upgrades

No structural refactoring. New business functionality must be implemented as independent modules.
