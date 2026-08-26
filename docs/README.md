# TrafficVision AI — Backend

> **Smart Traffic Prediction & Congestion Management System**
> Production-ready, high-performance RESTful API powering real-time urban traffic monitoring, predictive congestion forecasting, IoT camera integration, incident management, route optimization, and operational analytics.

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.x_Async-red.svg)](https://sqlalchemy.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)](https://postgresql.org)
[![Tests](https://img.shields.io/badge/Pytest-367_Passed%20%7C%205_PG_Validated-brightgreen.svg)](../tests/)
[![Status](https://img.shields.io/badge/Release-v1.4.0_Milestone_4-success.svg)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../LICENSE)

---

## Executive Overview

**TrafficVision AI Backend** is an enterprise-grade backend infrastructure built with Python 3.12, FastAPI, SQLAlchemy 2.x (Async), and PostgreSQL. It delivers a scalable, modular architecture engineered for real-time traffic monitoring, automated incident reporting, machine-learning prediction ingestion, dynamic routing, operational intelligence, notification dispatch, and deep analytics.

The backend is fully complete and hardened for **v1.4.0 (Milestone 4)**, featuring **100% feature completion across all 7 domain modules**, an **immutable Authentication & User Management foundation**, **Docker containerization**, and **measurable performance profiling**.

### Core System Capabilities
- 🔐 **Stateless Authentication & User Management**: JWT (HS256) bearer token authentication, bcrypt (12 rounds) password security, and 3-tier Role-Based Access Control (`ADMIN`, `TRAFFIC_CONTROLLER`, `PUBLIC_USER`).
- 📹 **Traffic Camera Network (Module 1)**: IoT camera device registry, status lifecycle (`ACTIVE`, `OFFLINE`, `MAINTENANCE`), geographic positioning (lat/long), soft deletion (`deleted_at`), and segment dependency guards.
- 🛣️ **Road Segment Topology (Module 2)**: Spatial road segment definitions linking cameras, operational status (`ACTIVE`, `CONSTRUCTION`, `CLOSED`), and dynamic latest-reading resolution.
- 📊 **Time-Series Traffic Readings (Module 3)**: High-throughput ingestion of traffic observations (`BIGSERIAL` PK), immutable append-only data architecture, vehicle counting, speed tracking, congestion scoring (`LOW`, `MODERATE`, `HEAVY`, `SEVERE`), and window-function aggregations.
- 🚨 **Traffic Incident Alerts (Module 4)**: Real-time incident reporting, multi-type taxonomy (`CONGESTION`, `ACCIDENT`, `WEATHER`, `ROADWORK`, `HAZARD`), severity levels (`LOW` to `CRITICAL`), and strict status state machine (`ACTIVE` → `RESOLVED` / `DISMISSED`).
- 🔮 **Predictive Traffic Forecasting (Module 5)**: Machine-learning forecasting pipeline utilizing dynamically trained `RandomForestRegressor`, orchestrating historical readings to predict future congestion, prediction horizon scheduling, model version tracking, and lifecycle execution (`PENDING` → `COMPLETED` / `FAILED`).
- 🗺️ **Dynamic Multi-Segment Routes (Module 6)**: Multi-segment route definition, ordered intersection sequencing, real-time route congestion aggregation, congestion-aware route comparison, dynamic travel-time estimation based on live readings, and external maps integration via OSRM adapters.
- 📈 **Operational Analytics & Intelligence (Module 7)**: System-wide snapshot summaries, real-time spatial congestion heatmaps, prediction analytics (reporting completion rates and model states), peak-hour time-series analysis, segment time-bucketing (5/15/30/60 min intervals), and cross-domain reports with RBAC protection.

---

## System Architecture

The backend strictly implements a **7-Layer Clean Architecture** where dependencies flow inward toward domain business logic. Cross-cutting infrastructure concerns (`app/core/`) are isolated from domain logic.

```
                  ┌─────────────────────────────────────────┐
                  │       HTTP Request (JSON / Bearer)       │
                  └────────────────────┬────────────────────┘
                                       │
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │     Middleware (CORS, RequestID, Log)   │
                  └────────────────────┬────────────────────┘
                                       │
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │          FastAPI Routers Layer          │
                  │        (Pydantic v2 Request/Resp)       │
                  └────────────────────┬────────────────────┘
                                       │
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │       Business Services Layer           │
                  │   (Domain Logic & State Transitions)   │
                  └────────────────────┬────────────────────┘
                                       │
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │       Repositories Layer (Data Access)  │
                  │   (Async SQLAlchemy 2.x ORM Queries)    │
                  └────────────────────┬────────────────────┘
                                       │
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │      Database Engine (PostgreSQL)       │
                  └─────────────────────────────────────────┘
```

### Module Folder Layout

```
app/
├── core/           # Infrastructure: config, database async engine, security, middleware, exceptions
├── models/         # SQLAlchemy 2.x ORM Mapped models (User, Camera, Segment, Reading, Alert, Prediction, Route)
├── schemas/        # Pydantic v2 schemas for request validation & response serialization
├── repositories/   # Data Access layer executing async SQL queries per entity
├── services/       # Domain Business Logic layer orchestrating repositories and state rules
├── routers/        # Thin REST HTTP API endpoint definitions with dependency injection
├── dependencies/   # FastAPI Depends() factories (DB session, Auth JWT, RBAC guards)
├── utils/          # Pure helper utilities (datetime, formatting)
└── main.py         # Application factory, lifespan management, middleware registration & health check
```

---

## Technology Stack

| Layer / Concern | Technology | Version | Purpose |
|-----------------|------------|---------|---------|
| **Language** | Python | 3.12.13 verified | Modern async Python execution environment |
| **Framework** | FastAPI | 0.115+ | High-performance async REST web framework |
| **Database** | PostgreSQL | 14+ | Relational storage for spatial, time-series, and user domain data |
| **Driver** | `asyncpg` | Latest | High-speed asynchronous PostgreSQL driver |
| **ORM** | SQLAlchemy | 2.x (Async) | Declarative async ORM with native PostgreSQL ENUM support |
| **Migrations** | Alembic | Latest | Reversible schema migration management |
| **Validation** | Pydantic | v2.x | Request/response schema validation and settings |
| **Authentication** | `python-jose` + `passlib` | 4.0.1 (bcrypt) | Stateless JWT (HS256) minting & 12-round bcrypt hashing |
| **Testing** | Pytest + `httpx` + `aiosqlite` | Latest | Async test suite with in-memory SQLite support |

---

## Quick Start

See [SETUP.md](SETUP.md) for detailed installation instructions.

### 1. Clone & Setup Environment

```bash
# Clone the repository
git clone <repository-url> trafficvision-ai
cd trafficvision-ai

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows (PowerShell)
source .venv/bin/activate        # Linux/macOS

# Install production dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your database credentials and a secure 64-character JWT secret:

```env
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/trafficvision"
JWT_SECRET_KEY="your-random-64-character-hex-secret"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
APP_ENV="development"
DEBUG=true
ALLOWED_ORIGINS="http://localhost:3000,http://localhost:5173"
```

### 3. Run Database Migrations & Start Server

```bash
# Apply Alembic schema migrations
alembic upgrade head

# Start the development server with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access the interactive API documentation:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

## API Endpoints Reference

The table below lists all endpoints exposed under `/api/v1`:

| Module | Method | Endpoint | Min Role | Description |
|--------|--------|----------|----------|-------------|
| **Health** | `GET` | `/api/v1/health` | Public | System health check & version info |
| **Auth** | `POST` | `/api/v1/auth/register` | Public | Create new user account |
| **Auth** | `POST` | `/api/v1/auth/login` | Public | Authenticate & receive JWT bearer token |
| **Auth** | `POST` | `/api/v1/auth/logout` | Bearer | Discard session token (stateless client hint) |
| **Users** | `GET` | `/api/v1/users/me` | Bearer | Get current user's profile |
| **Users** | `PUT` | `/api/v1/users/me` | Bearer | Update current user's profile |
| **Cameras** | `GET` | `/api/v1/cameras` | Bearer | List cameras with status filtering & pagination |
| **Cameras** | `POST` | `/api/v1/cameras` | `ADMIN` | Register a new IoT traffic camera |
| **Cameras** | `GET` | `/api/v1/cameras/{id}` | Bearer | Get camera details by UUID |
| **Cameras** | `PUT` | `/api/v1/cameras/{id}` | `ADMIN` | Update camera status or coordinates |
| **Cameras** | `DELETE` | `/api/v1/cameras/{id}` | `ADMIN` | Soft-delete a camera (guarded against active segments) |
| **Segments** | `GET` | `/api/v1/segments` | Bearer | List traffic segments with filters |
| **Segments** | `POST` | `/api/v1/segments` | `ADMIN` | Create a new road segment |
| **Segments** | `GET` | `/api/v1/segments/{id}` | Bearer | Get segment details by UUID |
| **Segments** | `PUT` | `/api/v1/segments/{id}` | `ADMIN` | Update segment properties or status |
| **Segments** | `DELETE` | `/api/v1/segments/{id}` | `ADMIN` | Soft-delete a segment |
| **Segments** | `GET` | `/api/v1/segments/{id}/latest-reading` | Bearer | Retrieve latest recorded reading for segment |
| **Readings** | `GET` | `/api/v1/readings` | Bearer | Query historical traffic readings (time-bounded) |
| **Readings** | `POST` | `/api/v1/readings` | `CONTROLLER` | Ingest time-series observation reading |
| **Readings** | `GET` | `/api/v1/readings/{id}` | Bearer | Get specific reading by BIGSERIAL ID |
| **Alerts** | `GET` | `/api/v1/alerts` | Bearer | List traffic alerts (filter by segment/severity/status/type) |
| **Alerts** | `POST` | `/api/v1/alerts` | `CONTROLLER` | Report new traffic alert/incident |
| **Alerts** | `GET` | `/api/v1/alerts/{id}` | Bearer | Get alert details |
| **Alerts** | `PUT` | `/api/v1/alerts/{id}` | `CONTROLLER` | Update active alert description or severity |
| **Alerts** | `PATCH` | `/api/v1/alerts/{id}/resolve` | `CONTROLLER` | Transition alert status to `RESOLVED` |
| **Alerts** | `PATCH` | `/api/v1/alerts/{id}/dismiss` | `CONTROLLER` | Transition alert status to `DISMISSED` |
| **Alerts** | `DELETE` | `/api/v1/alerts/{id}` | `ADMIN` | Soft-delete an alert |
| **Predictions** | `GET` | `/api/v1/predictions` | Bearer | List traffic predictions (filter by status/segment) |
| **Predictions** | `POST` | `/api/v1/predictions` | `CONTROLLER` | Request new traffic prediction forecast |
| **Predictions** | `GET` | `/api/v1/predictions/{id}` | Bearer | Get prediction forecast details |
| **Predictions** | `GET` | `/api/v1/predictions/segment/{id}/upcoming` | Bearer | Fetch upcoming predictions for a segment |
| **Predictions** | `PATCH` | `/api/v1/predictions/{id}/complete` | `CONTROLLER` | Submit AI model result (`PENDING` → `COMPLETED`) |
| **Predictions** | `PATCH` | `/api/v1/predictions/{id}/fail` | `CONTROLLER` | Mark prediction execution as `FAILED` |
| **Predictions** | `DELETE` | `/api/v1/predictions/{id}` | `ADMIN` | Soft-delete a prediction forecast |
| **Routes** | `GET` | `/api/v1/routes` | Bearer | List routes with pagination |
| **Routes** | `POST` | `/api/v1/routes` | `ADMIN` | Create a new route definition |
| **Routes** | `GET` | `/api/v1/routes/{id}` | Bearer | Get route with ordered segment sequence |
| **Routes** | `PUT` | `/api/v1/routes/{id}` | `ADMIN` | Update route properties |
| **Routes** | `DELETE` | `/api/v1/routes/{id}` | `ADMIN` | Soft-delete a route |
| **Routes** | `GET` | `/api/v1/routes/{id}/traffic` | Bearer | Get real-time aggregated traffic across route |
| **Routes** | `POST` | `/api/v1/routes/{id}/segments` | `ADMIN` | Attach segment to route at sequence order |
| **Routes** | `DELETE` | `/api/v1/routes/{id}/segments/{assoc_id}` | `ADMIN` | Remove segment from route |
| **Notifications** | `GET` | `/api/v1/notifications/me` | Bearer | Retrieve owned user notifications |
| **Notifications** | `PATCH` | `/api/v1/notifications/{id}/read` | Bearer | Mark owned notification as read |
| **Incidents** | `POST` | `/api/v1/incidents` | `CONTROLLER` | Report traffic incident triggering alerts |
| **Analytics** | `GET` | `/api/v1/analytics/summary` | Bearer | System-wide operational snapshot |
| **Analytics** | `GET` | `/api/v1/analytics/congestion-heatmap` | Bearer | Current segment congestion levels & coordinates |
| **Analytics** | `GET` | `/api/v1/analytics/peak-hours` | Bearer | System-wide hourly vehicle count averages |
| **Analytics** | `GET` | `/api/v1/analytics/segments/{id}/history` | Bearer | Segment historical metrics in time buckets |
| **Analytics** | `GET` | `/api/v1/analytics/segments/{id}/trends` | `CONTROLLER` | Segment statistical trend analysis |
| **Analytics** | `GET` | `/api/v1/analytics/reports` | `CONTROLLER` | Comprehensive multi-domain analytical report |
| **Analytics** | `GET` | `/api/v1/analytics/ai-report` | `CONTROLLER` | AI traffic intelligence report across domains |
| **Insights** | `GET` | `/api/v1/insights/segment/{id}` | Bearer | Structured AI insights for a specific segment |

> **Note:** `CONTROLLER` denotes `TRAFFIC_CONTROLLER` or `ADMIN` roles. Detailed request/response payloads are in [API_REFERENCE.md](API_REFERENCE.md).

---

## Role-Based Access Control (RBAC) Matrix

| Domain Operations | `PUBLIC_USER` | `TRAFFIC_CONTROLLER` | `ADMIN` |
|-------------------|:-------------:|:------------------:|:-------:|
| Auth Register & Login | ✅ | ✅ | ✅ |
| View Profile / Update Own Profile | ✅ | ✅ | ✅ |
| View Cameras, Segments, Readings, Alerts, Predictions, Routes | ✅ | ✅ | ✅ |
| Ingest Readings (`POST /readings`) | ❌ | ✅ | ✅ |
| Create/Update Alerts (`POST`, `PUT`, `PATCH resolve/dismiss`) | ❌ | ✅ | ✅ |
| Manage Predictions (`POST`, `PATCH complete/fail`) | ❌ | ✅ | ✅ |
| View Segment Trends & System Reports (`GET /analytics/reports`) | ❌ | ✅ | ✅ |
| Write/Update Cameras & Segments (`POST`, `PUT` /cameras & /segments) | ❌ | ❌ | ✅ |
| Write/Update Routes (`POST`, `PUT`, attach segments) | ❌ | ❌ | ✅ |
| Soft-Delete Records (Cameras, Segments, Alerts, Predictions, Routes) | ❌ | ❌ | ✅ |

---

## Testing & Quality Assurance

The codebase includes a comprehensive test suite of **364 unit and integration tests** executing asynchronously using `pytest-asyncio`, `httpx`, and in-memory `aiosqlite`.

### Execute Test Suite

```bash
# Run all tests
.\.venv\Scripts\pytest tests/ -v   # Windows
pytest tests/ -v                    # Linux/macOS

# Run with concise traceback on failure
pytest tests/ -v --tb=short

# Run specific domain module tests
pytest tests/test_cameras/ -v
pytest tests/test_alerts/ -v
pytest tests/test_analytics/ -v
```

### Test Coverage Breakdown

| Test Suite Module | Target Scope | Test Count | Status |
|-------------------|--------------|------------|--------|
| `tests/test_auth` | JWT encoding/decoding, passlib bcrypt, register, login, user profile | 25+ | PASSED |
| `tests/test_cameras` | Camera ORM model, repository CRUD, soft delete, router RBAC | 25+ | PASSED |
| `tests/test_segments` | Segment spatial model, camera FK validation, latest reading resolution | 25+ | PASSED |
| `tests/test_readings` | Ingestion bounds, timestamp validation, time-series aggregations | 30+ | PASSED |
| `tests/test_alerts` | Alert state transitions (`ACTIVE` → `RESOLVED`/`DISMISSED`), severity filters | 35+ | PASSED |
| `tests/test_predictions` | Prediction forecasting lifecycle, horizon validation, router RBAC | 35+ | PASSED |
| `tests/test_routes` | Multi-segment route calculation, route segment order, traffic aggregation | 40+ | PASSED |
| `tests/test_analytics` | System summary, heatmap, peak hours, segment time-bucketing, reports | 50+ | PASSED |
| `tests/test_incidents` | Incident reporting and workflow validation | 5+ | PASSED |
| `tests/test_notifications` | Notification tracking and read marking | 5+ | PASSED |
| `tests/test_insights` | Insight orchestration across domains | 5+ | PASSED |
| `tests/test_e2e` | E2E integration validations across M1, M2, and M3 | 10+ | PASSED |
| **Total** | **All Domain Modules + Auth Foundation** | **364** | **100% Passed (5 Skipped)** |

---

## Documentation Ecosystem

The `docs/` directory contains comprehensive specifications and developer guides for every aspect of the project:

| Document | Description |
|----------|-------------|
| [API_REFERENCE.md](API_REFERENCE.md) | Complete endpoint specification with JSON request/response schemas for all 7 modules |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System topology, clean layer contracts, dependency injection flow, and database schema |
| [AUTHENTICATION.md](AUTHENTICATION.md) | JWT token format, claim validation, bcrypt parameters, and RBAC implementation details |
| [ENGINEERING_DESIGN_V2.md](ENGINEERING_DESIGN_V2.md) | Full architectural blueprint and technical requirements specification (v2.0) |
| [SETUP.md](SETUP.md) | Local development setup guide, Docker PostgreSQL deployment, and configuration reference |
| [BACKEND_CONTRACT.md](BACKEND_CONTRACT.md) | Module boundaries, integration guidelines, and extension rules |
| [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) | Integration protocols for frontend applications and external AI prediction services |
| [IMPLEMENTATION_PROGRESS.md](IMPLEMENTATION_PROGRESS.md) | Module-by-module completion log, test execution summaries, and validation history |
| [CHANGELOG.md](CHANGELOG.md) | Version history tracking features, fixes, and release readiness (v1.0.0) |

---

## License

This project is licensed under the MIT License — see the [LICENSE](../LICENSE) file for details.
