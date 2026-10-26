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
	docker compose exec backend python -m scripts.seed_db

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
	@echo "=== Checking Liveness Probe (/api/v1/health) ==="
	@curl -s http://localhost/api/v1/health | python -m json.tool || curl -s http://localhost:8000/api/v1/health | python -m json.tool
	@echo "\n=== Checking Readiness Probe (/api/v1/ready) ==="
	@curl -s http://localhost/api/v1/ready | python -m json.tool || curl -s http://localhost:8000/api/v1/ready | python -m json.tool
	@echo "\n=== Swagger API Documentation ==="
	@echo "Swagger UI accessible at http://localhost/api/docs"
	@echo "Frontend Dashboard accessible at http://localhost/"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
