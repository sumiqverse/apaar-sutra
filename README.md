# APAAR-Sutra: AICTE Student Data Management and Verification Platform

[![CI Pipeline](https://github.com/aicte/apaar-sutra/actions/workflows/ci.yml/badge.svg)](https://github.com/aicte/apaar-sutra/actions)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3-61DAFB?logo=react)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-5.2-646CFF?logo=vite)](https://vitejs.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis)](https://redis.io)

**Smart India Hackathon (SIH) Problem Statement 26263**  
**AICTE Student Data Management and Verification Platform Keyed on 12-Digit APAAR ID**

---

## 🏛️ Executive Summary
**APAAR-Sutra** is an enterprise-grade academic registry and real-time verification hub designed for AICTE institutions across India. Built on the national 12-digit **APAAR ID (Automated Permanent Academic Account Registry / One Nation, One Student ID)**, the platform ingests, validates, de-duplicates, and verifies student enrollment, academic progression, and awarded credentials.

---

## ⚡ Fixed Architecture & Technology Stack

| Layer | Component | Specification |
| :--- | :--- | :--- |
| **Frontend** | React 18 + Vite + TypeScript | Strict typing, HMR, modular SPA architecture |
| | Tailwind CSS + shadcn/ui | High-density dashboard system with Lucide icons |
| | TanStack Query v5 | Server-state caching and background synchronization |
| | Recharts | State-level and national academic charts |
| | i18next (`en`, `hi`) | Dual-language English and Hindi localization |
| **Backend** | Python 3.12 + FastAPI | Native asynchronous endpoints with OpenAPI 3.1 |
| | Pydantic v2 + pydantic-settings | High-speed Rust-based data validation |
| | SQLAlchemy 2.0 + Alembic | Declarative mapping, tenant-isolated repositories |
| | Celery 5.4 + Celery Beat | Asynchronous bulk ingestion & scheduled anomaly sweeps |
| **Data Stores** | PostgreSQL 16 (Alpine) | ACID relational data with multi-tenant row security |
| | Redis 7 (Alpine) | Cache, rate limiter, and Celery message broker |
| **Gateway & Infra** | Nginx (Alpine) | Reverse proxy routing `/` to SPA and `/api` to backend |
| | Docker Compose v2 | Multi-stage, non-root (UID 10001) containers with healthchecks |
| | GitHub Actions CI | Automated linting, type-checking, tests, and image builds |

---

## 📁 Repository Directory Structure

```text
/
├── .agent/rules/project.md                 # Antigravity agent rules pointing to master contract
├── .github/workflows/ci.yml                # Multi-job GitHub Actions CI pipeline
├── backend/                                # FastAPI API, Celery worker, Alembic migrations
│   ├── app/
│   │   ├── api/                            # Routers (/health, /ready, /v1), deps, middleware
│   │   ├── core/                           # Config, logging, exceptions, security
│   │   ├── models/                         # SQLAlchemy 2.0 entities (Institution, Student, Audit)
│   │   ├── schemas/                        # Pydantic v2 validation models
│   │   ├── repositories/                   # Tenant-isolated data access layer
│   │   ├── services/                       # Verification service with HMAC signatures
│   │   ├── validation/                     # 12-digit Verhoeff APAAR rule engine
│   │   ├── ml/                             # Cross-college anomaly & fraud detection
│   │   ├── integrations/                   # National APAAR registry client adapters
│   │   ├── workers/                        # Celery app, tasks, and beat schedules
│   │   └── main.py                         # Application factory & router mounts
│   ├── alembic/                            # Database migrations (0001_initial_schema.py)
│   ├── mock_apaar/                         # Local mock server mimicking government gateway
│   ├── tests/                              # Pytest suite (health, tracing, errors, checksums)
│   └── Dockerfile                          # Multi-stage non-root containerfile
├── frontend/                               # React 18 + TypeScript + Vite SPA
│   ├── public/locales/                     # i18n translations (en, hi)
│   ├── src/
│   │   ├── components/                     # Layout (Navbar, Sidebar, Shell), LanguageSwitcher
│   │   ├── lib/                            # API client with X-Request-ID and utils
│   │   ├── pages/                          # Health diagnostics, Dashboard, NotFound
│   │   └── routes/                         # React Router configuration
│   ├── tests/                              # Vitest suite for component testing
│   └── Dockerfile                          # Multi-stage build served via unprivileged Nginx
├── infra/                                  # Infrastructure definitions
│   ├── docker/                             # Dockerfile.backend & Dockerfile.frontend
│   ├── nginx/nginx.conf                    # Edge gateway: / -> frontend, /api -> backend
│   └── monitoring/prometheus.yml           # Prometheus telemetry scrape configurations
├── docs/                                   # Architecture specs and ADRs
│   ├── adr/0001-stack.md                   # Architectural decision record for technology stack
│   └── architecture.md                     # C4 Context, Container, and Ingestion flow diagrams
├── scripts/                                # Database seeding and wait-for scripts
├── data/                                   # Sample student ingestion CSVs
├── docker-compose.yml                      # Production-grade 7-service composition
├── Makefile                                # Developer CLI (up, down, test, lint, demo)
├── .env.example                            # Documented environment variables
├── PROJECT_CONTEXT.md                      # Engineering contract & 10 SIH requirements
└── README.md
```

---

## 🚀 Quick Start

### 1. Prerequisites
- Docker Engine 24+ and Docker Compose v2+
- Make (optional, commands can be executed directly via docker compose)

### 2. Launch the Platform
```bash
# Clone the repository
git clone https://github.com/aicte/apaar-sutra.git
cd apaar-sutra

# Start all 7 containers in the background with healthchecks
make up
# Alternatively: docker compose up -d --build
```

### 3. Initialize & Seed Database
```bash
# Run database migrations
make migrate

# Seed sample AICTE colleges, students, and academic records
make seed
```

### 4. Verify Endpoints
Once containers report healthy:
- **Frontend Dashboard**: [http://localhost/](http://localhost/)
- **Live Health Diagnostics**: [http://localhost/health](http://localhost/health)
- **Interactive OpenAPI Docs**: [http://localhost/api/docs](http://localhost/api/docs)
- **Liveness Probe**: `curl http://localhost/api/v1/health`
- **Readiness Probe**: `curl http://localhost/api/v1/ready`

---

## 🧪 Testing & Quality Assurance

### Run All Tests
```bash
make test
```

### Backend Tests Only (Pytest)
```bash
make test-backend
```

### Frontend Tests Only (Vitest)
```bash
make test-frontend
```

### Linting & Formatting
```bash
make lint
make fmt
```

---

## 🔒 Security & Privacy Guarantees
1. **PII Protection**: Raw national identity credentials (Aadhaar references, plaintext APAAR IDs) are salted, hashed (SHA-256), and masked in logs/UI (`XXXX-XXXX-1234`).
2. **Tenant Scoping**: All institutional queries require repository-level scoping on `institution_id`.
3. **Correlation Tracing**: Every request is tagged with an `X-Request-ID` propagated through Python context variables, structured JSON logs, and response headers.
4. **Standard Error Envelope**: All API errors adhere to `{ "error": { "code", "message", "details", "request_id" } }`.
5. **Non-Root Containers**: Containers run under dedicated non-root service users (`appuser` UID 10001 in backend; `nginxinc/nginx-unprivileged` in frontend).
