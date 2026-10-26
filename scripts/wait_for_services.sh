#!/usr/bin/env bash
set -e

echo "⏳ Waiting for PostgreSQL (postgres:5432)..."
until pg_isready -h postgres -p 5432 -U apaar_user; do
  >&2 echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done

echo "⏳ Waiting for Redis (redis:6379)..."
until redis-cli -h redis ping | grep -q PONG; do
  >&2 echo "Redis is unavailable - sleeping"
  sleep 2
done

echo "✅ All dependent storage engines are healthy and accepting connections."
exec "$@"
