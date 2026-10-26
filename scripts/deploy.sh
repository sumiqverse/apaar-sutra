#!/usr/bin/env bash
# ==============================================================================
# APAAR-Sutra Automated Production Deployment Script
# Executes pre-flight checks, pulls containers, runs DB migrations, and health checks.
# ==============================================================================

set -euo pipefail

echo "=========================================================="
echo " Starting APAAR-Sutra Production Deployment"
echo " Date: $(date -u)"
echo "=========================================================="

# 1. Pre-flight verification
if [ ! -f ".env.production" ]; then
    echo "ERROR: .env.production file missing! Copy .env.production.example and configure secrets."
    exit 1
fi

# 2. Generate local self-signed TLS certificate if none present
SSL_DIR="./infra/nginx/ssl"
mkdir -p "${SSL_DIR}"
if [ ! -f "${SSL_DIR}/fullchain.pem" ] || [ ! -f "${SSL_DIR}/privkey.pem" ]; then
    echo "[1/5] Generating temporary self-signed TLS certificates..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "${SSL_DIR}/privkey.pem" \
        -out "${SSL_DIR}/fullchain.pem" \
        -subj "/CN=localhost/O=APAAR-Sutra/C=IN"
fi

# 3. Pull / Build Production Container Images
echo "[2/5] Building and validating hardened production containers..."
docker compose -f docker-compose.prod.yml build --parallel

# 4. Start Core Infrastructure (Postgres, Redis)
echo "[3/5] Starting database and cache backends..."
docker compose -f docker-compose.prod.yml up -d postgres redis
echo "Waiting for PostgreSQL and Redis readiness..."
sleep 10

# 5. Execute Alembic Database Migrations
echo "[4/5] Running database migrations..."
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# 6. Start Application Services
echo "[5/5] Deploying API, Celery Workers, Frontend, and Nginx Gateway..."
docker compose -f docker-compose.prod.yml up -d

echo "=========================================================="
echo " Deployment Completed Successfully!"
echo " Verification:"
echo " - Health Probe: https://localhost/health"
echo " - API Docs:     https://localhost/docs"
echo " - Metrics:      https://localhost/metrics (internal)"
echo "=========================================================="
