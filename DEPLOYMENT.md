# 🚀 CityFlowX AI - Complete Docker & Cloud Deployment Guide

This guide walks you through containerizing and deploying the **CityFlowX Smart Traffic AI Platform** across local Docker environments, single-server cloud VMs (AWS EC2, DigitalOcean), and managed cloud platforms (Render, Railway, Vercel, Google Cloud Run).

---

## 📋 Architecture Overview

- **Frontend**: Next.js 15 (React 19, TypeScript, TailwindCSS v4) — runs on Port `3000` (or behind Nginx)
- **Backend**: FastAPI (Python 3.10, Uvicorn, ML Models, APScheduler) — runs on Port `8000`
- **Reverse Proxy**: Nginx (optional unified gateway) — routes `/api/` to Backend and `/` to Frontend on Port `80` / `443`
- **Databases**: Supabase (PostgreSQL) + MongoDB Atlas (NoSQL Telemetry)

---

## 🐳 Option 1: One-Command Local or VM Deployment (Docker Compose)

The easiest and fastest way to deploy the entire stack together.

### 1. Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & Docker Compose installed.

### 2. Configure Environment Variables
Copy the environment template in the project root:
```bash
cp .env.production.example backend/.env
```
Edit `backend/.env` with your Supabase, MongoDB Atlas, and Traffic API credentials.

### 3. Run with Docker Compose

#### Standard Multi-Port (Frontend on :3000, Backend on :8000):
```bash
docker compose up --build -d
```
- Frontend UI: `http://localhost:3000`
- Backend Swagger Docs: `http://localhost:8000/docs`
- Healthcheck: `http://localhost:8000/health`

#### Production Mode with Nginx Reverse Proxy (Unified Port 80):
```bash
docker compose -f docker-compose.prod.yml up --build -d
```
- App + API Gateway: `http://localhost/`
- Backend API: `http://localhost/api/v1/`
- API Docs: `http://localhost/docs`

---

## ☁️ Option 2: 1-Click / Git Deployment on Render (PaaS)

Render provides an easy managed hosting environment for Docker containers.

### Method A: Blueprint Deployment (Fastest)
1. Push your repository to **GitHub**.
2. Go to [Render Dashboard](https://dashboard.render.com/) -> **New** -> **Blueprint**.
3. Connect your repository (`Team_4_Smart_Traffic_AI`).
4. Render will detect `render.yaml` automatically.
5. In the Render UI, input the secret environment variables (`POSTGRES_PASSWORD`, `MONGODB_URI`, `NEXT_PUBLIC_SUPABASE_URL`, etc.) when prompted.
6. Click **Apply**. Render will automatically build both Docker containers and link them!

### Method B: Manual Service Creation
1. **Backend Service**:
   - Create **New Web Service** -> Connect GitHub repo.
   - Root Directory: `backend`
   - Runtime: `Docker` (will use `backend/Dockerfile`).
   - Add Environment Variables from `.env.production.example`.
2. **Frontend Service**:
   - Create **New Web Service** -> Connect GitHub repo.
   - Root Directory: `frontend`
   - Runtime: `Docker` (will use `frontend/Dockerfile`).
   - Set `NEXT_PUBLIC_API_BASE_URL` to your backend's Render URL (e.g., `https://cityflowx-backend.onrender.com/api/v1`).

---

## ⚡ Option 3: Railway Deployment

1. Go to [Railway.app](https://railway.app/) and create a **New Project**.
2. Select **Deploy from GitHub repo**.
3. Add **Backend**:
   - Set Root Directory to `/backend`
   - Railway auto-detects `Dockerfile`.
   - In Settings -> Variables, add your backend environment variables.
   - Generate a Railway public domain (e.g., `https://cityflowx-backend.up.railway.app`).
4. Add **Frontend**:
   - Add a second service from the same repo with Root Directory `/frontend`.
   - Set environment variable `NEXT_PUBLIC_API_BASE_URL` to the Backend domain URL.
   - Generate a Railway public domain.

---

## 🌐 Option 4: Hybrid (Vercel Frontend + Docker Backend)

This gives you the best Next.js performance via Vercel's global Edge Network while keeping the Python AI backend containerized.

### 1. Deploy Backend (on Render, Railway, or Google Cloud Run)
Follow Option 2 or 3 to deploy the `backend/` container and get your public API URL (e.g. `https://cityflowx-backend.onrender.com`).

### 2. Deploy Frontend on Vercel
1. Go to [Vercel](https://vercel.com/) -> **Add New Project**.
2. Import your GitHub repository.
3. Set Root Directory to `frontend`.
4. Under **Environment Variables**, add:
   - `NEXT_PUBLIC_API_BASE_URL`: `https://cityflowx-backend.onrender.com/api/v1`
   - `NEXT_PUBLIC_SUPABASE_URL`: Your Supabase URL
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Your Supabase Anon Key
   - `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`: Your Google Maps Key
5. Click **Deploy**.

---

## 🖥️ Option 5: Cloud VM (AWS EC2 / DigitalOcean Droplet / Ubuntu) + Free SSL

For full control on a single virtual server ($4-$10/mo):

### 1. Provision Server
- Launch an Ubuntu 22.04 / 24.04 instance.
- In security groups / firewall, allow Ports **22 (SSH)**, **80 (HTTP)**, and **443 (HTTPS)**.

### 2. Install Docker & Clone Repository
```bash
# Update and install Docker
sudo apt update && sudo apt install -y docker.io docker-compose git

# Enable Docker without sudo
sudo usermod -aG docker $USER
newgrp docker

# Clone repository
git clone https://github.com/your-username/Team_4_Smart_Traffic_AI.git
cd Team_4_Smart_Traffic_AI

# Setup Environment Variables
cp .env.production.example backend/.env
nano backend/.env  # Fill in your DB & API keys
```

### 3. Launch Services
```bash
docker compose -f docker-compose.prod.yml up --build -d
```

### 4. Setup Free HTTPS with Let's Encrypt (Certbot)
If you pointed a domain (e.g., `traffic.yourdomain.com`) to your server IP:
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d traffic.yourdomain.com
```

---

## 🛠️ Option 6: Google Cloud Run (Serverless Containers)

### 1. Build & Push Backend to Google Artifact Registry:
```bash
# Authenticate
gcloud auth configure-docker

# Build & Push Backend
docker build -t gcr.io/YOUR_PROJECT_ID/cityflowx-backend:latest ./backend
docker push gcr.io/YOUR_PROJECT_ID/cityflowx-backend:latest

# Deploy to Cloud Run
gcloud run deploy cityflowx-backend \
  --image gcr.io/YOUR_PROJECT_ID/cityflowx-backend:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000 \
  --set-env-vars="PROJECT_NAME=CityFlowX AI,API_V1_STR=/api/v1,POSTGRES_HOST=your-supabase-host,POSTGRES_PASSWORD=your-db-pass,MONGODB_URI=your-mongo-uri"
```

---

## 🔍 Verification & Health Checks

Once deployed, verify the platform health:

| Component | Verification Endpoint | Expected Output |
| :--- | :--- | :--- |
| **API Health** | `GET /health` or `GET /api/v1/health` | `{"status": "healthy", "service": "CityFlowX AI"}` |
| **API Documentation** | `GET /docs` | Interactive Swagger UI |
| **Realtime Traffic AI** | `GET /api/v1/traffic/realtime` | Live congestion score, ML inference array |
| **Frontend UI** | `GET /` | Responsive landing page and Civilian/Controller dashboards |

---

## 🔒 Production Security Best Practices

1. **JWT Secret Key**: Always generate a 256-bit secret key in production (e.g., via `python -c "import secrets; print(secrets.token_hex(32))"`).
2. **Database Allowlist**: If using MongoDB Atlas or Supabase with IP restrictions, ensure your cloud host / container outbound IP or `0.0.0.0/0` (with strong passwords) is whitelisted.
3. **CORS Restrictions**: In `backend/app/main.py`, replace `allow_origins=["*"]` with your specific production frontend domain (e.g. `allow_origins=["https://your-frontend-domain.com"]`) if strict origin isolation is preferred.
