# ==============================================================================
# Multi-Stage Production Dockerfile for APAAR-Sutra Backend
# ==============================================================================

# --- Stage 1: Build Dependencies ---
FROM python:3.12-slim-bookworm AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Stage 2: Final Minimal Runtime ---
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/app:/install/lib/python3.12/site-packages"

# Install curl for container healthchecks and libpq5 for PostgreSQL client
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python dependencies from builder
COPY --from=builder /install /install

# Create non-root user (UID 10001)
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# Copy application source code and migrations
COPY --chown=appuser:appgroup app /app/app
COPY --chown=appuser:appgroup alembic /app/alembic
COPY --chown=appuser:appgroup alembic.ini /app/alembic.ini
COPY --chown=appuser:appgroup mock_apaar /app/mock_apaar

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
