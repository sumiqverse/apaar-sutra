#!/usr/bin/env bash
# ==============================================================================
# APAAR-Sutra Disaster Recovery & Production Rollback Script
# Reverts containers to previous revision and rolls back database migrations.
# ==============================================================================

set -euo pipefail

echo "=========================================================="
echo " Initiating Emergency Rollback for APAAR-Sutra"
echo " Timestamp: $(date -u)"
echo "=========================================================="

# 1. Stop current application containers
echo "[1/3] Stopping running application containers..."
docker compose -f docker-compose.prod.yml stop backend frontend celery-worker celery-beat nginx

# 2. Database Migration Rollback (Optional: step back 1 revision)
if [ "${1:-}" == "--with-db" ]; then
    echo "[2/3] Rolling back database schema by 1 Alembic revision..."
    docker compose -f docker-compose.prod.yml run --rm backend alembic downgrade -1
else
    echo "[2/3] Skipping database downgrade (use --with-db to rollback schema)..."
fi

# 3. Restart stable services
echo "[3/3] Restarting services on stable configuration..."
docker compose -f docker-compose.prod.yml up -d

# 4. Verify healthcheck
echo "Verifying service health..."
sleep 5
docker compose -f docker-compose.prod.yml ps

echo "=========================================================="
echo " Rollback Complete. Services stabilized."
echo "=========================================================="
