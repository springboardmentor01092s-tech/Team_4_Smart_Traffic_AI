# ─── Stage 1: Base Image ──────────────────────────────────────────────────────
FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

WORKDIR /app

# Install minimal OS runtime dependencies (curl for container healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source, migrations, and configuration
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .
COPY pyproject.toml .
COPY entrypoint.sh .

# Create non-root user and set permissions
RUN useradd -m -u 1001 appuser && \
    chmod +x entrypoint.sh && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Container healthcheck using liveness endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/live || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
