# Architecture — TrafficVision AI Backend

## Design Philosophy

The backend is architected around the **Clean Architecture** principle:
dependencies always point **inward** (toward domain logic), never outward.

```
HTTP Layer (Routers)
        ↓
Business Logic (Services)
        ↓
Data Access (Repositories)
        ↓
Database (PostgreSQL)
```

Infrastructure (core/) is a cross-cutting concern available at all layers but never depends on domain logic.

---

## Folder Structure

```
app/
├── core/                    # Infrastructure — no domain logic
│   ├── config.py            # Pydantic BaseSettings (all env vars in one place)
│   ├── database.py          # SQLAlchemy async engine, Base class, get_db Depends
│   ├── security.py          # bcrypt + JWT — pure functions, no I/O
│   ├── middleware.py        # CORS, RequestID, RequestLogging middleware
│   ├── logging.py           # Structured logging setup
│   └── exceptions.py        # Domain exceptions + global exception handlers
│
├── models/                  # ORM models (SQLAlchemy 2.x Mapped classes)
│   ├── __init__.py          # Re-exports ALL models (required for Alembic)
│   └── user.py              # User model + UserRole enum
│
├── schemas/                 # Pydantic v2 schemas (independent of ORM)
│   ├── auth.py              # LoginRequest, RegisterRequest, TokenResponse
│   └── user.py              # UserRead, UserProfile, UserUpdate
│
├── repositories/            # Database access — raw async SQLAlchemy queries
│   └── user_repository.py   # CRUD for User table
│
├── services/                # Business logic — orchestrates repositories
│   ├── auth_service.py      # register(), login() — no HTTP, no ORM queries
│   └── user_service.py      # get_profile(), update_profile()
│
├── routers/                 # Thin HTTP layer — route definitions only
│   ├── auth.py              # /api/v1/auth/*
│   └── users.py             # /api/v1/users/*
│
├── dependencies/            # FastAPI Depends() factories
│   └── auth.py              # get_current_user, require_role()
│
├── ml/                      # Machine Learning supporting logic
│   ├── feature_engineering.py # Data transforms and window aggregations
│   ├── model_adapter.py       # Wrapper for external ML libraries
│   └── prediction_engine.py   # Prediction inference orchestrator
│
├── adapters/                # External integration anti-corruption layer
│   └── maps_adapter.py      # Abstract protocol and OSRM implementation
│
├── utils/                   # Pure helper functions (no I/O)
│   └── datetime.py          # UTC timestamp helpers
│
└── main.py                  # App factory, router registration, health endpoint
```

---

## Dependency Flow

```
Incoming Request
     │
     ▼
[CORS Middleware]
     │
     ▼
[Request ID Middleware]
     │
     ▼
[Request Logging Middleware]
     │
     ▼
[FastAPI Router] — validates schema via Pydantic
     │
     ├──→ [Depends(get_db)] — opens AsyncSession
     │
     ├──→ [Depends(get_current_user)] — JWT decode + DB user load
     │
     └──→ [Service] — business logic
               │
               ├──→ [ML Engine] — feature engineering & model inference
               │
               ├──→ [Maps Adapter] — external HTTP abstraction
               │
               └──→ [Repository] — SQL queries
                         │
                         └──→ [PostgreSQL]
     │
     ▼
[Pydantic Response Model] — output serialization
     │
     ▼
[Exception Handler] — maps domain errors → HTTP status
     │
     ▼
JSON Response
```

---

## Authentication Flow

```
POST /api/v1/auth/register
─────────────────────────────────
 1. Pydantic validates request body
 2. AuthService checks email uniqueness (UserRepository.exists_by_email)
 3. security.hash_password() creates bcrypt hash
 4. UserRepository.create() persists User
 5. UserRead schema returned (no password)

POST /api/v1/auth/login
─────────────────────────────────
 1. Pydantic validates request body
 2. AuthService fetches user by email (timing-safe: always hashes)
 3. security.verify_password() checks bcrypt hash
 4. is_active check — rejects deactivated accounts
 5. security.create_access_token() mints JWT with role + email claims
 6. TokenResponse returned (access_token, token_type, expires_in)

GET /api/v1/users/me [Bearer required]
─────────────────────────────────
 1. HTTPBearer extracts token from Authorization header
 2. get_current_user Depends() decodes JWT via security.decode_access_token()
 3. User loaded from DB by UUID (sub claim)
 4. is_active re-checked (handles post-issuance deactivation)
 5. UserProfile schema returned
```

---

## Database Design

### User Table Schema

```sql
CREATE TABLE users (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name        VARCHAR(255) NOT NULL,
    email            VARCHAR(255) NOT NULL UNIQUE,
    hashed_password  VARCHAR(255) NOT NULL,
    role             VARCHAR(50) NOT NULL DEFAULT 'PUBLIC_USER'
                         CHECK (role IN ('ADMIN','TRAFFIC_CONTROLLER','PUBLIC_USER')),
    is_active        BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX ix_users_email ON users (email);
```

---

## Role-Based Access Control

```python
class UserRole(str, Enum):
    ADMIN             = "ADMIN"
    TRAFFIC_CONTROLLER = "TRAFFIC_CONTROLLER"
    PUBLIC_USER       = "PUBLIC_USER"
```

### Permission Matrix (current foundation)

| Endpoint | PUBLIC_USER | TRAFFIC_CONTROLLER | ADMIN |
|----------|----|----|----|
| `POST /auth/register` | ✅ (no auth) | ✅ | ✅ |
| `POST /auth/login` | ✅ (no auth) | ✅ | ✅ |
| `GET /users/me` | ✅ | ✅ | ✅ |
| `PUT /users/me` | ✅ | ✅ | ✅ |

---

## Extension Points for Backend Developer #2

### Adding a New Module (step-by-step)

```
Step 1: Create your model
   app/models/traffic.py  (inherits from Base)
   → Add import to app/models/__init__.py

Step 2: Create your schemas
   app/schemas/traffic.py  (Pydantic v2)

Step 3: Create your repository
   app/repositories/traffic_repository.py

Step 4: Create your service
   app/services/traffic_service.py

Step 5: Create your router
   app/routers/traffic.py

Step 6: Register in app/routers/__init__.py
   from app.routers.traffic import router as traffic_router
   api_router.include_router(traffic_router)

Step 7: Generate a migration
   alembic revision --autogenerate -m "add_traffic_cameras_table"
   alembic upgrade head
```

### Using Authentication in New Routers

```python
from fastapi import APIRouter, Depends
from app.dependencies.auth import get_current_user, require_role
from app.models.user import User, UserRole

router = APIRouter(prefix="/traffic", tags=["Traffic"])

# Any authenticated user:
@router.get("/public-view")
async def public_view(user: User = Depends(get_current_user)):
    ...

# Only TRAFFIC_CONTROLLER and ADMIN:
@router.post(
    "/incident",
    dependencies=[Depends(require_role(UserRole.TRAFFIC_CONTROLLER, UserRole.ADMIN))]
)
async def report_incident(...):
    ...

# Admin only:
@router.delete(
    "/camera/{id}",
    dependencies=[Depends(require_role(UserRole.ADMIN))]
)
async def delete_camera(...):
    ...
```

---

## SOLID Principles Applied

| Principle | Implementation |
|-----------|---------------|
| **Single Responsibility** | Each layer has one job (Router=HTTP, Service=Logic, Repo=Data) |
| **Open/Closed** | New modules extend by adding files, not modifying auth code |
| **Liskov Substitution** | UserRead/UserProfile schema hierarchy |
| **Interface Segregation** | Dependency factories are small and specific (get_db, get_current_user, require_role) |
| **Dependency Inversion** | Services receive Repositories via constructor injection |
