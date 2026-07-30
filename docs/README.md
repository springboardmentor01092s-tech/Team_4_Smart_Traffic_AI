# TrafficVision AI — Backend

> **Smart Traffic Prediction & Congestion Management System**
> Authentication & User Management Foundation

[![Python](https://img.shields.io/badge/Python-3.12+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.x-red)](https://sqlalchemy.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## Overview

This repository contains the **authentication and user management foundation** for the TrafficVision AI backend. It is designed as an **immutable base layer** that a second backend developer can extend with traffic, prediction, analytics, and alert modules without modifying any authentication code.

**What's included:**
- ✅ FastAPI application factory with lifespan management
- ✅ JWT authentication (Bearer tokens, HS256)
- ✅ Password hashing (bcrypt, 12 rounds)
- ✅ Role-Based Access Control (ADMIN / TRAFFIC_CONTROLLER / PUBLIC_USER)
- ✅ SQLAlchemy 2.x async ORM with PostgreSQL
- ✅ Alembic database migrations
- ✅ Centralized exception handling with consistent JSON error responses
- ✅ CORS, Request ID, and Structured Logging middleware
- ✅ 25+ unit and integration tests
- ✅ Comprehensive developer documentation

**What's NOT included (by design):**
- ❌ Traffic monitoring APIs
- ❌ Prediction and analytics modules
- ❌ Alert and camera management
- ❌ Any business logic beyond authentication

---

## Quick Start

See [SETUP.md](SETUP.md) for full installation instructions.

```bash
# 1. Clone and enter the project
cd trafficvision-ai

# 2. Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows
source .venv/bin/activate        # Linux/macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your PostgreSQL credentials and JWT secret

# 5. Run database migrations
alembic upgrade head

# 6. Start the development server
uvicorn app.main:app --reload

# 7. Open API documentation
# http://127.0.0.1:8000/docs
```

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/api/v1/health` | None | Health check |
| `POST` | `/api/v1/auth/register` | None | Register new account |
| `POST` | `/api/v1/auth/login` | None | Login → JWT |
| `POST` | `/api/v1/auth/logout` | Optional | Logout acknowledgement |
| `GET` | `/api/v1/users/me` | Bearer | Get own profile |
| `PUT` | `/api/v1/users/me` | Bearer | Update own profile |

---

## Team Structure

| Developer | Responsibility |
|-----------|----------------|
| **Backend Dev #1** | Auth, JWT, RBAC, User Management (this repo) |
| **Backend Dev #2** | Traffic, Prediction, Analytics, Alerts, AI |

See [BACKEND_CONTRACT.md](BACKEND_CONTRACT.md) for the integration contract.

---

## Documentation

| Document | Purpose |
|----------|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, folder structure, dependency flow |
| [AUTHENTICATION.md](AUTHENTICATION.md) | Auth flow, JWT format, RBAC usage |
| [SETUP.md](SETUP.md) | Full local development setup guide |
| [API_REFERENCE.md](API_REFERENCE.md) | Complete endpoint documentation |
| [BACKEND_CONTRACT.md](BACKEND_CONTRACT.md) | Integration rules for Backend Dev #2 |

---

## Project Structure

```
app/
├── core/           # Infrastructure (config, DB, security, middleware)
├── models/         # SQLAlchemy ORM models
├── schemas/        # Pydantic request/response schemas
├── repositories/   # Database access layer
├── services/       # Business logic layer
├── routers/        # HTTP route handlers
├── dependencies/   # FastAPI Depends() factories
├── utils/          # Pure utility functions
└── main.py         # App factory and entry point
```

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI 0.115 |
| Language | Python 3.14 |
| Database | PostgreSQL (asyncpg driver) |
| ORM | SQLAlchemy 2.x (async) |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Auth | python-jose (JWT) + passlib (bcrypt) |
| Testing | Pytest + httpx + aiosqlite |
