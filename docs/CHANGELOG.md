# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2026-08-24

### Current Status
**TrafficVision AI Backend Milestone 3 Completion**
The Operational Intelligence layer (Alerts, Notifications, Incidents, Heatmaps, Trends, and Structured AI Reports) has been successfully implemented and E2E verified.

### Added
- **Automated Alerts**: Implemented synchronous `AlertEvaluatorService` triggered by new traffic readings.
- **Notifications & Incidents**: Added user-specific notification tracking (`recipient_user_id`) and incident ingestion workflow triggering alerts.
- **Geographic Heatmaps**: Upgraded `GET /api/v1/analytics/congestion-heatmap` to expose segment start/end geographic coordinates.
- **Trend Classification**: Added deterministic thresholding for historical trends (-5% / +5% configuration defaults) in `GET /api/v1/analytics/segments/{segment_id}/trends`.
- **Structured AI Insights**: Added `GET /api/v1/insights/segment/{segment_id}` for deterministic traffic intelligence combining alerts, route comparisons, predictions, and readings.
- **AI Traffic Reports**: Added `GET /api/v1/analytics/ai-report` serving bounded, read-only operational intelligence across all domains for specified reporting windows.
- **E2E Integration Validation**: Test suite expanded to thoroughly cover cross-module execution workflows. Final regression baseline: 359 passed, 5 skipped, 0 failed.

## [1.2.0] - 2026-08-13

### Current Status
**TrafficVision AI Backend Milestone 2 Completion**
The intelligence layer (ML predictions, dynamic travel times, route recommendations) and OSRM integration have been successfully implemented and tested.

### Added
- **Machine Learning (app/ml)**: Added `feature_engineering.py` and `prediction_engine.py` using `RandomForestRegressor` (`scikit-learn`) for on-the-fly congestion forecasting.
- **Congestion Forecasting Endpoint**: Added `POST /api/v1/predictions/segment/{segment_id}/forecast` orchestrating historical readings and ML inference.
- **Travel Time Estimation**: Added `GET /api/v1/routes/{route_id}/estimate` to calculate dynamic travel durations utilizing current traffic reading speeds and falling back to speed limits.
- **Route Recommendation**: Added `GET /api/v1/routes/compare` for scoring candidate routes based on estimated travel times and congestion penalties.
- **Maps Provider Integration**: Created `MapsAdapterProtocol` and a concrete `OSRMAdapter` leveraging `httpx` to abstract routing provider HTTP calls. Added `maps_provider_url` and `maps_api_key` to core configuration.
- **Prediction Analytics**: Added `GET /api/v1/analytics/predictions` to report real operational prediction metrics (e.g., completion rate).
- **Domain Exceptions**: Expanded `app/core/exceptions.py` with `InsufficientReadingsError`, `NoViableRouteError`, and `MapsProviderError`.
- **Test Suite**: Developed comprehensive unit and integration tests for ML logic, forecasting, travel times, recommendations, and mock-based maps adapters.

### Changed
- `RouteService` now optionally injects `PredictionRepository` for congestion forecasting functionality.
- `requirements.txt` updated to include `scikit-learn==1.5.2` and `numpy==1.26.4`.

## [1.0.0] - 2026-08-01

### Current Status
**TrafficVision AI Backend v1.0.0 Release Readiness**
All core modules (1–7) and the Authentication foundation are fully implemented, verified, and frozen.

### Added
- Completed `API_REFERENCE.md` for Module 6 (Routes) and Module 7 (Analytics).

### Fixed
- Resolved PostgreSQL ENUM migration deployment issue (`DuplicateObjectError`) using `postgresql.ENUM` with `create_type=False` across affected migrations.
- Aligned ORM mappings of `Camera` and `Segment` models strictly to native SQLAlchemy `Enum` types.
- Final PostgreSQL migration verification successful (upgrade/downgrade/upgrade on a fresh DB).
- Final regression verification: 269 passed, 5 skipped, 0 failed.

## [1.1.0] - 2026-07-31

### Current Status
**Modules 1–5** (Cameras, Segments, Readings, Alerts, Predictions) are now fully implemented, reviewed, and frozen.

### Added
- **Module 1: Traffic Cameras**: CRUD operations, RBAC, UUID primary keys, ENUM status, and soft-delete capabilities.
- **Module 2: Traffic Segments**: Geospatial coordinate fields, segment status ENUM, and segment-camera relationship validation.
- **Module 3: Traffic Readings**: High-throughput time-series data ingest using `BIGSERIAL` (auto-increment variant for SQLite), immutable records, and advanced time-series aggregations using standard SQL window functions (`ROW_NUMBER() OVER()`).
- **Module 4: Traffic Alerts**: Alert management linked to segments, state transitions (ACTIVE -> RESOLVED / DISMISSED), comprehensive CRUD operations, soft-deletion, and robust state validations preventing illegal modifications of non-active alerts.
- **Module 5: Traffic Predictions**: AI-driven congestion forecasting including `PredictionStatus` state transitions (PENDING -> COMPLETED / FAILED), confidence scoring, predictive congestion levels, and validation against predictions scheduled in the past.
- Added robust test coverage ensuring that Modules 1, 2, 3, 4, and 5 function correctly. The global test suite now contains 188 passing tests (1 skipped for SQLite dialect limitations).

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
- Reworked Module 5 (Predictions) to address specification deviations:
  - Added router integration tests covering HTTP 204 for DELETE, HTTP 404 for soft-deleted predictions, and the complete end-to-end `PENDING` -> `COMPLETED`/`FAILED` lifecycles.
  - Verified and confirmed that physical database schemas strictly rely on Alembic to manage indexes and constraints, decoupling ORM models.

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
