# ADR 0001: Selection of Core Technology Stack for APAAR-Sutra

## Status
Accepted

## Context
AICTE (All India Council for Technical Education) requires a production-grade Student Data Management and Verification Platform (SIH Problem Statement 26263). The platform must manage academic credentials for millions of students across technical institutions in India, keyed by the 12-digit APAAR ID (Automated Permanent Academic Account Registry / One Nation, One Student ID).

The platform must satisfy:
1. High-throughput ingestion of student academic data across thousands of colleges.
2. Low-latency, cryptographically sound verification by third parties (employers, universities).
3. Resilient asynchronous processing with failure isolation and retry capabilities.
4. Strict multi-tenant data boundaries ensuring no cross-institution data contamination.
5. National-scale analytics with real-time anomaly detection.
6. Responsive, accessible, multilingual user interfaces supporting Indian regional workflows (Hindi, English).

## Decision
We enforce a fixed, standardized technology stack:

### 1. Frontend
- **React 18 + Vite + TypeScript**: Provides rapid Hot Module Replacement (HMR), static typing, and a mature component ecosystem.
- **Tailwind CSS + shadcn/ui**: Eliminates CSS bloat, provides accessible Radix UI primitives, and enables rapid iteration of an institutional dashboard design system.
- **TanStack Query (React Query) v5**: Handles asynchronous server-state caching, automatic refetching, and background synchronization for upload and verification jobs.
- **Recharts**: Modular SVG charting library for national enrollment and anomaly distribution graphs.
- **i18next + react-i18next**: Standardized internationalization supporting dual-language English (`en`) and Hindi (`hi`) parity.

### 2. Backend & Task Processing
- **Python 3.12 + FastAPI**: High-performance asynchronous REST API framework natively supporting OpenAPI 3.1 schema auto-generation.
- **Pydantic v2 + pydantic-settings**: Rust-based validation core offering 5x–10x speedup over v1, essential for processing large batches of student demographic and academic records.
- **SQLAlchemy 2.0 + Alembic**: Declarative database mapping, type-safe queries, transactional integrity, and automated schema migration histories.
- **Celery 5.4+ with Redis 7 Broker & Result Backend**: Offloads long-running CSV parsing, APAAR checksum validation, and fraud anomaly detection out of the HTTP request loop.
- **Celery Beat**: Handles scheduled audit log rotations, dead-letter queue reprocessing, and nightly synchronization with the mock National APAAR Gateway.

### 3. Data Storage & Caching
- **PostgreSQL 16**: Relational persistence providing ACID transactions, JSONB indexing for flexible academic transcripts, and robust row-level security capabilities.
- **Redis 7**: High-speed ephemeral cache for rate-limiting, session tokens, and message brokering.

### 4. Infrastructure & Gateway
- **Nginx**: Edge reverse proxy terminating TLS, routing traffic to `/` (SPA frontend) and `/api` (FastAPI backend), and injecting security headers.
- **Docker Compose**: Deterministic multi-container environment with non-root security profiles, automated healthcheck chains, and volume isolation.
- **GitHub Actions**: Automated CI matrix executing linting, static analysis, unit tests, and multi-stage container builds.

## Consequences
### Positive
- Strict separation of concerns between asynchronous ingestion pipelines and synchronous verification queries.
- Type safety end-to-end (TypeScript on frontend, Pydantic v2 + Mypy on backend).
- Unified multi-tenant architecture minimizing database overhead while guaranteeing tenant isolation.
- Fully local reproducibility via `docker-compose.yml` and unified `Makefile`.

### Negative / Trade-offs
- Managing Celery workers and Redis introduces operational complexity compared to a monolithic synchronous architecture, but is necessary for bulk ingestion.
- Multi-stage Docker builds require initial build time overhead, but result in minimal, secure production images.
