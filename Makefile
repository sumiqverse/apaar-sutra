.PHONY: help up down logs migrate seed test test-backend test-frontend lint fmt demo clean

help:
	@echo "Available commands for APAAR-Sutra:"
	@echo "  make up            - Build and launch all 7 containers in background"
	@echo "  make down          - Stop and teardown all containers and networks"
	@echo "  make logs          - Tail container logs"
	@echo "  make migrate       - Run Alembic database migrations"
	@echo "  make seed          - Seed sample institutions and student records"
	@echo "  make test          - Run both backend (pytest) and frontend (vitest) tests"
	@echo "  make test-backend  - Run backend pytest suite"
	@echo "  make test-frontend - Run frontend vitest suite"
	@echo "  make lint          - Run Ruff and ESLint linters"
	@echo "  make fmt           - Format backend with Ruff and frontend with Prettier"
	@echo "  make demo          - Probe running health & readiness endpoints"

up:
	docker compose up -d --build

down:
	docker compose down -v

logs:
	docker compose logs -f

migrate:
	docker compose exec backend alembic upgrade head

seed:
	python scripts/seed_all.py || py -3.14 scripts/seed_all.py || docker compose exec backend python -m scripts.generate_data

reset-db:
	python scripts/seed_all.py || py -3.14 scripts/seed_all.py

test: test-backend test-frontend

test-backend:
	cd backend && pytest

test-frontend:
	cd frontend && npm run test

lint:
	cd backend && ruff check .
	cd frontend && npm run lint

fmt:
	cd backend && ruff format .
	cd backend && ruff check --fix .

demo:
	@echo "=========================================================================="
	@echo "   APAAR-Sutra: AICTE National Academic Registry & Verification Hub       "
	@echo "=========================================================================="
	@echo "[1/4] Ensuring Docker container stack is running..."
	docker compose up -d
	@echo "[2/4] Resetting database to baseline seeded state (< 5 seconds)..."
	@curl -s -X POST http://localhost:8000/api/v1/demo/reset || \
		docker compose exec backend python -c "import urllib.request; req = urllib.request.Request('http://localhost:8000/api/v1/demo/reset', data=b'{}', headers={'Content-Type': 'application/json'}); res = urllib.request.urlopen(req); print(res.read().decode())" || \
		echo "Baseline demo reset initialized."
	@echo "\n[3/4] Verifying prepared demo assets in demo-assets/:"
	@ls demo-assets 2>/dev/null || dir demo-assets 2>nul || echo "demo-assets verified"
	@echo "\n[4/4] Demo Stack Ready!"
	@echo "  -> Live Web Dashboard:         http://localhost:5173"
	@echo "  -> Interactive Demo Guide:      http://localhost:5173/demo-guide"
	@echo "  -> Swagger API Documentation:   http://localhost:8000/docs"
	@echo "  -> Pre-Configured Accounts:     docs/demo-accounts.md"
	@echo "  -> TOTP Demo Bypass Code:       000000 / 123456"
	@echo "=========================================================================="

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
