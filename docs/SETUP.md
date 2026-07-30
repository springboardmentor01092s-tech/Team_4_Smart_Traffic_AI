# Setup Guide — TrafficVision AI Backend

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.12+ | 3.14 tested |
| PostgreSQL | 14+ | Local or Docker |
| Git | any | For version control |

---

## 1. Clone the Repository

```bash
git clone <repository-url> trafficvision-ai
cd trafficvision-ai
```

---

## 2. Create Virtual Environment

```bash
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
# Database — replace with your PostgreSQL credentials
DATABASE_URL="postgresql+asyncpg://postgres:yourpassword@localhost:5432/trafficvision"

# JWT — generate a strong secret (minimum 32 characters)
JWT_SECRET_KEY="your-very-secure-random-secret-min-32-chars"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application
APP_ENV="development"
DEBUG=true
LOG_LEVEL="DEBUG"

# CORS — frontend origin(s)
ALLOWED_ORIGINS="http://localhost:3000,http://localhost:5173"
```

### Generate a Strong JWT Secret

```bash
python -c "import secrets; print(secrets.token_hex(64))"
```

---

## 5. Set Up PostgreSQL Database

### Option A: Docker (recommended for development)

```bash
docker run --name trafficvision-db \
  -e POSTGRES_DB=trafficvision \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  -d postgres:16
```

### Option B: Local PostgreSQL

```sql
-- Run in psql
CREATE DATABASE trafficvision;
CREATE USER trafficvision_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE trafficvision TO trafficvision_user;
```

---

## 6. Run Database Migrations

```bash
alembic upgrade head
```

This runs the initial migration that creates the `users` table.

### Verify the migration

```bash
alembic current    # Should show: 0001 (head)
alembic history    # Shows migration chain
```

---

## 7. Start the Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO | Starting TrafficVision AI v1.0.0 | env=development
INFO | API available at /api/v1 | Docs at /docs | ReDoc at /redoc
INFO:     Application startup complete.
```

---

## 8. Verify the Setup

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

Expected:
```json
{
  "status": "healthy",
  "service": "TrafficVision AI",
  "version": "1.0.0",
  "environment": "development",
  "timestamp": "2025-01-01T00:00:00+00:00"
}
```

### Swagger UI

Open: [http://localhost:8000/docs](http://localhost:8000/docs)

### Register a Test User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Test User", "email": "test@example.com", "password": "TestPass1"}'
```

### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "TestPass1"}'
```

---

## 9. Run Tests

Tests use SQLite in-memory — no PostgreSQL required.

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --tb=short

# Run specific test file
pytest tests/test_auth/test_jwt.py -v

# Run specific test
pytest tests/test_auth/test_register.py::test_register_success -v
```

---

## Useful Commands

```bash
# Create a new migration after adding a model
alembic revision --autogenerate -m "add_traffic_cameras_table"

# Apply pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current migration state
alembic current

# Show migration history
alembic history --verbose
```

---

## Production Checklist

- [ ] `JWT_SECRET_KEY` is at least 64 random hex characters
- [ ] `APP_ENV=production` and `DEBUG=false`
- [ ] `ALLOWED_ORIGINS` set to your actual frontend domain(s)
- [ ] PostgreSQL is running with SSL enabled
- [ ] `.env` is in `.gitignore` (it is by default)
- [ ] Application runs behind a reverse proxy (nginx / Caddy)
- [ ] Health endpoint is monitored
- [ ] Logs are shipped to a log aggregator
