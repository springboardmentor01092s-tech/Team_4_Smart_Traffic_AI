# Setup & Deployment Guide — TrafficVision AI Backend

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.12+ | Python 3.12.13 verified |
| PostgreSQL | 14+ | PostgreSQL 16 recommended (or Docker) |
| Docker & Compose | 20.10+ / v2+ | Optional (for containerized deployment) |
| Git | any | For version control |

---

## 1. Quickstart with Docker Compose (Recommended)

The fastest and most isolated way to run the entire backend with PostgreSQL:

```bash
# 1. Clone the repository
git clone https://github.com/springboardmentor01092s-tech/Team_4_Smart_Traffic_AI.git
cd Team_4_Smart_Traffic_AI

# 2. Build and start services in detached mode
docker compose up --build -d

# 3. View live application logs
docker compose logs -f backend

# 4. Check container health status
docker compose ps
```

The Docker container automatically executes `alembic upgrade head` before starting the Uvicorn server, ensuring deterministic schema synchronization.

---

## 2. Local Python Virtual Environment Setup

### A. Clone and Virtual Environment

```bash
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### B. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### C. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your local values:

```env
# Application
APP_NAME="TrafficVision AI"
APP_VERSION="1.4.0"
APP_ENV="development"
DEBUG=true
LOG_LEVEL="DEBUG"

# API Prefix
API_V1_PREFIX="/api/v1"

# Database (PostgreSQL)
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/trafficvision"

# JWT Secret & Expiration (Generate via: python -c "import secrets; print(secrets.token_hex(64))")
JWT_SECRET_KEY="your-very-secure-random-secret-min-32-chars"
JWT_ALGORITHM="HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
ALLOWED_ORIGINS="http://localhost:3000,http://localhost:5173"

# Maps Provider (Optional)
MAPS_PROVIDER_URL="http://router.project-osrm.org"
MAPS_API_KEY=""

# Operational Intelligence
TREND_INCREASING_THRESHOLD_PERCENT=5.0
TREND_DECREASING_THRESHOLD_PERCENT=-5.0
```

---

## 3. Database Setup & Migrations

### Apply Migrations

Run all database migrations up to current head (`0009`):

```bash
alembic upgrade head
```

### Verify Migration History

```bash
alembic current    # Shows: 0009 (head)
alembic history    # Shows full chain: 0001 -> 0008 -> 3b8c7d3f099c -> 0009
```

---

## 4. Run Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive API documentation will be available at:
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 5. Health & Liveness Verification

The backend exposes three production health probes:

### 1. General Health Probe
```bash
curl http://localhost:8000/api/v1/health
```
```json
{
  "status": "healthy",
  "service": "TrafficVision AI",
  "version": "1.4.0",
  "environment": "development",
  "timestamp": "2026-08-26T19:00:00+00:00"
}
```

### 2. Process Liveness Probe (Kubernetes / Docker)
```bash
curl http://localhost:8000/api/v1/health/live
```
```json
{
  "status": "live",
  "service": "TrafficVision AI"
}
```

### 3. Database Readiness Probe (Kubernetes / Load Balancer)
```bash
curl http://localhost:8000/api/v1/health/ready
```
- Returns `200 OK` when the database connection is healthy:
  ```json
  {
    "status": "ready",
    "database": "connected"
  }
  ```
- Returns `503 Service Unavailable` if the database is unreachable or down.

---

## 6. Running Tests & Quality Assurance

### Execute Pytest Suite

```bash
# Run full suite
pytest -v

# Run with durations
pytest -v --durations=10

# Run specific domain module
pytest tests/test_routes/ -v
pytest tests/test_health/ -v
pytest tests/test_optimizations/ -v
```

### Test Suite Verification Summary
- **Total Tests Collected**: 372
- **Passed**: 367
- **Skipped**: 5 (SQLite `date_trunc` compatibility skips)
- **PostgreSQL Direct Validation**: 100% Passed (All 5 `date_trunc` operations fully verified against live PostgreSQL)

---

## 7. Production Hardening Checklist

- [x] **Non-root container user**: `Dockerfile` runs as `appuser` (uid 1001).
- [x] **Defensive container startup**: `entrypoint.sh` halts if migration fails.
- [x] **Idempotent notification delivery**: Database unique constraint `uq_notifications_recipient_alert`.
- [x] **Batch route querying**: N+1 queries eliminated (81.8% query reduction).
- [x] **Production Health Probes**: `/health/live` and `/health/ready` implemented.
- [x] **Zero-secret repository**: `.env` ignored, `.env.example` provides documentation templates.
- [x] **Automated CI Workflow**: GitHub Actions pipeline validates syntax, migrations, tests, and Docker builds.
