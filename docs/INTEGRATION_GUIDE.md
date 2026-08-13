# Integration Guide for Backend Developer #2

Welcome to the **TrafficVision AI Backend**. This guide contains all the information you need to successfully integrate the new business modules: Traffic, Prediction, Alerts, and Analytics.

This guide acts as your instruction manual. It assumes the existing code across the codebase (such as User models or Auth flow) is strictly off-limits (frozen) and focuses exclusively on teaching you how to extend the application gracefully.

---

## Project Architecture Overview

The system strictly adheres to Clean/Layered Architecture, utilizing FastAPI and SQLAlchemy asynchronously. 

Layers are distinctly separated:
* **Routers (`app/routers/`):** The HTTP exposure layer. It performs no logic aside from request marshalling via Pydantic.
* **Services (`app/services/`):** Handles all business logic. No database connections or SQL syntax are executed here directly.
* **Repositories (`app/repositories/`):** Dedicated classes handling the `AsyncSession` interactions and executing SQLAlchemy queries.
* **Models (`app/models/`):** Declarative base classes and Enums mapping to PostgreSQL tables.
* **Schemas (`app/schemas/`):** Pydantic v2 schemas providing strict input/output validation decoupled entirely from models.
* **Dependencies (`app/dependencies/`):** Reusable FastAPI extensions containing factory functions for repositories/authentication logic structure.

## Folder Structure

```
app/
├── core/           # [FROZEN] Core infrastructure 
├── models/         # [EXTENDABLE] Database entities
├── schemas/        # [EXTENDABLE] Pydantic types
├── repositories/   # [EXTENDABLE] SQL CRUD wrappers
├── services/       # [EXTENDABLE] Business behavior
├── routers/        # [EXTENDABLE] API HTTP endpoints
├── dependencies/   # [EXTENDABLE] DI factories
└── main.py         # [FROZEN] Application entry point
```

---

## Adding a New Module (End-to-End)

To build a hypothetical `Alert` module, you will create files systematically spanning across layers:

### 1. Database Model
Create `app/models/alert.py`:
```python
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(primary_key=True)
    # ...
```
**CRITICAL:** Always import your newly added models in `app/models/__init__.py`. Failing to do so ensures Alembic will NOT build your tables.

### 2. Migration Workflow
Generate the SQL script securely using Alembic:
```bash
alembic revision --autogenerate -m "create_alerts_table"
alembic upgrade head
```

### 3. Schemas
Create Pydantic validators in `app/schemas/alert.py`. Define differing models for creations/reads decoupled from the DB context.

### 4. Repositories (Data Access)
Create `app/repositories/alert_repository.py`. Expose asynchronous functions requiring the dependency injection pattern:
```python
class AlertRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def create(self, **kwargs):
        # Database code here
```

### 5. Services (Logic)
Create `app/services/alert_service.py`. Enforce domain business rules using repository dependency arguments rather than directly binding DB connections.

### 6. Dependency Injection 
Create `app/dependencies/alerts.py` leveraging FastAPI bindings:
```python
def get_alert_service(db: AsyncSession = Depends(get_db)):
    return AlertService(AlertRepository(db))
```

### 7. Router
Create `app/routers/alerts.py`:
```python
from fastapi import APIRouter, Depends
router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.get("/")
async def get_alerts(service = Depends(get_alert_service)):
    # ...
```

### 8. Router Registration
Go directly into `app/routers/__init__.py`. DO NOT touch `main.py`.
Locate the `get_api_router()` method and explicitly include your new component underneath the `FUTURE MODULE ROUTERS` marker:
```python
from app.routers.alerts import router as alerts_router
api_router.include_router(alerts_router)
```

---

## Authentication and RBAC (Role-Based Access Control)

You do not need to implement authentication. Import these established tools:

```python
from app.dependencies.auth import get_current_user, require_role
from app.models.user import User, UserRole
```

**Get the connected user:**
```python
@router.post("/")
async def specific_user_endpoint(user: User = Depends(get_current_user)):
    # Provides fully resolved DB user object. Return 401 if missing/invalid.
```

**Protect operations via Roles:**
```python
@router.delete("/", dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.TRAFFIC_CONTROLLER))])
async def sensitive_resource():
    # Only users authorized in those roles can penetrate this handler line.
```

---

## Testing Conventions

- **In-Memory SQLite:** Testing avoids PostgreSQL interactions. Ensure any complex database operations function compatibly across generic SQLAlchemy or write specialized behaviors mapping accordingly.
- **Dependency Override:** Instead of mocking SQL query inputs explicitly, heavily deploy `app.dependency_overrides` against factories (`get_alert_service` etc.) replacing complex components within Router tests cleanly.

## Code and Naming Conventions

* Leverage **Black** syntax formatting guidelines explicitly prior to PRs.
* Pydantic classes represent input/output strictly (`TrafficRead`, `TrafficUpdate`).
* All I/O must remain `async/await` compliant. Do not utilize `.scalar()` blocking syntax; heavily rely on `await db.execute(...)`.

## Git Workflow & PR Expectations

* Feature branch architectures (e.g. `feature/alerts-module`).
* Every newly established route must be bundled alongside respective pytest verifications confirming normal flows and expected failing conditionals (404/422).
* DO NOT submit adjustments or formatting modifications sweeping across files owned within the existing frozen scope (anything associated with generic auth handling).

---

## Common Mistakes to Avoid

1. Failing to import new models under `app/models/__init__.py` (causing Alembic confusion).
2. Implementing business orchestration logic within `routers`.
3. Constructing generic services directly within parameter variables without wrapping them inside FastAPI's `Depends()` contexts utilizing dependency containers.
4. Returning hashed outputs or arbitrary parameters loosely without invoking validation bindings mapped by strict Pydantic return representations.

---

## External Maps Integration (Milestone 2)

The application communicates with an external routing provider (OSRM) to calculate road intersections, distances, and base travel times. This integration is handled via the Adapters layer.

### Configuration
The maps adapter uses the following fields in `app/core/config.py`:
- `maps_provider_url` (str): Base URL for the OSRM backend.
- `maps_api_key` (str): API key (defaults to empty string for OSRM public servers, currently unused by the OSRM implementation but preserved for extensibility).

### Architecture & Mocking
- **MapsAdapterProtocol**: The interface that maps providers must implement. Services only interact with this protocol.
- **OSRMAdapter**: The concrete implementation making asynchronous HTTP calls using `httpx`.
- **Failure Handling**: External HTTP failures or malformed responses are captured by the adapter and translated into domain exceptions (e.g., `MapsProviderError`), ensuring services do not crash from unhandled external HTTP errors.
- **Testing**: In the test suite, the external provider is inherently mocked by injecting a mock implementing `MapsAdapterProtocol`. This guarantees that tests remain hermetic, fast, and not reliant on a live OSRM endpoint.
