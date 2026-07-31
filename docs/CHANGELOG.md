# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-30

## [1.1.0] - 2026-07-31

### Current Status
**Ready for Module 5 (Traffic Predictions)**
Modules 1 (Cameras), 2 (Segments), 3 (Readings), and 4 (Alerts) are now fully implemented, reviewed, and frozen.

### Added
- **Module 1: Traffic Cameras**: CRUD operations, RBAC, UUID primary keys, ENUM status, and soft-delete capabilities.
- **Module 2: Traffic Segments**: Geospatial coordinate fields, segment status ENUM, and segment-camera relationship validation.
- **Module 3: Traffic Readings**: High-throughput time-series data ingest using `BIGSERIAL` (auto-increment variant for SQLite), immutable records, and advanced time-series aggregations using standard SQL window functions (`ROW_NUMBER() OVER()`).
- **Module 4: Traffic Alerts**: Alert management linked to segments, state transitions (ACTIVE -> RESOLVED / DISMISSED), comprehensive CRUD operations, soft-deletion, and robust state validations preventing illegal modifications of non-active alerts.
- Added robust test coverage ensuring that Modules 1, 2, 3, and 4 function correctly. The global test suite now contains 172 passing tests (1 skipped for SQLite dialect limitations).

### Fixed
- Fixed trailing slash redirection issues on router root endpoints (e.g., `""` instead of `"/"`).
- Fixed repository test suite timezone evaluation constraints when asserting soft deletes.
- Integrated missing `GET /segments/{segment_id}/latest-reading` implementation via DI of `ReadingRepository` into `SegmentService`.
- Corrected generic `ValueError` logic on date ranges into a structured `InvalidDateRangeError` to trigger a consistent HTTP 422 Unprocessable Entity response.
- Replaced Postgres-only `DISTINCT ON` constructs with cross-dialect compatible `ROW_NUMBER() OVER()` window functions to prevent SQLite testing breakages.
- Handled PostgreSQL `DuplicateObjectError` during Alembic enum creation using `enum.create(op.get_bind(), checkfirst=True)`.
- Reworked Module 4 (Alerts) to address specification deviations:
  - Added missing `get_active_count` and `get_active_by_severity` analytics methods to `AlertRepository`.
  - Added `alert_type` filtering consistently across repository, service, and router layers.
  - Converted `resolve` and `dismiss` endpoints from POST to PATCH.
  - Mapped enum fields to native SQLAlchemy Enums instead of `String` for the `Alert` model.
  - Renamed the table to `alerts` and correctly named the Alembic migration to `0007_create_alerts_table.py`.

## [1.0.0] - 2026-07-30

### Current Status
**Ready for Backend Developer #2**
The Authentication & User Management foundation is completely **frozen**, fully documented, and successfully tested against all requirements.

### Added
- Complete FastAPI application factory with lifespan context management.
- Stateless authentication leveraging securely signed JWTs (Bearer tokens, HS256).
- End-to-end Role-Based Access Control (`ADMIN`, `TRAFFIC_CONTROLLER`, `PUBLIC_USER`).
- User schemas, robust dependency injection patterns, and RESTful routing for Account and Profile management.
- Asynchronous PostgreSQL integration through SQLAlchemy 2.x and the `asyncpg` driver.
- Alembic database migration environment and the initial schema definition.
- Standardized, consistent exception handling that outputs structured JSON for HTTP errors.
- CORS, Request ID generation, and structured Request/Response logging middleware.
- 25+ unit and integration tests executing independently leveraging in-memory SQLite and aiosqlite.

### Improved
- Extracted router registration from `main.py` into a centralized `app/routers/__init__.py` registry to avert future code collisions/merge conflicts.
- Applied robust dependency injection wrappers (`get_auth_service`, `get_user_service`) resulting in better encapsulation and making the application simpler to mock for isolated testing.
- Fixed inconsistent logging behavior within authentication exception handlers to ensure HTTP authentication exceptions properly flush to stdout (useful in production context).
- Improved SQLite testing robustness by conditionally gating PostgreSQL-specific SQLAlchemy pool configurations (e.g. `pool_size`, `max_overflow`).
- Removed duplicated `model_config` attributes within schema inheritance chains and performed unused import cleanup across the system.

### Security
- Password storage utilizes `bcrypt` via Passlib (configured rigidly at 12 work factor rounds by default).
- The `bcrypt` dependency is actively pinned at version `4.0.1` to maintain native compatibility with the generic `passlib` context hashing APIs.
- JWT decoding validates structure and expiry, failing securely via distinct error representations.
- Login operations securely thwart email enumeration attempts via constant-time password hash evaluation mechanisms, irrespective of the existence of the targeted subject email.
- Authentication paths actively observe and respect account suspension conditions (`is_active` flags) synchronously across all interactions.
