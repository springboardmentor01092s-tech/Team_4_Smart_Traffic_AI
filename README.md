# TrafficVision AI — Backend

> **Smart Traffic Prediction & Congestion Management System**  
> Production-ready, high-performance RESTful API powering real-time urban traffic monitoring, predictive congestion forecasting, IoT camera integration, incident management, route optimization, operational intelligence, notifications, and analytics.

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.x_Async-red.svg)](https://sqlalchemy.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)](https://postgresql.org)
[![Tests](https://img.shields.io/badge/Pytest-367_Passed%20%7C%205_PG_Validated-brightgreen.svg)](tests/)
[![Release](https://img.shields.io/badge/Release-v1.4.0_Milestone_4-success.svg)](docs/CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Executive Overview

**TrafficVision AI Backend** is an enterprise-grade backend infrastructure engineered with Python 3.12, FastAPI, SQLAlchemy 2.x (Async), and PostgreSQL. It delivers a modular, hardened 7-layer architecture designed for high-throughput traffic telemetry ingestion, automated incident alerting, machine-learning congestion forecasting, route optimization, AI insights, and real-time notification dispatch.

Milestone 4 completes the production-readiness hardening, containerization, performance profiling, automated CI/CD pipeline, and health monitoring.

---

## Key System Modules & Features

- 🔐 **Authentication & RBAC**: JWT (HS256) bearer token authentication, bcrypt (12 rounds) password hashing, and 3-tier Role-Based Access Control (`ADMIN`, `TRAFFIC_CONTROLLER`, `PUBLIC_USER`).
- 📹 **Traffic Camera Network**: IoT camera registry, status lifecycle (`ACTIVE`, `OFFLINE`, `MAINTENANCE`), GPS coordinates, and segment dependency guards.
- 🛣️ **Road Segment Topology**: Spatial road segment definitions linking cameras, operational status (`ACTIVE`, `CONSTRUCTION`, `CLOSED`), and dynamic speed/congestion tracking.
- 📊 **Time-Series Traffic Telemetry**: High-throughput ingestion of traffic observations (`BIGSERIAL` PK), append-only data architecture, vehicle counting, speed tracking, and window-function aggregations.
- 🚨 **Incident Alerts & Notification Dispatch**: Multi-severity incident management with idempotent user notification generation and database-enforced uniqueness constraints (`uq_notifications_recipient_alert`).
- 🔮 **Predictive Forecasting & AI Insights**: Machine-learning forecasting pipeline with dynamic feature extraction, regression model training, prediction horizon scheduling, and heuristic AI insight generation.
- 🗺️ **Dynamic Multi-Segment Routes**: Multi-segment route definition, ordered intersection sequencing, travel-time estimation, and batch-optimized route comparisons (N+1 query elimination).
- 📈 **Operational Analytics**: System snapshot summaries, hourly vehicle count aggregations (`date_trunc`), peak-hour detection, and direct SQL aggregations.
- 🩺 **Production Health & Readiness**: Kubernetes/load-balancer-compatible endpoints (`/api/v1/health`, `/api/v1/health/live`, `/api/v1/health/ready`).

---

## Performance Optimizations (Milestone 4)

| Area | Before Optimization | After Optimization | Improvement |
| :--- | :--- | :--- | :--- |
| **Travel Time Estimation** (1 route, 10 segments) | 22 DB queries, 20.85 ms | 4 DB queries, 9.56 ms | **81.8% query reduction, 54.1% faster** |
| **Route Comparison** (5 routes, 10 segments) | 115 DB queries, 83.67 ms | 21 DB queries, 20.15 ms | **81.7% query reduction, 75.9% faster** |
| **Notification Generation** | Application-only existence check | DB Unique Constraint + Idempotent Handlers | **Zero race condition duplicates** |
| **Analytics Aggregation** | Unbounded list loading in Python | Direct SQL Grouped Count Queries | **O(1) memory footprint** |

---

## Quickstart

### Option A: Docker Compose (Recommended for Production / Deployment)

1. Clone the repository and navigate to the project directory:
   ```bash
   git clone https://github.com/springboardmentor01092s-tech/Team_4_Smart_Traffic_AI.git
   cd Team_4_Smart_Traffic_AI
   ```

2. Start PostgreSQL and FastAPI backend with automated migrations:
   ```bash
   docker compose up --build -d
   ```

3. Verify application health:
   ```bash
   curl http://localhost:8000/api/v1/health/ready
   ```

4. Access interactive API documentation:
   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

---

### Option B: Local Python Virtual Environment

1. Ensure Python 3.12+ and PostgreSQL 14+ are installed.
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows PowerShell
   .\.venv\Scripts\Activate.ps1
   # Linux/macOS
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment:
   ```bash
   cp .env.example .env
   ```
5. Apply database migrations:
   ```bash
   alembic upgrade head
   ```
6. Start development server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

---

## Testing & Quality Assurance

Run the comprehensive pytest suite:
```bash
pytest -v
```

### Verified Test Results
- **Collected**: 372 tests
- **Passed**: 367 tests
- **Skipped**: 5 tests (explicitly identified as SQLite `date_trunc` compatibility skips; 100% verified against PostgreSQL)
- **Failures**: 0

Run CI workflow locally or via GitHub Actions:
```bash
python -m compileall -q app alembic tests
pytest -v --durations=10
```

---

## Documentation

Detailed architectural and operational documentation is available in the [`docs/`](docs/) directory:
- [API Reference](docs/API_REFERENCE.md) — Comprehensive API endpoint specifications and schemas
- [Setup & Deployment Guide](docs/SETUP.md) — Step-by-step setup and environment configuration
- [System Architecture](docs/ARCHITECTURE.md) — 7-layer architecture and data flow diagrams
- [Changelog](docs/CHANGELOG.md) — Release history and migration notes
- [Implementation Progress](docs/IMPLEMENTATION_PROGRESS.md) — Complete milestone verification log
