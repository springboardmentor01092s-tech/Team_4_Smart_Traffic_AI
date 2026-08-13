# TrafficVision AI — Engineering Design Document
## Backend Developer #2 — Business Modules

> **Status:** Design Only. No implementation code.
> **Author:** Backend Developer #2
> **Foundation:** Authentication & User Management (Dev #1) — FROZEN
> **Version:** 2.0 (revised)
> **Date:** 2026-07-31

---

## Revision History

| Section | Change |
|---------|--------|
| Header | Version bumped to 2.0 |
| 0 (new) | Revision History table added |
| 1.1–1.7 | All `id` fields changed from `int / auto-increment` to `uuid.UUID` except TrafficReading |
| 1.2 | `TrafficSegment` — four coordinate fields added; `deleted_at` added |
| 1.3 | `TrafficReading` — `segment_id` FK type changed to `uuid.UUID`; no other change |
| 1.4 | `Alert` — `id` and `segment_id` to UUID; `deleted_at` added |
| 1.5 | `TrafficPrediction` — `id` and `segment_id` to UUID; `requested_at` and `completed_at` added; `deleted_at` added |
| 1.6 | `Route` — `id` to UUID; `deleted_at` added |
| 1.7 | `RouteSegment` — `id`, `route_id`, `segment_id` to UUID |
| 2 (all) | All `SERIAL` PKs → `UUID`; `INTEGER` FKs pointing to soft-delete tables → `UUID`; `VARCHAR+CHECK` → native PostgreSQL ENUM; `deleted_at` columns added; coordinate columns added to segments; lifecycle timestamps added to predictions; FK delete behavior updated |
| 3.2, 3.3 | Soft-delete narrative updated; FK delete behaviour explanations updated |
| 4 (new note) | PostgreSQL ENUM type names listed; SQLAlchemy usage guidance added |
| 5.2 | Segment JSON examples updated with coordinate fields |
| 5.5 | Prediction response JSON updated with `requested_at` / `completed_at` |
| 5.4, 5.1, 5.6 | `id` in JSON examples changed to UUID strings |
| 6.1–6.5 | Repository method signatures updated: `int` IDs → `uuid.UUID`; `delete` → `soft_delete`; `get_all` now filters `deleted_at IS NULL` |
| 6.7 | `AnalyticsRepository` section removed entirely |
| 7.7 | `AnalyticsService` dependencies changed — no longer uses `AnalyticsRepository`; now uses `ReadingRepository`, `AlertRepository`, `SegmentRepository`, `PredictionRepository` |
| 9.7 | `get_analytics_service` factory updated to inject four existing repositories |
| 11.1–11.4 | Alembic plan updated: `CREATE TYPE` statements precede each `CREATE TABLE`; soft-delete columns included in table DDL notes |
| 12.1 | Repository test guidance updated for `soft_delete` and `deleted_at` filter |
| 12.6 | Integration workflow 5 updated — soft-delete rather than cascade-delete tested |

---

## Table of Contents

1. [Domain Model](#1-domain-model)
2. [Database Design](#2-database-design)
3. [Entity Relationships](#3-entity-relationships)
4. [Enumerations](#4-enumerations)
5. [REST API Design](#5-rest-api-design)
6. [Repository Design](#6-repository-design)
7. [Service Design](#7-service-design)
8. [Router Design](#8-router-design)
9. [Dependency Injection](#9-dependency-injection)
10. [Exception Design](#10-exception-design)
11. [Alembic Plan](#11-alembic-plan)
12. [Testing Strategy](#12-testing-strategy)
13. [Module Dependency Graph](#13-module-dependency-graph)

---

## 1. Domain Model

Seven business entities satisfy all six functional requirement groups.
Changes from v1 are called out inline with **[REVISED]** markers.

---

### 1.1 TrafficCamera

**Purpose:**
Represents a physical surveillance camera installed at a road location.
Cameras are the source infrastructure for all live traffic data collection.
Other entities (TrafficSegment) reference cameras to identify where readings originate.
Soft-deleted cameras are hidden from normal queries but retained for audit history.

| Field | Python Type | Nullable | Default | Validation |
|-------|------------|----------|---------|-----------|
| `id` | `uuid.UUID` **[REVISED: was int]** | No | `uuid4()` | PK |
| `name` | `str` | No | — | 2–100 chars |
| `location_name` | `str` | No | — | 2–255 chars |
| `latitude` | `float` | No | — | -90.0 to 90.0 |
| `longitude` | `float` | No | — | -180.0 to 180.0 |
| `status` | `CameraStatus` | No | `ACTIVE` | enum value |
| `description` | `str` | Yes | `None` | max 500 chars |
| `installed_at` | `datetime` | No | `utcnow()` | UTC, timezone-aware |
| `created_at` | `datetime` | No | `utcnow()` | UTC, timezone-aware |
| `updated_at` | `datetime` | No | `utcnow()` | UTC, updated on write |
| `deleted_at` | `datetime` | Yes **[NEW]** | `None` | UTC, set on soft delete |

---

### 1.2 TrafficSegment

**Purpose:**
Represents a discrete road segment being actively monitored.
A segment is a logical span of road between two defined points, now including
precise geographic coordinates for mapping and geospatial queries.
It is the primary domain entity — all readings, alerts, predictions,
and routes are anchored to segments.
Optionally linked to one camera that monitors it.
Soft deletion preserves historical reading, alert, and prediction records.

| Field | Python Type | Nullable | Default | Validation |
|-------|------------|----------|---------|-----------|
| `id` | `uuid.UUID` **[REVISED: was int]** | No | `uuid4()` | PK |
| `name` | `str` | No | — | 2–150 chars |
| `start_point` | `str` | No | — | 2–255 chars, human-readable name |
| `end_point` | `str` | No | — | 2–255 chars, human-readable name |
| `start_latitude` | `float` | No **[NEW]** | — | -90.0 to 90.0 |
| `start_longitude` | `float` | No **[NEW]** | — | -180.0 to 180.0 |
| `end_latitude` | `float` | No **[NEW]** | — | -90.0 to 90.0 |
| `end_longitude` | `float` | No **[NEW]** | — | -180.0 to 180.0 |
| `length_km` | `float` | No | — | > 0.0 |
| `speed_limit_kmh` | `int` | No | — | 1–300 |
| `camera_id` | `uuid.UUID` (FK) **[REVISED]** | Yes | `None` | references `traffic_cameras.id` |
| `status` | `SegmentStatus` | No | `ACTIVE` | enum value |
| `created_at` | `datetime` | No | `utcnow()` | UTC |
| `updated_at` | `datetime` | No | `utcnow()` | UTC |
| `deleted_at` | `datetime` | Yes **[NEW]** | `None` | UTC, set on soft delete |

---

### 1.3 TrafficReading

**Purpose:**
A snapshot measurement of traffic conditions on a segment at a specific instant.
This is the raw data produced by cameras or manual input.
Serves as the factual basis for alerts, predictions, and analytics.
Readings are append-only; they are **never updated or deleted**.
The `id` remains BIGSERIAL because this table is the highest-volume table in the system.

| Field | Python Type | Nullable | Default | Validation |
|-------|------------|----------|---------|-----------|
| `id` | `int` (BIGSERIAL) | No | auto | PK — retained as integer for performance |
| `segment_id` | `uuid.UUID` (FK) **[REVISED]** | No | — | references `traffic_segments.id` |
| `vehicle_count` | `int` | No | — | >= 0 |
| `average_speed_kmh` | `float` | No | — | >= 0.0 |
| `congestion_level` | `CongestionLevel` | No | — | enum value |
| `occupancy_percent` | `float` | Yes | `None` | 0.0–100.0, road occupancy |
| `recorded_at` | `datetime` | No | — | UTC, time of measurement |
| `created_at` | `datetime` | No | `utcnow()` | UTC, time of insertion |

> No `deleted_at`. Readings are never deleted or soft-deleted. They are the immutable measurement record.

---

### 1.4 Alert

**Purpose:**
Represents a traffic incident notification raised by a controller or the system.
Alerts inform road users and other systems of actionable conditions
(congestion, accidents, closures, emergencies).
Alerts have an operational lifecycle: `ACTIVE → RESOLVED or DISMISSED`.
Soft deletion (via `deleted_at`) preserves the audit trail after an admin removes an alert.

| Field | Python Type | Nullable | Default | Validation |
|-------|------------|----------|---------|-----------|
| `id` | `uuid.UUID` **[REVISED: was int]** | No | `uuid4()` | PK |
| `segment_id` | `uuid.UUID` (FK) **[REVISED]** | No | — | references `traffic_segments.id` |
| `created_by` | `uuid.UUID` (FK) | Yes | `None` | references `users.id`, SET NULL on delete |
| `title` | `str` | No | — | 5–200 chars |
| `description` | `str` | Yes | `None` | max 1000 chars |
| `alert_type` | `AlertType` | No | — | enum value |
| `severity` | `AlertSeverity` | No | — | enum value |
| `status` | `AlertStatus` | No | `ACTIVE` | enum value |
| `resolved_at` | `datetime` | Yes | `None` | UTC, set when status → RESOLVED |
| `created_at` | `datetime` | No | `utcnow()` | UTC |
| `updated_at` | `datetime` | No | `utcnow()` | UTC |
| `deleted_at` | `datetime` | Yes **[NEW]** | `None` | UTC, set on soft delete |

---

### 1.5 TrafficPrediction

**Purpose:**
A forward-looking forecast of traffic conditions for a segment at a future timestamp.
Generated by an AI/ML model (or rule-based logic in the early phase).
Predictions follow a strict lifecycle: `PENDING → COMPLETED or FAILED`.
Lifecycle timestamps (`requested_at`, `completed_at`) allow latency tracking and SLA monitoring.
Soft deletion preserves historical prediction accuracy records.

| Field | Python Type | Nullable | Default | Validation |
|-------|------------|----------|---------|-----------|
| `id` | `uuid.UUID` **[REVISED: was int]** | No | `uuid4()` | PK |
| `segment_id` | `uuid.UUID` (FK) **[REVISED]** | No | — | references `traffic_segments.id` |
| `predicted_congestion_level` | `CongestionLevel` | Yes | `None` | enum value, set on completion |
| `predicted_vehicle_count` | `int` | Yes | `None` | >= 0 |
| `predicted_avg_speed_kmh` | `float` | Yes | `None` | >= 0.0 |
| `confidence_score` | `float` | Yes | `None` | 0.0–1.0 |
| `prediction_for` | `datetime` | No | — | UTC, the future moment being predicted |
| `horizon_minutes` | `int` | No | — | > 0, how far ahead (e.g. 30, 60, 120) |
| `status` | `PredictionStatus` | No | `PENDING` | enum value |
| `model_version` | `str` | Yes | `None` | max 50 chars |
| `requested_at` | `datetime` | No **[NEW]** | `utcnow()` | UTC, timestamp when prediction was requested |
| `completed_at` | `datetime` | Yes **[NEW]** | `None` | UTC, set when status → COMPLETED or FAILED |
| `created_at` | `datetime` | No | `utcnow()` | UTC |
| `updated_at` | `datetime` | No | `utcnow()` | UTC |
| `deleted_at` | `datetime` | Yes **[NEW]** | `None` | UTC, set on soft delete |

> `requested_at` is set at creation time, semantically equivalent to `created_at` but named to
> express domain intent (when was the prediction job triggered?).
> `completed_at` is set by the service when transitioning to COMPLETED or FAILED,
> enabling model latency calculation: `completed_at - requested_at`.

---

### 1.6 Route

**Purpose:**
A named, ordered path through one or more traffic segments.
Used for route optimization, alternate route suggestions, and travel time estimation.
A route is a container; it gains meaning through its ordered `RouteSegment` association records.
`is_active` controls visibility; `deleted_at` adds a full soft-delete audit trail.

| Field | Python Type | Nullable | Default | Validation |
|-------|------------|----------|---------|-----------|
| `id` | `uuid.UUID` **[REVISED: was int]** | No | `uuid4()` | PK |
| `name` | `str` | No | — | 2–150 chars |
| `origin_name` | `str` | No | — | 2–255 chars |
| `destination_name` | `str` | No | — | 2–255 chars |
| `total_distance_km` | `float` | No | — | > 0.0 |
| `is_active` | `bool` | No | `True` | business toggle; hides without deleting |
| `created_at` | `datetime` | No | `utcnow()` | UTC |
| `updated_at` | `datetime` | No | `utcnow()` | UTC |
| `deleted_at` | `datetime` | Yes **[NEW]** | `None` | UTC, set on soft delete |

---

### 1.7 RouteSegment

**Purpose:**
Association record linking a Route to an ordered sequence of TrafficSegments.
Expresses "Route R passes through Segment S in position N."
This is a pure join entity with an ordering field — not a business entity in itself.
Not soft-deleted: if a segment is removed from a route, the join row is hard-deleted.

| Field | Python Type | Nullable | Default | Validation |
|-------|------------|----------|---------|-----------|
| `id` | `uuid.UUID` **[REVISED: was int]** | No | `uuid4()` | PK |
| `route_id` | `uuid.UUID` (FK) **[REVISED]** | No | — | references `routes.id` |
| `segment_id` | `uuid.UUID` (FK) **[REVISED]** | No | — | references `traffic_segments.id` |
| `sequence_order` | `int` | No | — | >= 1 |

---

## 2. Database Design

### Soft-Delete Convention (applies to all tables with `deleted_at`)

- All repository `get_by_id` and `get_all` queries **always filter `deleted_at IS NULL`** unless explicitly querying deleted records.
- `soft_delete` sets `deleted_at = now()` and `updated_at = now()`. No physical `DELETE` is issued.
- `deleted_at` is indexed on every table that carries it.

### PostgreSQL ENUM Convention

Native PostgreSQL ENUM types are used instead of `VARCHAR + CHECK` constraints.
Each enum type is created with a `CREATE TYPE` statement **before** the first table that uses it.
See Section 4 for the full PostgreSQL type names.

---

### 2.1 `traffic_cameras`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `UUID` **[REVISED]** | No | `gen_random_uuid()` | Primary key |
| `name` | `VARCHAR(100)` | No | — | |
| `location_name` | `VARCHAR(255)` | No | — | |
| `latitude` | `DOUBLE PRECISION` | No | — | |
| `longitude` | `DOUBLE PRECISION` | No | — | |
| `status` | `camera_status` **[REVISED: native ENUM]** | No | `'ACTIVE'` | |
| `description` | `TEXT` | Yes | NULL | |
| `installed_at` | `TIMESTAMPTZ` | No | `now()` | |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | |
| `deleted_at` | `TIMESTAMPTZ` **[NEW]** | Yes | NULL | Soft delete timestamp |

**Primary Key:** `id` (UUID)
**Indexes:**
- `ix_traffic_cameras_status` on `(status)`
- `ix_traffic_cameras_deleted_at` on `(deleted_at)` **[NEW]**
**Constraints:**
- `ck_cameras_latitude` — `latitude BETWEEN -90 AND 90`
- `ck_cameras_longitude` — `longitude BETWEEN -180 AND 180`
- Status enforced by native ENUM type `camera_status` — no separate CHECK constraint needed **[REVISED]**
**FK Delete Behavior:**
- Traffic segments referencing this table use `ON DELETE RESTRICT`.
  Cameras are soft-deleted rather than physically removed to preserve referential integrity.

---

### 2.2 `traffic_segments`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `UUID` **[REVISED]** | No | `gen_random_uuid()` | Primary key |
| `name` | `VARCHAR(150)` | No | — | |
| `start_point` | `VARCHAR(255)` | No | — | Human-readable start name |
| `end_point` | `VARCHAR(255)` | No | — | Human-readable end name |
| `start_latitude` | `DOUBLE PRECISION` **[NEW]** | No | — | |
| `start_longitude` | `DOUBLE PRECISION` **[NEW]** | No | — | |
| `end_latitude` | `DOUBLE PRECISION` **[NEW]** | No | — | |
| `end_longitude` | `DOUBLE PRECISION` **[NEW]** | No | — | |
| `length_km` | `DOUBLE PRECISION` | No | — | CHECK > 0 |
| `speed_limit_kmh` | `INTEGER` | No | — | CHECK 1–300 |
| `camera_id` | `UUID` **[REVISED]** | Yes | NULL | FK → `traffic_cameras.id` |
| `status` | `segment_status` **[REVISED: native ENUM]** | No | `'ACTIVE'` | |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | |
| `deleted_at` | `TIMESTAMPTZ` **[NEW]** | Yes | NULL | Soft delete timestamp |

**Primary Key:** `id` (UUID)
**Foreign Keys:**
- `camera_id` → `traffic_cameras.id` ON DELETE SET NULL (if camera is physically removed, camera_id becomes NULL)
**Indexes:**
- `ix_traffic_segments_status` on `(status)`
- `ix_traffic_segments_camera_id` on `(camera_id)`
- `ix_traffic_segments_deleted_at` on `(deleted_at)` **[NEW]**
**Constraints:**
- `ck_segments_length` — `length_km > 0`
- `ck_segments_speed_limit` — `speed_limit_kmh BETWEEN 1 AND 300`
- `ck_segments_start_latitude` — `start_latitude BETWEEN -90 AND 90` **[NEW]**
- `ck_segments_start_longitude` — `start_longitude BETWEEN -180 AND 180` **[NEW]**
- `ck_segments_end_latitude` — `end_latitude BETWEEN -90 AND 90` **[NEW]**
- `ck_segments_end_longitude` — `end_longitude BETWEEN -180 AND 180` **[NEW]**
- Status enforced by native ENUM type `segment_status` **[REVISED]**
**FK Delete Behavior:**
- Child tables (readings, alerts, predictions, route_segments) referencing this table use `ON DELETE RESTRICT`.
  Segments are soft-deleted rather than physically removed.

---

### 2.3 `traffic_readings`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `BIGSERIAL` | No | auto | Primary key — retained integer for performance |
| `segment_id` | `UUID` **[REVISED]** | No | — | FK → `traffic_segments.id` |
| `vehicle_count` | `INTEGER` | No | — | CHECK >= 0 |
| `average_speed_kmh` | `DOUBLE PRECISION` | No | — | CHECK >= 0 |
| `congestion_level` | `congestion_level` **[REVISED: native ENUM]** | No | — | |
| `occupancy_percent` | `DOUBLE PRECISION` | Yes | NULL | CHECK 0–100 |
| `recorded_at` | `TIMESTAMPTZ` | No | — | Time of measurement |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Time of DB insertion |

**Primary Key:** `id` (BIGSERIAL — integer retained for insert throughput)
**Foreign Keys:**
- `segment_id` → `traffic_segments.id` ON DELETE RESTRICT
  Readings reference a segment UUID; the segment must be soft-deleted, not physically removed.
**Indexes:**
- `ix_traffic_readings_segment_id` on `(segment_id)`
- `ix_traffic_readings_recorded_at` on `(recorded_at DESC)`
- `ix_traffic_readings_segment_recorded` on `(segment_id, recorded_at DESC)` — primary query path
**Constraints:**
- `ck_readings_vehicle_count` — `vehicle_count >= 0`
- `ck_readings_speed` — `average_speed_kmh >= 0`
- `ck_readings_occupancy` — `occupancy_percent BETWEEN 0 AND 100`
- Congestion level enforced by native ENUM type `congestion_level` **[REVISED]**

> Readings are append-only. No UPDATE, no DELETE, no `deleted_at`.

---

### 2.4 `alerts`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `UUID` **[REVISED]** | No | `gen_random_uuid()` | Primary key |
| `segment_id` | `UUID` **[REVISED]** | No | — | FK → `traffic_segments.id` |
| `created_by` | `UUID` | Yes | NULL | FK → `users.id` |
| `title` | `VARCHAR(200)` | No | — | |
| `description` | `TEXT` | Yes | NULL | |
| `alert_type` | `alert_type` **[REVISED: native ENUM]** | No | — | |
| `severity` | `alert_severity` **[REVISED: native ENUM]** | No | — | |
| `status` | `alert_status` **[REVISED: native ENUM]** | No | `'ACTIVE'` | |
| `resolved_at` | `TIMESTAMPTZ` | Yes | NULL | Set when status → RESOLVED |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | |
| `deleted_at` | `TIMESTAMPTZ` **[NEW]** | Yes | NULL | Soft delete timestamp |

**Primary Key:** `id` (UUID)
**Foreign Keys:**
- `segment_id` → `traffic_segments.id` ON DELETE RESTRICT
- `created_by` → `users.id` ON DELETE SET NULL
**Indexes:**
- `ix_alerts_segment_id` on `(segment_id)`
- `ix_alerts_status` on `(status)`
- `ix_alerts_severity` on `(severity)`
- `ix_alerts_created_by` on `(created_by)`
- `ix_alerts_created_at` on `(created_at DESC)`
- `ix_alerts_deleted_at` on `(deleted_at)` **[NEW]**
**Constraints:**
- All enum columns enforced by native ENUM types — no separate CHECK constraints needed **[REVISED]**

---

### 2.5 `traffic_predictions`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `UUID` **[REVISED]** | No | `gen_random_uuid()` | Primary key |
| `segment_id` | `UUID` **[REVISED]** | No | — | FK → `traffic_segments.id` |
| `predicted_congestion_level` | `congestion_level` **[REVISED: native ENUM]** | Yes | NULL | Set on completion |
| `predicted_vehicle_count` | `INTEGER` | Yes | NULL | |
| `predicted_avg_speed_kmh` | `DOUBLE PRECISION` | Yes | NULL | |
| `confidence_score` | `DOUBLE PRECISION` | Yes | NULL | CHECK 0.0–1.0 |
| `prediction_for` | `TIMESTAMPTZ` | No | — | Future timestamp being predicted |
| `horizon_minutes` | `INTEGER` | No | — | CHECK > 0 |
| `status` | `prediction_status` **[REVISED: native ENUM]** | No | `'PENDING'` | |
| `model_version` | `VARCHAR(50)` | Yes | NULL | |
| `requested_at` | `TIMESTAMPTZ` **[NEW]** | No | `now()` | When prediction job was triggered |
| `completed_at` | `TIMESTAMPTZ` **[NEW]** | Yes | NULL | When status transitioned to COMPLETED or FAILED |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | |
| `deleted_at` | `TIMESTAMPTZ` **[NEW]** | Yes | NULL | Soft delete timestamp |

**Primary Key:** `id` (UUID)
**Foreign Keys:**
- `segment_id` → `traffic_segments.id` ON DELETE RESTRICT
**Indexes:**
- `ix_predictions_segment_id` on `(segment_id)`
- `ix_predictions_status` on `(status)`
- `ix_predictions_prediction_for` on `(prediction_for)`
- `ix_predictions_segment_for` on `(segment_id, prediction_for)`
- `ix_predictions_deleted_at` on `(deleted_at)` **[NEW]**
**Constraints:**
- `ck_predictions_confidence` — `confidence_score BETWEEN 0.0 AND 1.0`
- `ck_predictions_horizon` — `horizon_minutes > 0`
- Enum columns enforced by native ENUM types **[REVISED]**

---

### 2.6 `routes`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `UUID` **[REVISED]** | No | `gen_random_uuid()` | Primary key |
| `name` | `VARCHAR(150)` | No | — | |
| `origin_name` | `VARCHAR(255)` | No | — | |
| `destination_name` | `VARCHAR(255)` | No | — | |
| `total_distance_km` | `DOUBLE PRECISION` | No | — | CHECK > 0 |
| `is_active` | `BOOLEAN` | No | `TRUE` | Business toggle; hides without deleting |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | |
| `deleted_at` | `TIMESTAMPTZ` **[NEW]** | Yes | NULL | Soft delete timestamp |

**Primary Key:** `id` (UUID)
**Indexes:**
- `ix_routes_is_active` on `(is_active)`
- `ix_routes_deleted_at` on `(deleted_at)` **[NEW]**
**Constraints:**
- `ck_routes_distance` — `total_distance_km > 0`
**FK Delete Behavior:**
- `route_segments` rows referencing this table use `ON DELETE CASCADE`.
  When a route is physically removed (which only happens if `deleted_at` was previously set
  and an admin purge is run), its join rows are also removed.

---

### 2.7 `route_segments`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `UUID` **[REVISED]** | No | `gen_random_uuid()` | Primary key |
| `route_id` | `UUID` **[REVISED]** | No | — | FK → `routes.id` |
| `segment_id` | `UUID` **[REVISED]** | No | — | FK → `traffic_segments.id` |
| `sequence_order` | `INTEGER` | No | — | CHECK >= 1 |

**Primary Key:** `id` (UUID)
**Foreign Keys:**
- `route_id` → `routes.id` ON DELETE CASCADE
- `segment_id` → `traffic_segments.id` ON DELETE RESTRICT
**Indexes:**
- `ix_route_segments_route_id` on `(route_id)`
- `ix_route_segments_segment_id` on `(segment_id)`
**Unique Constraint:** `uq_route_segment_order` on `(route_id, sequence_order)`
**Constraints:**
- `ck_route_segments_order` — `sequence_order >= 1`

> No `deleted_at`. Removing a segment from a route is an explicit hard-delete of this join row.

---

## 3. Entity Relationships

### 3.1 Relationship Summary

```
users (Dev #1, FROZEN)
  └──< alerts.created_by          (One User → Many Alerts; SET NULL on user delete)

traffic_cameras
  └──< traffic_segments.camera_id  (One Camera → Many Segments; SET NULL on physical delete)

traffic_segments  [CENTRAL ENTITY — soft deleted]
  ├──< traffic_readings.segment_id (One Segment → Many Readings; RESTRICT physical delete)
  ├──< alerts.segment_id           (One Segment → Many Alerts;   RESTRICT physical delete)
  ├──< traffic_predictions.segment_id (One Segment → Many Predictions; RESTRICT physical delete)
  └──< route_segments.segment_id   (One Segment → Many RouteSegment join rows; RESTRICT physical delete)

routes [soft deleted]
  └──< route_segments.route_id     (One Route → Many RouteSegment join rows; CASCADE on physical delete)
```

### 3.2 Detailed Relationship Descriptions

**TrafficCamera → TrafficSegment (One-to-Many)**
- One camera can monitor multiple segments.
- A segment may have at most one camera (`camera_id` nullable).
- Cameras are soft-deleted. If a camera is *physically* purged, segments survive with `camera_id = NULL`.
- Normal operational "deletion" of a camera sets `deleted_at` — segments are unaffected.

**TrafficSegment → TrafficReading (One-to-Many)**
- One segment generates many readings over time (high-volume).
- Readings reference the segment UUID. Segments are soft-deleted — the FK is `ON DELETE RESTRICT`
  so a segment with readings can never be physically deleted by accident.
- All readings associated with a soft-deleted segment remain queryable for analytics.

**TrafficSegment → Alert (One-to-Many)**
- One segment can have many alerts simultaneously.
- Segment is soft-deleted rather than physically removed. FK is `ON DELETE RESTRICT`.
- Alert `deleted_at` is independent of segment `deleted_at`.

**User → Alert (One-to-Many via `created_by`)**
- A traffic controller or admin creates many alerts.
- The `created_by` FK is nullable with `SET NULL` — alert history is preserved if the user is deleted.

**TrafficSegment → TrafficPrediction (One-to-Many)**
- One segment can have many predictions (one per future time horizon).
- FK is `ON DELETE RESTRICT`. Predictions survive segment soft deletion.

**Route → RouteSegment → TrafficSegment (Many-to-Many through `route_segments`)**
- A route passes through many segments in a specific order.
- A segment can appear in many routes.
- `route_segments` is the ordered join table (no `deleted_at`; removal is hard delete).
- If a route is physically purged, its `route_segments` rows cascade-delete.
- Segment FK is `ON DELETE RESTRICT` — a segment that is part of a route cannot be physically purged.

### 3.3 ER-Style Diagram (Text)

```
[users] 1──────────────────────────────────* [alerts]
                                                 │
[traffic_cameras] 1────────* [traffic_segments] 1──────* [traffic_readings]
                                    │
                                    1──────────────────────────* [alerts]
                                    │
                                    1──────────────────────────* [traffic_predictions]
                                    │
                              [route_segments] *──────1 [routes]
```

---

## 4. Enumerations

### PostgreSQL ENUM Type Names

Native PostgreSQL ENUM types replace `VARCHAR + CHECK` constraints.
Each type is created once via `CREATE TYPE` in the first migration that needs it.

| Python Enum Class | PostgreSQL Type Name | Created in Migration |
|-------------------|---------------------|---------------------|
| `CameraStatus` | `camera_status` | `0002_create_traffic_cameras` |
| `SegmentStatus` | `segment_status` | `0003_create_traffic_segments` |
| `CongestionLevel` | `congestion_level` | `0003_create_traffic_segments` |
| `AlertType` | `alert_type` | `0007_create_alerts` |
| `AlertSeverity` | `alert_severity` | `0007_create_alerts` |
| `AlertStatus` | `alert_status` | `0007_create_alerts` |
| `PredictionStatus` | `prediction_status` | `0008_create_traffic_predictions` |

> **SQLAlchemy note (for implementation):** Use `sa.Enum(..., name="camera_status", create_type=False)`
> with `native_enum=True` and manage `CREATE TYPE` explicitly in each Alembic migration.
> `CongestionLevel` is shared between `traffic_segments`, `traffic_readings`, and
> `traffic_predictions` — it is created in `0003` (first migration to use it) and
> referenced (not recreated) in `0004` and `0008`.
> Downgrade steps must `DROP TYPE` only from the migration that created it,
> after the table using it is dropped.

---

### 4.1 `CameraStatus`

Controls the operational state of a physical camera.

| Value | Meaning |
|-------|---------|
| `ACTIVE` | Camera is online and collecting data |
| `INACTIVE` | Camera is installed but not currently operating |
| `MAINTENANCE` | Camera is undergoing planned maintenance; data unreliable |
| `OFFLINE` | Camera is unreachable or has failed unexpectedly |

---

### 4.2 `SegmentStatus`

Controls whether a road segment is available for normal monitoring.

| Value | Meaning |
|-------|---------|
| `ACTIVE` | Segment is being monitored normally |
| `INACTIVE` | Segment exists but monitoring is paused |
| `UNDER_MAINTENANCE` | Road works in progress; readings may be abnormal |
| `CLOSED` | Segment is closed to traffic (emergency, construction) |

---

### 4.3 `CongestionLevel`

Standardised traffic flow classification.
Used in `traffic_readings` (actual measurements) and `traffic_predictions` (forecasts).

| Value | Meaning | Typical Speed % of Limit |
|-------|---------|--------------------------|
| `FREE_FLOW` | Traffic moving freely | > 80% |
| `LIGHT` | Minor delays | 60–80% |
| `MODERATE` | Noticeable slowdown | 40–60% |
| `HEAVY` | Significant congestion | 20–40% |
| `STANDSTILL` | Near-zero movement | < 20% |

---

### 4.4 `AlertType`

Classifies the nature of the traffic incident.

| Value | Meaning |
|-------|---------|
| `CONGESTION` | Traffic buildup above normal thresholds |
| `ACCIDENT` | Vehicle collision or incident on the segment |
| `ROAD_CLOSURE` | Full or partial closure of the road |
| `WEATHER` | Weather condition affecting road safety (fog, ice, flood) |
| `EMERGENCY` | Police, fire, or other emergency services operation |
| `ROADWORKS` | Planned construction or maintenance activity |

---

### 4.5 `AlertSeverity`

Indicates urgency and impact of the alert.

| Value | Meaning |
|-------|---------|
| `LOW` | Minor inconvenience; no immediate action required |
| `MEDIUM` | Noticeable impact; alternate routes advisable |
| `HIGH` | Significant disruption; expect major delays |
| `CRITICAL` | Road impassable or life-safety risk present |

---

### 4.6 `AlertStatus`

Tracks the operational lifecycle of an alert.

| Value | Meaning |
|-------|---------|
| `ACTIVE` | Alert is live and relevant |
| `RESOLVED` | Incident has ended; road returned to normal |
| `DISMISSED` | Alert was retracted (e.g. false report) |

---

### 4.7 `PredictionStatus`

Tracks the processing lifecycle of a prediction job.

| Value | Meaning |
|-------|---------|
| `PENDING` | Prediction requested but model has not yet produced output |
| `COMPLETED` | Model returned results; prediction fields populated; `completed_at` set |
| `FAILED` | Model encountered an error; prediction fields remain NULL; `completed_at` set |

---

## 5. REST API Design

All routes are registered under `/api/v1`.
Auth abbreviations: **PUB** = any authenticated user, **TC** = TRAFFIC_CONTROLLER, **ADM** = ADMIN.
All `{*_id}` path parameters are now UUID strings.

---

### 5.1 Traffic Cameras — `/api/v1/cameras`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/cameras` | PUB | List non-deleted cameras (paginated, filterable by status) |
| `GET` | `/cameras/{camera_id}` | PUB | Get single camera by UUID |
| `POST` | `/cameras` | ADM | Create a new camera |
| `PUT` | `/cameras/{camera_id}` | ADM | Update camera fields |
| `DELETE` | `/cameras/{camera_id}` | ADM | Soft-delete camera (sets `deleted_at`) |

**Request Schema — CameraCreate:**
```json
{
  "name": "Highway 1 North Camera",
  "location_name": "NH-1 near Toll Plaza 3",
  "latitude": 28.6139,
  "longitude": 77.2090,
  "status": "ACTIVE",
  "description": "Overhead gantry camera, 4K resolution"
}
```

**Response Schema — CameraRead:**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "Highway 1 North Camera",
  "location_name": "NH-1 near Toll Plaza 3",
  "latitude": 28.6139,
  "longitude": 77.2090,
  "status": "ACTIVE",
  "description": "Overhead gantry camera, 4K resolution",
  "installed_at": "2026-01-15T08:00:00Z",
  "created_at": "2026-01-15T08:00:00Z",
  "updated_at": "2026-01-15T08:00:00Z"
}
```

> `deleted_at` is never exposed in API responses. Soft-deleted cameras are invisible to all consumers.

**Status Codes:**
| Code | When |
|------|------|
| 200 | Successful GET |
| 201 | Camera created |
| 204 | Camera soft-deleted |
| 422 | Validation failure |
| 403 | Insufficient role |
| 404 | Camera not found |

---

### 5.2 Traffic Segments — `/api/v1/segments`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/segments` | PUB | List non-deleted segments (filterable by status, camera_id) |
| `GET` | `/segments/{segment_id}` | PUB | Get segment detail |
| `GET` | `/segments/{segment_id}/latest-reading` | PUB | Get most recent reading for segment |
| `POST` | `/segments` | ADM | Create segment |
| `PUT` | `/segments/{segment_id}` | ADM | Update segment |
| `DELETE` | `/segments/{segment_id}` | ADM | Soft-delete segment |

**Request Schema — SegmentCreate:**
```json
{
  "name": "NH-1 Sector 14 to Sector 18",
  "start_point": "Sector 14 Flyover",
  "end_point": "Sector 18 Interchange",
  "start_latitude": 28.6820,
  "start_longitude": 77.1025,
  "end_latitude": 28.6530,
  "end_longitude": 77.0840,
  "length_km": 4.2,
  "speed_limit_kmh": 80,
  "camera_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "ACTIVE"
}
```

**Response Schema — SegmentRead:**
```json
{
  "id": "f7e6d5c4-b3a2-1098-fedc-ba9876543210",
  "name": "NH-1 Sector 14 to Sector 18",
  "start_point": "Sector 14 Flyover",
  "end_point": "Sector 18 Interchange",
  "start_latitude": 28.6820,
  "start_longitude": 77.1025,
  "end_latitude": 28.6530,
  "end_longitude": 77.0840,
  "length_km": 4.2,
  "speed_limit_kmh": 80,
  "camera_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "ACTIVE",
  "created_at": "2026-01-20T09:00:00Z",
  "updated_at": "2026-01-20T09:00:00Z"
}
```

---

### 5.3 Traffic Readings — `/api/v1/readings`

Unchanged from v1 except `segment_id` in request/response is now a UUID string.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/readings` | TC, ADM | Submit a new traffic reading |
| `GET` | `/readings` | PUB | List readings (filterable by segment UUID, congestion level, date range) |
| `GET` | `/readings/{reading_id}` | PUB | Get single reading (reading_id is still integer) |

**Request Schema — ReadingCreate:**
```json
{
  "segment_id": "f7e6d5c4-b3a2-1098-fedc-ba9876543210",
  "vehicle_count": 312,
  "average_speed_kmh": 38.5,
  "congestion_level": "HEAVY",
  "occupancy_percent": 74.2,
  "recorded_at": "2026-07-31T08:15:00Z"
}
```

**Response Schema — ReadingRead:**
```json
{
  "id": 10041,
  "segment_id": "f7e6d5c4-b3a2-1098-fedc-ba9876543210",
  "vehicle_count": 312,
  "average_speed_kmh": 38.5,
  "congestion_level": "HEAVY",
  "occupancy_percent": 74.2,
  "recorded_at": "2026-07-31T08:15:00Z",
  "created_at": "2026-07-31T08:15:02Z"
}
```

---

### 5.4 Alerts — `/api/v1/alerts`

`DELETE` now performs a soft-delete (sets `deleted_at`), not a hard delete.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/alerts` | PUB | List non-deleted alerts (filterable by status, severity, type, segment) |
| `GET` | `/alerts/{alert_id}` | PUB | Get single alert |
| `POST` | `/alerts` | TC, ADM | Create alert |
| `PUT` | `/alerts/{alert_id}` | TC, ADM | Update alert title/description/severity |
| `PATCH` | `/alerts/{alert_id}/resolve` | TC, ADM | Mark alert as RESOLVED |
| `PATCH` | `/alerts/{alert_id}/dismiss` | TC, ADM | Mark alert as DISMISSED |
| `DELETE` | `/alerts/{alert_id}` | ADM | Soft-delete alert (sets `deleted_at`) |

**Response Schema — AlertRead:**
```json
{
  "id": "c0ffee00-dead-beef-cafe-123456789abc",
  "segment_id": "f7e6d5c4-b3a2-1098-fedc-ba9876543210",
  "created_by": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Heavy congestion approaching peak hour",
  "description": "Vehicle count 312, speed dropped to 38 kmh.",
  "alert_type": "CONGESTION",
  "severity": "HIGH",
  "status": "ACTIVE",
  "resolved_at": null,
  "created_at": "2026-07-31T08:20:00Z",
  "updated_at": "2026-07-31T08:20:00Z"
}
```

---

### 5.5 Traffic Predictions — `/api/v1/predictions`

Response schema now includes `requested_at` and `completed_at`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/predictions` | PUB | List non-deleted predictions (filterable by segment, status, horizon) |
| `GET` | `/predictions/{prediction_id}` | PUB | Get single prediction |
| `POST` | `/predictions` | TC, ADM | Request a new prediction |
| `PATCH` | `/predictions/{prediction_id}/complete` | TC, ADM | Submit model output |
| `PATCH` | `/predictions/{prediction_id}/fail` | TC, ADM | Mark prediction as FAILED |
| `GET` | `/predictions/segment/{segment_id}/upcoming` | PUB | Upcoming predictions for segment |
| `DELETE` | `/predictions/{prediction_id}` | ADM | Soft-delete prediction |

**Request Schema — PredictionCreate:**
```json
{
  "segment_id": "f7e6d5c4-b3a2-1098-fedc-ba9876543210",
  "prediction_for": "2026-07-31T09:00:00Z",
  "horizon_minutes": 45,
  "model_version": "v2.1.0"
}
```

**Response Schema — PredictionRead:**
```json
{
  "id": "aaaabbbb-cccc-dddd-eeee-ffffffffffff",
  "segment_id": "f7e6d5c4-b3a2-1098-fedc-ba9876543210",
  "predicted_congestion_level": "HEAVY",
  "predicted_vehicle_count": 380,
  "predicted_avg_speed_kmh": 32.0,
  "confidence_score": 0.87,
  "prediction_for": "2026-07-31T09:00:00Z",
  "horizon_minutes": 45,
  "status": "COMPLETED",
  "model_version": "v2.1.0",
  "requested_at": "2026-07-31T08:15:00Z",
  "completed_at": "2026-07-31T08:16:30Z",
  "created_at": "2026-07-31T08:15:00Z",
  "updated_at": "2026-07-31T08:16:30Z"
}
```

---

### 5.6 Routes — `/api/v1/routes`

Unchanged from v1 except IDs are UUID strings. `DELETE` now soft-deletes.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/routes` | PUB | List non-deleted active routes |
| `GET` | `/routes/{route_id}` | PUB | Get route with ordered segment list |
| `GET` | `/routes/{route_id}/traffic` | PUB | Aggregate current traffic status across route segments |
| `POST` | `/routes` | ADM | Create route |
| `PUT` | `/routes/{route_id}` | ADM | Update route metadata |
| `POST` | `/routes/{route_id}/segments` | ADM | Add a segment to the route |
| `DELETE` | `/routes/{route_id}/segments/{segment_id}` | ADM | Remove a segment (hard-deletes join row) |
| `DELETE` | `/routes/{route_id}` | ADM | Soft-delete route (sets `deleted_at`) |

---

### 5.7 Analytics — `/api/v1/analytics`

Unchanged from v1. No new fields in responses.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/analytics/summary` | PUB | System-wide snapshot |
| `GET` | `/analytics/congestion-heatmap` | PUB | All segments with latest congestion level |
| `GET` | `/analytics/peak-hours` | PUB | Hourly vehicle count averages |
| `GET` | `/analytics/segments/{segment_id}/history` | PUB | Historical readings (date range, aggregated) |
| `GET` | `/analytics/segments/{segment_id}/trends` | TC, ADM | Statistical trends |
| `GET` | `/analytics/reports` | TC, ADM | Full analytics report |

---

## 6. Repository Design

Repositories perform ONLY database operations via async SQLAlchemy.
No business logic. No HTTP concepts. No exception raising for business rules.

### Soft-Delete Convention for Repositories

Every repository that manages a soft-deleted entity follows these rules:

- **`get_by_id`** and **`get_all`** always include `WHERE deleted_at IS NULL` implicitly.
- **`soft_delete(entity)`** sets `entity.deleted_at = utcnow()` + `entity.updated_at = utcnow()`, calls `flush()`.
- No `delete()` hard-delete method is exposed for soft-delete entities.
  Hard deletion of soft-deleted records is an offline administrative operation outside the API.

---

### 6.1 `CameraRepository`

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `get_by_id` | `camera_id: uuid.UUID` **[REVISED]** | `TrafficCamera \| None` | Fetch where `deleted_at IS NULL` |
| `get_all` | `status: CameraStatus \| None, skip: int, limit: int` | `Sequence[TrafficCamera]` | Paginated, filters `deleted_at IS NULL` |
| `create` | `name, location_name, latitude, longitude, status, description, installed_at` | `TrafficCamera` | Insert and flush |
| `update` | `camera: TrafficCamera, **fields` | `TrafficCamera` | Setattr + flush + refresh |
| `soft_delete` **[REVISED: was `delete`]** | `camera: TrafficCamera` | `None` | Sets `deleted_at = utcnow()`, flush |
| `count_by_status` | `status: CameraStatus` | `int` | Count cameras in given state (excludes deleted) |

---

### 6.2 `SegmentRepository`

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `get_by_id` | `segment_id: uuid.UUID` **[REVISED]** | `TrafficSegment \| None` | Fetch where `deleted_at IS NULL` |
| `get_all` | `status, camera_id: uuid.UUID \| None, skip, limit` **[REVISED]** | `Sequence[TrafficSegment]` | Paginated, filters `deleted_at IS NULL` |
| `get_by_camera_id` | `camera_id: uuid.UUID` **[REVISED]** | `Sequence[TrafficSegment]` | All non-deleted segments for a camera |
| `create` | `name, start_point, end_point, start_latitude, start_longitude, end_latitude, end_longitude, length_km, speed_limit_kmh, camera_id, status` **[REVISED: coords added]** | `TrafficSegment` | Insert + flush |
| `update` | `segment: TrafficSegment, **fields` | `TrafficSegment` | Setattr + flush + refresh |
| `soft_delete` **[REVISED: was `delete`]** | `segment: TrafficSegment` | `None` | Sets `deleted_at = utcnow()`, flush |

---

### 6.3 `ReadingRepository`

Unchanged in behaviour; FK param types now `uuid.UUID`.

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `get_by_id` | `reading_id: int` | `TrafficReading \| None` | Single reading (integer PK) |
| `get_latest_for_segment` | `segment_id: uuid.UUID` **[REVISED]** | `TrafficReading \| None` | Most recent reading by `recorded_at` |
| `get_by_segment` | `segment_id: uuid.UUID, from_dt, to_dt, congestion_level, skip, limit` **[REVISED]** | `Sequence[TrafficReading]` | Time-range query for one segment |
| `get_all` | `segment_id: uuid.UUID \| None, from_dt, to_dt, congestion_level, skip, limit` **[REVISED]** | `Sequence[TrafficReading]` | Cross-segment list |
| `create` | `segment_id: uuid.UUID, vehicle_count, average_speed_kmh, congestion_level, occupancy_percent, recorded_at` **[REVISED]** | `TrafficReading` | Insert + flush (no update ever) |
| `get_hourly_averages` | `segment_id: uuid.UUID \| None, from_dt, to_dt` **[REVISED]** | `Sequence[dict]` | Aggregated averages per hour |
| `get_latest_per_segment` | *(no args)* | `Sequence[dict]` | One latest reading per non-deleted segment |
| `count_by_congestion_level` | *(no args)* | `dict[str, int]` | **[NEW]** Count latest readings per congestion level (used by analytics summary) |

---

### 6.4 `AlertRepository`

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `get_by_id` | `alert_id: uuid.UUID` **[REVISED]** | `Alert \| None` | Fetch where `deleted_at IS NULL` |
| `get_all` | `status, severity, alert_type, segment_id: uuid.UUID \| None, skip, limit` **[REVISED]** | `Sequence[Alert]` | Filtered, paginated, `deleted_at IS NULL` |
| `get_active_count` | *(no args)* | `int` | Count of ACTIVE, non-deleted alerts |
| `get_active_by_severity` | `severity: AlertSeverity` | `int` | Count for a given severity (non-deleted) |
| `create` | `segment_id: uuid.UUID, created_by: uuid.UUID \| None, title, description, alert_type, severity` **[REVISED]** | `Alert` | Insert + flush |
| `update` | `alert: Alert, **fields` | `Alert` | Setattr + flush + refresh |
| `soft_delete` **[REVISED: was `delete`]** | `alert: Alert` | `None` | Sets `deleted_at = utcnow()`, flush |

---

### 6.5 `PredictionRepository`

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `get_by_id` | `prediction_id: uuid.UUID` **[REVISED]** | `TrafficPrediction \| None` | Fetch where `deleted_at IS NULL` |
| `get_all` | `segment_id: uuid.UUID \| None, status, skip, limit` **[REVISED]** | `Sequence[TrafficPrediction]` | Filtered, paginated, `deleted_at IS NULL` |
| `get_upcoming_for_segment` | `segment_id: uuid.UUID` **[REVISED]** | `Sequence[TrafficPrediction]` | Non-deleted PENDING/COMPLETED where `prediction_for > now()` |
| `create` | `segment_id: uuid.UUID, prediction_for, horizon_minutes, model_version` **[REVISED]** | `TrafficPrediction` | Insert + flush; `status=PENDING`, `requested_at=utcnow()` set automatically |
| `update` | `prediction: TrafficPrediction, **fields` | `TrafficPrediction` | Setattr + flush + refresh |
| `soft_delete` **[NEW]** | `prediction: TrafficPrediction` | `None` | Sets `deleted_at = utcnow()`, flush |

---

### 6.6 `RouteRepository`

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `get_by_id` | `route_id: uuid.UUID` **[REVISED]** | `Route \| None` | Fetch where `deleted_at IS NULL` |
| `get_by_id_with_segments` | `route_id: uuid.UUID` **[REVISED]** | `Route \| None` | Route + eagerly-loaded RouteSegment list |
| `get_all` | `is_active: bool \| None, skip, limit` | `Sequence[Route]` | Paginated, filters `deleted_at IS NULL` |
| `create` | `name, origin_name, destination_name, total_distance_km` | `Route` | Insert + flush |
| `update` | `route: Route, **fields` | `Route` | Setattr + flush + refresh |
| `soft_delete` **[REVISED: was `delete`]** | `route: Route` | `None` | Sets `deleted_at = utcnow()`, flush |
| `add_segment` | `route_id: uuid.UUID, segment_id: uuid.UUID, sequence_order: int` **[REVISED]** | `RouteSegment` | Insert RouteSegment join row |
| `remove_segment` | `route_id: uuid.UUID, segment_id: uuid.UUID` **[REVISED]** | `None` | Hard-delete RouteSegment join row |
| `get_segment_ids_for_route` | `route_id: uuid.UUID` **[REVISED]** | `Sequence[uuid.UUID]` | Ordered UUIDs for the route |

---

### ~~6.7 `AnalyticsRepository`~~ — REMOVED

**[REMOVED in v2.0]**

The `AnalyticsRepository` has been eliminated. Analytics queries are now executed by
`AnalyticsService` directly through the existing repositories:
- `ReadingRepository` — for heatmap, history, peak hours, and congestion distribution
- `AlertRepository` — for alert counts and severity breakdown
- `SegmentRepository` — for total segment count and status distribution
- `PredictionRepository` — for prediction summary in the full report

This eliminates a repository with no ORM model of its own, avoids duplicating query
logic already present in `ReadingRepository` and `AlertRepository`, and keeps the
"one repository per model" rule intact.

---

## 7. Service Design

Services own all business logic.
They receive repositories via constructor injection.
They are HTTP-agnostic — no FastAPI, no Request, no Response.
They raise domain exceptions (defined in Section 10).

---

### 7.1 `CameraService`

**Dependencies:** `CameraRepository`

| Method | Business Logic |
|--------|---------------|
| `list_cameras(status, skip, limit)` | Delegates to repo. Returns list (all non-deleted). |
| `get_camera(camera_id: uuid.UUID)` | Raises `CameraNotFoundError` if None. |
| `create_camera(data: CameraCreate)` | Validates lat/lon ranges. Delegates to repo. Logs creation. |
| `update_camera(camera_id, data: CameraUpdate)` | Fetches camera (raises if not found). Builds partial update dict from non-None fields. Delegates to repo. |
| `delete_camera(camera_id)` | Fetches camera (raises if not found). Checks if camera has non-deleted segments referencing it (raises `CameraInUseError`). Calls `repo.soft_delete()`. |

---

### 7.2 `SegmentService`

**Dependencies:** `SegmentRepository`, `CameraRepository`

| Method | Business Logic |
|--------|---------------|
| `list_segments(status, camera_id, skip, limit)` | Validates `camera_id` exists (non-deleted) if provided. Delegates to repo. |
| `get_segment(segment_id: uuid.UUID)` | Raises `SegmentNotFoundError` if None. |
| `get_latest_reading(segment_id)` | Validates segment exists. Returns latest reading or None. |
| `create_segment(data)` | Validates `camera_id` refers to a non-deleted camera if provided. Delegates to repo with coordinate fields. |
| `update_segment(segment_id, data)` | Validates segment exists. Validates camera_id if changing. Builds update dict including any coordinate changes. Delegates to repo. |
| `delete_segment(segment_id)` | Validates segment exists. Raises `SegmentHasActiveAlertsError` if any non-deleted ACTIVE alert exists on the segment. Calls `repo.soft_delete()`. |

---

### 7.3 `ReadingService`

**Dependencies:** `ReadingRepository`, `SegmentRepository`

| Method | Business Logic |
|--------|---------------|
| `submit_reading(data: ReadingCreate)` | Validates segment exists (non-deleted). Validates `recorded_at` is not in the future. Delegates to repo. |
| `list_readings(segment_id, from_dt, to_dt, congestion_level, skip, limit)` | Validates `from_dt < to_dt` if both provided. Validates segment exists (non-deleted) if `segment_id` provided. Delegates. |
| `get_reading(reading_id: int)` | Raises `ReadingNotFoundError` if None. |

---

### 7.4 `AlertService`

**Dependencies:** `AlertRepository`, `SegmentRepository`

| Method | Business Logic |
|--------|---------------|
| `list_alerts(status, severity, alert_type, segment_id, skip, limit)` | Validates segment exists if provided. Delegates to repo. |
| `get_alert(alert_id: uuid.UUID)` | Raises `AlertNotFoundError` if None. |
| `create_alert(data: AlertCreate, created_by: uuid.UUID)` | Validates segment exists (non-deleted). Delegates to repo. Logs creation with severity. |
| `update_alert(alert_id, data: AlertUpdate)` | Validates alert exists (non-deleted). Validates status is ACTIVE. Updates non-None fields. |
| `resolve_alert(alert_id)` | Validates alert exists. Validates status is ACTIVE. Sets `status=RESOLVED`, `resolved_at=utcnow()`. |
| `dismiss_alert(alert_id)` | Validates alert exists. Validates status is ACTIVE. Sets `status=DISMISSED`. |
| `delete_alert(alert_id)` | Validates alert exists. Calls `repo.soft_delete()`. |

---

### 7.5 `PredictionService`

**Dependencies:** `PredictionRepository`, `SegmentRepository`

| Method | Business Logic |
|--------|---------------|
| `list_predictions(segment_id, status, skip, limit)` | Validates segment if provided. Delegates. |
| `get_prediction(prediction_id: uuid.UUID)` | Raises `PredictionNotFoundError` if None. |
| `get_upcoming_for_segment(segment_id)` | Validates segment exists (non-deleted). Returns upcoming predictions. |
| `create_prediction(data: PredictionCreate)` | Validates segment exists (non-deleted). Validates `prediction_for` is in the future. Delegates; `requested_at` set by repo at insert time. |
| `complete_prediction(prediction_id, data: PredictionComplete)` | Validates prediction exists. Validates status is PENDING (raises `PredictionNotPendingError`). Sets prediction result fields + `status=COMPLETED` + `completed_at=utcnow()`. |
| `fail_prediction(prediction_id)` | Validates prediction exists. Validates status is PENDING. Sets `status=FAILED` + `completed_at=utcnow()`. |
| `delete_prediction(prediction_id)` **[NEW]** | Validates prediction exists. Calls `repo.soft_delete()`. |

---

### 7.6 `RouteService`

**Dependencies:** `RouteRepository`, `SegmentRepository`

| Method | Business Logic |
|--------|---------------|
| `list_routes(is_active, skip, limit)` | Delegates to repo (non-deleted only). |
| `get_route(route_id: uuid.UUID)` | Raises `RouteNotFoundError` if None. Returns route with segments loaded. |
| `get_route_traffic(route_id)` | Fetches route. Gets segment UUIDs. Fetches latest reading per segment. Computes worst congestion level across all segments. Returns summary. |
| `create_route(data: RouteCreate)` | Validates total_distance_km > 0. Delegates to repo. |
| `update_route(route_id, data: RouteUpdate)` | Validates route exists. Updates non-None fields. |
| `add_segment_to_route(route_id, segment_id, sequence_order)` | Validates route exists (non-deleted). Validates segment exists (non-deleted). Validates `sequence_order` not already taken (raises `RouteSequenceConflictError`). Delegates to repo. |
| `remove_segment_from_route(route_id, segment_id)` | Validates route exists. Validates segment is part of the route (raises `SegmentNotInRouteError`). Delegates to repo (hard-deletes join row). |
| `delete_route(route_id)` | Validates route exists. Calls `repo.soft_delete()`. |

---

### 7.7 `AnalyticsService` **[REVISED: AnalyticsRepository removed]**

**Dependencies:** `ReadingRepository`, `AlertRepository`, `SegmentRepository`, `PredictionRepository`

`AnalyticsService` orchestrates the four existing repositories directly.
It contains only business logic — no SQL, no ORM queries of its own.

| Method | Repositories Used | Business Logic |
|--------|------------------|---------------|
| `get_summary()` | `SegmentRepository`, `AlertRepository`, `ReadingRepository` | Calls `segment_repo.count_all_non_deleted()` for segment total. Calls `alert_repo.get_active_count()` and `alert_repo.get_active_by_severity(CRITICAL)` for alert stats. Calls `reading_repo.count_by_congestion_level()` for congestion distribution. Assembles summary dict. |
| `get_congestion_heatmap()` | `ReadingRepository` | Calls `reading_repo.get_latest_per_segment()`. Returns list of per-segment current state. |
| `get_peak_hour_averages(from_dt, to_dt)` | `ReadingRepository` | Validates `from_dt < to_dt`. Max range = 30 days (raises `AnalyticsRangeExceededError`). Calls `reading_repo.get_hourly_averages(segment_id=None, from_dt, to_dt)`. |
| `get_segment_history(segment_id, from_dt, to_dt, bucket_minutes)` | `SegmentRepository`, `ReadingRepository` | Validates segment exists. Validates date range ≤ 90 days. Validates `bucket_minutes` in {5, 15, 30, 60}. Calls `reading_repo.get_by_segment(...)`. Applies time-bucketing aggregation in memory for small ranges, or delegates SQL grouping for large ranges. |
| `get_segment_trends(segment_id)` | `SegmentRepository`, `ReadingRepository` | Validates segment exists. Retrieves last 7 days of hourly aggregates. Retrieves prior 7 days. Computes delta percentage for each hour band. |
| `get_full_report(from_dt, to_dt)` | All four repositories | Validates date range ≤ 30 days. Aggregates: active segment count, active alert summary, congestion distribution, prediction completion rate (COMPLETED / total), busiest hour band. |

---

## 8. Router Design

Routers are thin. Every handler:
1. Extracts parameters (path, query, body, current user)
2. Calls one service method
3. Returns a schema

No business logic. No try/except for domain errors (those are caught by global exception handlers).

---

### 8.1 Camera Router — `app/routers/cameras.py`

```
prefix = "/cameras"
tags   = ["Traffic Cameras"]
```

| Handler | Method | Path | Calls |
|---------|--------|------|-------|
| `list_cameras` | GET | `/` | `service.list_cameras(...)` |
| `get_camera` | GET | `/{camera_id}` | `service.get_camera(camera_id)` |
| `create_camera` | POST | `/` | `service.create_camera(data)` |
| `update_camera` | PUT | `/{camera_id}` | `service.update_camera(camera_id, data)` |
| `delete_camera` | DELETE | `/{camera_id}` | `service.delete_camera(camera_id)` → 204 |

Write operations require `Depends(require_role(UserRole.ADMIN))`.

---

### 8.2 Segment Router — `app/routers/segments.py`

```
prefix = "/segments"
tags   = ["Traffic Segments"]
```

| Handler | Method | Path | Calls |
|---------|--------|------|-------|
| `list_segments` | GET | `/` | `service.list_segments(...)` |
| `get_segment` | GET | `/{segment_id}` | `service.get_segment(segment_id)` |
| `get_latest_reading` | GET | `/{segment_id}/latest-reading` | `service.get_latest_reading(segment_id)` |
| `create_segment` | POST | `/` | `service.create_segment(data)` |
| `update_segment` | PUT | `/{segment_id}` | `service.update_segment(segment_id, data)` |
| `delete_segment` | DELETE | `/{segment_id}` | `service.delete_segment(segment_id)` → 204 |

Write operations require `Depends(require_role(UserRole.ADMIN))`.

---

### 8.3 Reading Router — `app/routers/readings.py`

```
prefix = "/readings"
tags   = ["Traffic Readings"]
```

Unchanged from v1.

---

### 8.4 Alert Router — `app/routers/alerts.py`

```
prefix = "/alerts"
tags   = ["Alerts"]
```

| Handler | Method | Path | Calls |
|---------|--------|------|-------|
| `list_alerts` | GET | `/` | `service.list_alerts(...)` |
| `get_alert` | GET | `/{alert_id}` | `service.get_alert(alert_id)` |
| `create_alert` | POST | `/` | `service.create_alert(data, current_user.id)` |
| `update_alert` | PUT | `/{alert_id}` | `service.update_alert(alert_id, data)` |
| `resolve_alert` | PATCH | `/{alert_id}/resolve` | `service.resolve_alert(alert_id)` |
| `dismiss_alert` | PATCH | `/{alert_id}/dismiss` | `service.dismiss_alert(alert_id)` |
| `delete_alert` | DELETE | `/{alert_id}` | `service.delete_alert(alert_id)` → 204 (soft delete) |

---

### 8.5 Prediction Router — `app/routers/predictions.py`

```
prefix = "/predictions"
tags   = ["Traffic Predictions"]
```

| Handler | Method | Path | Calls |
|---------|--------|------|-------|
| `list_predictions` | GET | `/` | `service.list_predictions(...)` |
| `get_prediction` | GET | `/{prediction_id}` | `service.get_prediction(prediction_id)` |
| `get_upcoming_for_segment` | GET | `/segment/{segment_id}/upcoming` | `service.get_upcoming_for_segment(segment_id)` |
| `create_prediction` | POST | `/` | `service.create_prediction(data)` |
| `complete_prediction` | PATCH | `/{prediction_id}/complete` | `service.complete_prediction(prediction_id, data)` |
| `fail_prediction` | PATCH | `/{prediction_id}/fail` | `service.fail_prediction(prediction_id)` |
| `delete_prediction` **[NEW]** | DELETE | `/{prediction_id}` | `service.delete_prediction(prediction_id)` → 204 |

Write operations require `require_role(TC, ADMIN)`. Delete requires `require_role(ADMIN)`.

---

### 8.6 Route Router — `app/routers/routes.py`

Unchanged from v1.

---

### 8.7 Analytics Router — `app/routers/analytics.py`

Unchanged from v1.

---

## 9. Dependency Injection

Every module follows the same factory pattern as `auth.py`.
One dependency file per module, in `app/dependencies/`.

---

### 9.1 `app/dependencies/cameras.py`

```
get_camera_service(db: AsyncSession = Depends(get_db)) -> CameraService
    └── returns CameraService(CameraRepository(db))
```

---

### 9.2 `app/dependencies/segments.py`

```
get_segment_service(db: AsyncSession = Depends(get_db)) -> SegmentService
    └── returns SegmentService(SegmentRepository(db), CameraRepository(db))
```

---

### 9.3 `app/dependencies/readings.py`

```
get_reading_service(db: AsyncSession = Depends(get_db)) -> ReadingService
    └── returns ReadingService(ReadingRepository(db), SegmentRepository(db))
```

---

### 9.4 `app/dependencies/alerts.py`

```
get_alert_service(db: AsyncSession = Depends(get_db)) -> AlertService
    └── returns AlertService(AlertRepository(db), SegmentRepository(db))
```

---

### 9.5 `app/dependencies/predictions.py`

```
get_prediction_service(db: AsyncSession = Depends(get_db)) -> PredictionService
    └── returns PredictionService(PredictionRepository(db), SegmentRepository(db))
```

---

### 9.6 `app/dependencies/routes.py`

```
get_route_service(db: AsyncSession = Depends(get_db)) -> RouteService
    └── returns RouteService(RouteRepository(db), SegmentRepository(db))
```

---

### 9.7 `app/dependencies/analytics.py` **[REVISED]**

```
get_analytics_service(db: AsyncSession = Depends(get_db)) -> AnalyticsService
    └── returns AnalyticsService(
            ReadingRepository(db),
            AlertRepository(db),
            SegmentRepository(db),
            PredictionRepository(db)
        )
```

> `AnalyticsRepository` is no longer constructed here. The four existing repositories
> are passed directly. No new repository file is required for the analytics module.

---

### 9.8 Router Registration

In `app/routers/__init__.py`, inside the marked FUTURE MODULE ROUTERS block:

```
from app.routers.cameras     import router as cameras_router
from app.routers.segments    import router as segments_router
from app.routers.readings    import router as readings_router
from app.routers.alerts      import router as alerts_router
from app.routers.predictions import router as predictions_router
from app.routers.routes      import router as routes_router
from app.routers.analytics   import router as analytics_router

api_router.include_router(cameras_router)
api_router.include_router(segments_router)
api_router.include_router(readings_router)
api_router.include_router(alerts_router)
api_router.include_router(predictions_router)
api_router.include_router(routes_router)
api_router.include_router(analytics_router)
```

---

## 10. Exception Design

All new exceptions inherit from `AppBaseException`.
Handlers are registered in `app/core/exceptions.py` inside `register_exception_handlers()`.
No changes to the exception classes themselves from v1 — only ID types in messages change
from `int` to `uuid.UUID`.

### 10.1 Camera Exceptions

| Exception Class | Message | HTTP Code | error_code |
|----------------|---------|-----------|-----------|
| `CameraNotFoundError(camera_id: uuid.UUID)` | "Traffic camera {id} not found." | 404 | `CAMERA_NOT_FOUND` |
| `CameraInUseError(camera_id: uuid.UUID)` | "Camera {id} is assigned to active segments and cannot be deleted." | 409 | `CAMERA_IN_USE` |

### 10.2 Segment Exceptions

| Exception Class | Message | HTTP Code | error_code |
|----------------|---------|-----------|-----------|
| `SegmentNotFoundError(segment_id: uuid.UUID)` | "Traffic segment {id} not found." | 404 | `SEGMENT_NOT_FOUND` |
| `SegmentHasActiveAlertsError(segment_id: uuid.UUID)` | "Segment {id} has active alerts. Resolve them before deleting." | 409 | `SEGMENT_HAS_ACTIVE_ALERTS` |

### 10.3 Reading Exceptions

| Exception Class | Message | HTTP Code | error_code |
|----------------|---------|-----------|-----------|
| `ReadingNotFoundError(reading_id: int)` | "Traffic reading {id} not found." | 404 | `READING_NOT_FOUND` |
| `InvalidReadingTimeError()` | "Reading recorded_at cannot be in the future." | 422 | `INVALID_READING_TIME` |

### 10.4 Alert Exceptions

| Exception Class | Message | HTTP Code | error_code |
|----------------|---------|-----------|-----------|
| `AlertNotFoundError(alert_id: uuid.UUID)` | "Alert {id} not found." | 404 | `ALERT_NOT_FOUND` |
| `AlertNotActiveError(alert_id: uuid.UUID)` | "Alert {id} is not active and cannot be modified." | 409 | `ALERT_NOT_ACTIVE` |

### 10.5 Prediction Exceptions

| Exception Class | Message | HTTP Code | error_code |
|----------------|---------|-----------|-----------|
| `PredictionNotFoundError(prediction_id: uuid.UUID)` | "Prediction {id} not found." | 404 | `PREDICTION_NOT_FOUND` |
| `PredictionNotPendingError(prediction_id: uuid.UUID)` | "Prediction {id} is not in PENDING status." | 409 | `PREDICTION_NOT_PENDING` |
| `PredictionTimeInPastError()` | "prediction_for must be a future timestamp." | 422 | `PREDICTION_TIME_IN_PAST` |

### 10.6 Route Exceptions

| Exception Class | Message | HTTP Code | error_code |
|----------------|---------|-----------|-----------|
| `RouteNotFoundError(route_id: uuid.UUID)` | "Route {id} not found." | 404 | `ROUTE_NOT_FOUND` |
| `RouteSequenceConflictError(route_id, order)` | "Sequence order {order} is already taken in route {id}." | 409 | `ROUTE_SEQUENCE_CONFLICT` |
| `SegmentNotInRouteError(route_id, segment_id)` | "Segment {seg_id} is not part of route {route_id}." | 404 | `SEGMENT_NOT_IN_ROUTE` |

### 10.7 Analytics Exceptions

| Exception Class | Message | HTTP Code | error_code |
|----------------|---------|-----------|-----------|
| `AnalyticsRangeExceededError(max_days)` | "Date range exceeds the maximum of {max_days} days." | 400 | `ANALYTICS_RANGE_EXCEEDED` |
| `InvalidBucketSizeError()` | "bucket_minutes must be one of: 5, 15, 30, 60." | 422 | `INVALID_BUCKET_SIZE` |

---

## 11. Alembic Plan

### 11.1 Migration Order and Filenames **[REVISED]**

Each migration now includes `CREATE TYPE` statements for native ENUM types
**before** its `CREATE TABLE` statement, and `DROP TYPE` in the corresponding
`downgrade()` **after** its `DROP TABLE`.

`CongestionLevel` (`congestion_level` type) is shared across three tables.
It is created in `0003` (first table to use it) and **not** recreated in `0004` or `0008`.
Downgrading `0003` requires `DROP TYPE congestion_level` after dropping `traffic_segments`.

| # | Filename | Table Created | ENUM Types Created | Reason for position |
|---|----------|--------------|---------------------|---------------------|
| 2 | `0002_create_traffic_cameras_table.py` | `traffic_cameras` | `camera_status` | No FK dependencies on other Dev #2 tables |
| 3 | `0003_create_traffic_segments_table.py` | `traffic_segments` | `segment_status`, `congestion_level` | FK → `traffic_cameras`. Cameras must exist first. `congestion_level` created here (first use) |
| 4 | `0004_create_traffic_readings_table.py` | `traffic_readings` | *(none — reuses `congestion_level`)* | FK → `traffic_segments`. Segments must exist first |
| 5 | `0005_create_routes_table.py` | `routes` | *(none)* | No FK dependencies on other Dev #2 tables |
| 6 | `0006_create_route_segments_table.py` | `route_segments` | *(none)* | FK → `routes` AND `traffic_segments`. Both must exist |
| 7 | `0007_create_alerts_table.py` | `alerts` | `alert_type`, `alert_severity`, `alert_status` | FK → `traffic_segments` AND `users`. Both must exist |
| 8 | `0008_create_traffic_predictions_table.py` | `traffic_predictions` | `prediction_status` *(reuses `congestion_level`)* | FK → `traffic_segments`. Segments must exist |

### 11.2 FK Dependency Resolution

```
0001_users              (Dev #1, never touch)
  └──── prerequisite for:
        0007_alerts (created_by FK)

0002_traffic_cameras  [UUID PK; camera_status ENUM created here]
  └──── prerequisite for:
        0003_traffic_segments (camera_id UUID FK)

0003_traffic_segments  [UUID PK; segment_status + congestion_level ENUMs created here]
  └──── prerequisite for:
        0004_traffic_readings   (segment_id UUID FK; reuses congestion_level)
        0006_route_segments     (segment_id UUID FK)
        0007_alerts             (segment_id UUID FK)
        0008_traffic_predictions (segment_id UUID FK; reuses congestion_level)

0005_routes  [UUID PK]
  └──── prerequisite for:
        0006_route_segments (route_id UUID FK)
```

### 11.3 `down_revision` Chain

| File | `down_revision` |
|------|----------------|
| 0002 | `"0001"` |
| 0003 | `"0002"` |
| 0004 | `"0003"` |
| 0005 | `"0004"` |
| 0006 | `"0005"` |
| 0007 | `"0006"` |
| 0008 | `"0007"` |

### 11.4 Downgrade Considerations **[REVISED]**

Each migration must implement a complete `downgrade()`:
1. Drop indexes first.
2. Drop the table.
3. Drop ENUM types created in this migration (only those created here, not shared ones).

For `0003` downgrade:
- Drop `traffic_segments`
- Drop `segment_status`
- Drop `congestion_level` (also used by readings and predictions, but they were dropped first in migrations 0004 and 0008 which have higher revision numbers and must be downgraded before 0003)

Alembic's linear `down_revision` chain enforces correct downgrade order automatically:
`0008 → 0007 → 0006 → 0005 → 0004 → 0003 → 0002 → 0001`

---

## 12. Testing Strategy

All tests follow the existing pattern from `tests/conftest.py`:
- SQLite in-memory via `aiosqlite`
- Fresh DB per test function (function scope)
- `app.dependency_overrides[get_db]` to inject the test session
- `pytest_asyncio` for all async test functions
- `make_auth_headers` and `login_user` helpers from `conftest.py`

> **Note on native ENUMs and SQLite:** PostgreSQL native ENUM types do not exist in SQLite.
> SQLAlchemy's `sa.Enum` with `native_enum=True` falls back to `VARCHAR` in SQLite automatically.
> Tests will still enforce enum string values through Pydantic validation — the DB layer simply
> stores the string. This is consistent with how the existing auth module handles `role` in tests.

---

### 12.1 Repository Tests

Location: No direct HTTP. Use `test_db` session fixture directly.

For each repository, test:
- `create` — object persisted, correct fields set
- `get_by_id` — returns object when present, returns `None` when absent, returns `None` when soft-deleted
- `get_all` — excludes soft-deleted records; filters applied correctly
- `update` — changed fields reflected, unchanged fields preserved
- `soft_delete` **[REVISED]** — `deleted_at` set; subsequent `get_by_id` returns None

New test focus areas for v2.0:
- `CameraRepository.get_all` excludes cameras where `deleted_at IS NOT NULL`
- `ReadingRepository.count_by_congestion_level` returns correct breakdown
- `PredictionRepository.create` — verify `requested_at` is populated, `completed_at` is NULL
- `SegmentRepository.create` — verify all four coordinate fields persisted correctly

---

### 12.2 Service Tests

For each service, test:
- **Happy path** — correct inputs produce expected output
- **Not found** — raises correct domain exception when entity is absent
- **Soft-delete visibility** — soft-deleted entities are treated as "not found" by services
- **Business rule violations:**
  - `CameraService.delete_camera` raises `CameraInUseError` when non-deleted segments reference it
  - `AlertService.resolve_alert` raises `AlertNotActiveError` if already RESOLVED or DISMISSED
  - `PredictionService.complete_prediction` raises `PredictionNotPendingError` if COMPLETED or FAILED
  - `PredictionService.complete_prediction` — verify `completed_at` set, `requested_at` unchanged
  - `PredictionService.fail_prediction` — verify `completed_at` set
  - `ReadingService.submit_reading` raises `InvalidReadingTimeError` for future `recorded_at`
  - `RouteService.add_segment_to_route` raises `RouteSequenceConflictError` for duplicate order
  - `SegmentService.create_segment` — verify coordinate fields passed through correctly

---

### 12.3 Router (Integration) Tests

Location: `tests/test_<module>/test_<endpoint_group>.py`
Use the `client` fixture (AsyncClient with overridden DB).

Directories to create:
```
tests/test_cameras/
tests/test_segments/
tests/test_readings/
tests/test_alerts/
tests/test_predictions/
tests/test_routes/
tests/test_analytics/
```

For each endpoint, test:
- **200/201** — correct response body and status code for valid input
- **404** — correct error envelope when UUID does not exist
- **422** — validation errors for missing/invalid fields
- **403** — missing Authorization header
- **401** — invalid or expired token
- **Role rejection** — 403 when wrong role calls a restricted endpoint
- **Soft delete visibility** — `GET /{id}` returns 404 after soft deletion

---

### 12.4 Validation Tests

For schemas, test:
- Required fields rejected when missing (422)
- Field length limits enforced
- Enum fields reject unknown string values (422)
- `confidence_score` outside 0–1 rejected
- Coordinate fields: `start_latitude` outside -90 to 90 rejected **[NEW]**
- Coordinate fields: `end_longitude` outside -180 to 180 rejected **[NEW]**
- `prediction_for` in the past rejected by service
- `horizon_minutes <= 0` rejected

---

### 12.5 RBAC Tests

| Role | Write Cameras | Submit Readings | Create Alerts | View Analytics Summary |
|------|:---:|:---:|:---:|:---:|
| PUBLIC_USER | 403 | 403 | 403 | 200 |
| TRAFFIC_CONTROLLER | 403 | 201 | 201 | 200 |
| ADMIN | 201 | 201 | 201 | 200 |

Fixtures `public_user`, `admin_user`, `traffic_controller_user` from `conftest.py` are reused.

---

### 12.6 Integration / Workflow Tests

Test complete workflows spanning multiple modules:

1. **Create camera → create segment (with coordinates) → submit reading → verify heatmap reflects reading**
2. **Submit HEAVY reading → create CONGESTION alert → resolve alert → verify `resolved_at` set**
3. **Create prediction (PENDING) → complete prediction → verify `status=COMPLETED`, `completed_at` set, `requested_at` unchanged**
4. **Create route → add 2 segments → call `/routes/{id}/traffic` → verify congestion aggregate**
5. **Soft-delete segment → verify `GET /segments/{id}` returns 404; verify readings still queryable via `/readings?segment_id=...`** **[REVISED: was cascade-delete test]**
6. **Create prediction → fail prediction → verify `status=FAILED`, `completed_at` set, result fields remain NULL** **[NEW]**

---

## 13. Module Dependency Graph

### 13.1 Runtime Dependencies

```
         [app/core/*]  ←  used by all modules (Base, get_db, exceptions, logging)
              │
         [User / UserRole]  ←  used by Alerts (created_by FK)
              │
     ┌────────┴────────┐
     │                 │
[TrafficCamera]    [Route]
     │                 │
[TrafficSegment] ───────────────────────────────────┐
     │                                               │
     ├──── [TrafficReading] ──────────────────────┐  │
     │                                            │  │
     ├──── [Alert]  (also uses User)              │  [RouteSegment]
     │                                            │
     ├──── [TrafficPrediction]                    │
     │                                            │
     └──── [Analytics]  ← orchestrates Reading + Alert + Segment + Prediction repos
```

### 13.2 Safe Implementation Order

| Step | Module | Files Created | Rationale |
|------|--------|--------------|-----------|
| 1 | **Traffic Cameras** | model, schema, repo, service, dependency, router, migration 0002, tests | No FK deps. Validates the full 7-layer stack and UUID+soft-delete patterns end-to-end. |
| 2 | **Traffic Segments** | model, schema, repo, service, dependency, router, migration 0003, tests | FK to cameras. Establishes central entity with coordinate fields and shared `congestion_level` ENUM. |
| 3 | **Traffic Readings** | model, schema, repo, service, dependency, router, migration 0004, tests | FK to segments. Core data source. BIGSERIAL PK pattern and time-series indexes verified here. |
| 4 | **Alerts** | model, schema, repo, service, dependency, router, migration 0007, tests | FK to segments + users. Most complex lifecycle rules. All alert ENUM types created here. |
| 5 | **Routes** | Route model + RouteSegment model, schema, repo, service, dependency, router, migrations 0005 + 0006, tests | FK to segments. Tests the many-to-many join table pattern. |
| 6 | **Predictions** | model, schema, repo, service, dependency, router, migration 0008, tests | FK to segments. Validates `requested_at`/`completed_at` lifecycle timestamps and `prediction_status` ENUM. |
| 7 | **Analytics** | service, dependency, router only (no new model, no new repo, no migration), tests | Pure aggregation. No new table. Requires all previous modules to have real data. Must be last. |

### 13.3 Justification for This Order

- **Cameras first:** Zero foreign key dependencies. UUID primary key, soft-delete pattern, and native ENUM type are all tested here with the simplest model before they cascade to everything else.
- **Segments second:** Everything pivots on segments. Coordinate fields and the shared `congestion_level` ENUM are introduced here. Establishing this entity early makes all subsequent modules straightforward.
- **Readings third:** The raw data pipeline. Validates the BIGSERIAL PK + UUID FK combination. Needed for analytics and alert integration tests.
- **Alerts fourth:** Most complex RBAC, lifecycle state machine, and cross-table FK (segments + users). Readings must exist to write meaningful integration tests.
- **Routes fifth:** Independent of readings and alerts at DB level. Tests UUID-to-UUID FK chains and the ordered join table pattern.
- **Predictions sixth:** Validates the new `requested_at`/`completed_at` lifecycle timestamps and the PENDING → COMPLETED/FAILED state machine.
- **Analytics last:** No new tables or repositories. Entirely derived from data produced by all preceding modules. Cannot be meaningfully implemented or tested until all source tables contain representative data.

---

## 14. Milestone 2 Architectural Extensions

The Milestone 2 implementation introduces advanced predictive intelligence and external mapping capabilities while strictly adhering to the established Clean Architecture principles. The core data flow (`Router → Service → Repository`) remains intact and authoritative. The following layers were introduced as supporting domain capabilities:

### 14.1 Machine Learning Foundation (`app/ml`)

The Machine Learning layer provides predictive capabilities strictly orchestrated by the `PredictionService`. Repositories and Routers do not interact with this layer directly.

- **PredictionEngine**: The core orchestrator for ML capabilities.
- **ModelAdapter**: Abstracts the underlying `RandomForestRegressor` (`scikit-learn`), providing deterministic hashing, dynamic in-memory training, and inference.
- **Feature Engineering**: Encapsulates raw data transformations, window functions, and congestion threshold logic to prepare data for the model.

### 14.2 External Maps Integration (`app/adapters`)

The Adapters layer encapsulates and isolates all external HTTP communications. It acts as an anti-corruption layer between external providers (like OSRM) and internal business logic.

- **MapsAdapterProtocol**: Defines the strict interface that any routing provider must fulfill.
- **OSRMAdapter**: Concrete implementation leveraging `httpx` for asynchronous HTTP communication with the OSRM backend.
- **Usage**: The `RouteService` utilizes the `MapsAdapterProtocol` to dynamically evaluate intersection routing and travel times without leaking external HTTP concerns into repositories or routers.

---

*End of Engineering Design Document v2.0*

*This document supersedes v1.0 and is the single source of truth for all TrafficVision AI Dev #2 implementation.*
*No code should be written that is not derivable from this document.*
