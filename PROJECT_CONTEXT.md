# PROJECT CONTEXT: APAAR-Sutra

**Platform**: AICTE Student Data Management and Verification Platform  
**Problem Statement**: SIH Problem 26263  
**Status**: Production-Grade Architecture Baseline  

---

## 1. Product Summary
**APAAR-Sutra** is an enterprise-grade, secure, multi-tenant academic registry and verification hub designed for the All India Council for Technical Education (AICTE). The platform anchors student identity on the 12-digit **Automated Permanent Academic Account Registry (APAAR) ID** ("One Nation, One Student ID") linked with India's Academic Bank of Credits (ABC) and DigiLocker ecosystem. 

The platform enables AICTE-approved institutions to ingest, validate, and verify academic records in bulk; detects fraudulent credentials and duplicates using deterministic rules and anomaly detection; provides employers and agencies with an instant, authorized verification portal; and supplies national-level real-time analytics to the AICTE Directorate.

---

## 2. User Roles & Access Control
The platform implements fine-grained Role-Based Access Control (RBAC) with repository-level tenant scoping:

1. **`SUPER_ADMIN` (AICTE Directorate)**
   - Pan-India oversight across all institutions, states, and universities.
   - Access to aggregate analytics, anomaly alerts, policy enforcement, and audit logs.
   - Capability to onboard and suspend institutional tenant credentials.

2. **`INSTITUTION_ADMIN` (Registrar / Dean / College Authority)**
   - Strictly scoped to their own `institution_id`.
   - Ingests student enrollment, course progression, marks, and graduation data.
   - Resolves validation flags, duplicates, and anomaly alerts within their tenant.

3. **`STUDENT` (Academic Record Holder)**
   - Self-service portal to view academic ledger, credits, and verified credentials.
   - Manages verification consent tokens for external agencies.

4. **`VERIFIER` (Authorized Third-Party / Employer / University)**
   - Verified enterprise accounts querying student records via APAAR ID + consent token.
   - Download cryptographically signed verification transcripts.

---

## 3. Fixed Technology Stack

| Layer | Technology | Enforced Version / Specification |
| :--- | :--- | :--- |
| **Frontend** | React + Vite + TypeScript | React 18, Vite 5+, TypeScript 5+ |
| **Styling & Components**| Tailwind CSS + shadcn/ui | Radix UI primitives, Lucide Icons |
| **State & Data Fetching**| TanStack Query (React Query) | v5 (server-state cache, optimistic updates) |
| **Charts & Analytics** | Recharts | 2.12+ |
| **Localization** | i18next + react-i18next | English (`en`), Hindi (`hi`) |
| **Backend Framework** | Python + FastAPI | Python 3.12, FastAPI 0.111+ |
| **Data Validation** | Pydantic v2 + pydantic-settings| Rust-backed v2 core validation |
| **ORM & Database** | SQLAlchemy 2.0 + Alembic | Declarative 2.0 syntax, async/sync session management |
| **Relational Database**| PostgreSQL 16 | PostgreSQL 16 Alpine, UTF-8, strict foreign keys |
| **Cache & Message Broker**| Redis 7 | Redis 7 Alpine, persistent volumes |
| **Asynchronous Engine**| Celery + Celery Beat | Celery 5.4+ with Redis broker and result backend |
| **Reverse Proxy & Gateway**| Nginx | Nginx 1.25 Alpine, non-root runner |
| **Containerization** | Docker + Docker Compose | Multi-stage Dockerfiles, non-root user (UID 10001) |
| **CI/CD Pipeline** | GitHub Actions | Linting (Ruff, ESLint), Mypy, Vitest, Pytest, Docker Build |

---

## 4. Repository & Monorepo Layout

```text
/
├── .agent/rules/project.md                 # Antigravity directive pointing to this contract
├── .github/workflows/ci.yml                # CI automation pipeline
├── backend/                                # FastAPI application, Celery workers, Alembic
│   ├── app/
│   │   ├── api/                            # API routes, middleware, dependencies
│   │   ├── core/                           # Config, logging, exceptions, security
│   │   ├── models/                         # SQLAlchemy 2.0 declarative models
│   │   ├── schemas/                        # Pydantic v2 schemas
│   │   ├── repositories/                   # Tenant-scoped data access objects
│   │   ├── services/                       # Business logic services
│   │   ├── validation/                     # Ingestion & APAAR rule engine
│   │   ├── ml/                             # Anomaly detection & duplicate resolution
│   │   ├── integrations/                   # APAAR / DigiLocker / ABC adapters
│   │   ├── workers/                        # Celery app, tasks, and beat schedules
│   │   └── main.py                         # FastAPI application entry point
│   ├── alembic/                            # Database migrations
│   ├── mock_apaar/                         # Local mock server for National APAAR gateway
│   ├── tests/                              # Pytest suite
│   └── Dockerfile                          # Multi-stage non-root containerfile
├── frontend/                               # React 18 + Vite + TS SPA
│   ├── public/locales/                     # i18n translations (en, hi)
│   ├── src/
│   │   ├── components/                     # shadcn/ui and layout components
│   │   ├── lib/                            # API client, utils
│   │   ├── pages/                          # Application routes and views
│   │   └── routes/                         # React Router configuration
│   ├── tests/                              # Vitest suite
│   └── Dockerfile                          # Multi-stage static build with unprivileged Nginx
├── infra/                                  # Infrastructure configurations
│   ├── docker/                             # Reusable container definitions
│   ├── nginx/                              # Edge reverse proxy configuration
│   └── monitoring/                         # Prometheus and health monitors
├── docs/                                   # Architectural specifications & ADRs
│   ├── adr/0001-stack.md
│   └── architecture.md
├── scripts/                                # Maintenance, seeding, and verification scripts
├── data/                                   # Sample datasets & schemas
├── docker-compose.yml                      # Full local & staging composition
└── Makefile                                # Unified developer workflow CLI
```

---

## 5. Architectural & Coding Conventions

1. **API Versioning & Routing**:
   - All functional endpoints MUST reside under `/api/v1/`.
   - Operational health probes are exposed at `/api/v1/health` (liveness) and `/api/v1/ready` (readiness).
   - Interactive OpenAPI documentation is accessible at `/api/docs`.

2. **Standard Error Envelope**:
   - Every non-2xx response MUST strictly follow the standard JSON envelope:
     ```json
     {
       "error": {
         "code": "STRING_ERROR_CODE",
         "message": "Human readable explanation",
         "details": {},
         "request_id": "c1f7a0b3-6c8a-4d44-8d9e-bf36bc752a22"
       }
     }
     ```

3. **Request Tracing**:
   - The platform honors incoming `X-Request-ID` headers or mints a UUIDv4 if omitted.
   - The Request-ID is attached to Python context vars, injected into every structured JSON log, and returned in the HTTP response headers.

4. **Multi-Tenancy & Repository Isolation**:
   - Cross-institution data leakage is unacceptable.
   - Queries modifying or accessing student data MUST execute via repository methods that explicitly bind `institution_id` (except for audited `SUPER_ADMIN` system queries).

5. **PII Protection & Data Privacy**:
   - National identification numbers (Aadhaar references, raw APAAR credentials) and biometric markers MUST NEVER be logged or stored as plaintext.
   - Use salted hashes (SHA-256 / Argon2) for match verification and column-level encryption for at-rest storage.
   - UI views must mask sensitive identifiers (e.g., `XXXX-XXXX-1234`).

6. **Auditability on Every State Mutation**:
   - Every `CREATE`, `UPDATE`, `DELETE`, or verification transaction MUST write an immutable record to the `audit_logs` table capturing `actor_id`, `actor_role`, `action`, `resource_type`, `resource_id`, `client_ip`, and `diff_payload`.

7. **Time Standard**:
   - All timestamps in PostgreSQL (`TIMESTAMPTZ`), backend Python models (`datetime.datetime(..., tzinfo=timezone.utc)`), and JSON payloads MUST be strictly in **UTC**.
   - Frontends display localized time with explicit timezone labels (e.g., `IST / UTC`).

8. **Pagination Protocol**:
   - Collection endpoints MUST enforce cursor or offset pagination:
     ```json
     {
       "items": [],
       "total_items": 100,
       "page": 1,
       "page_size": 20,
       "total_pages": 5
     }
     ```

9. **Quality & Testing Requirement**:
   - Every service, router, and repository must be accompanied by unit tests.
   - Backend tests run under `pytest`; frontend tests run under `vitest`.
   - CI builds block on lint failures, type errors (`mypy`, `tsc`), or failing tests.

---

## 6. The 10 SIH 26263 Core Requirements Checklist

| Req # | Requirement Name | Description & Platform Implementation |
| :---: | :--- | :--- |
| **REQ-01** | **Centralized Student Academic Record Management** | Unified database storing student demographic, enrollment, course credit, and graduation records linked to a single permanent ledger. |
| **REQ-02** | **APAAR ID Integration & Verification** | Formal 12-digit APAAR validation engine with Verhoeff/Luhn checksum checking, format verification, and integration with the national mock gateway. |
| **REQ-03** | **Multi-Tenant Role-Based Access Control (RBAC)** | Strict isolation between AICTE Super Admin, College/Institution Admins, Students, and Third-Party Verifiers. |
| **REQ-04** | **Real-Time Record Verification & Fraud Detection** | Instant verification endpoint for employers and academic bodies with tamper-evident digital certificate verification. |
| **REQ-05** | **Bulk Data Ingestion & Async Pipeline** | Celery + Redis workers processing CSV/Excel institutional uploads asynchronously with progress streaming and error reporting. |
| **REQ-06** | **Data Privacy, Encryption & Consent Management** | AES-256 encryption at rest, field masking in logs and UI, and explicit student consent verification tokens for third parties. |
| **REQ-07** | **Tamper-Evident Audit Logging** | Append-only audit ledger recording every administrative mutation, verification query, and data export. |
| **REQ-08** | **Interactive Analytics & National Dashboard** | Real-time AICTE oversight dashboard featuring national enrollment charts, institutional verification status, and anomaly clusters. |
| **REQ-09** | **Multilingual Localization** | Native i18next support for English (`en`) and Hindi (`hi`), designed to support additional regional Indian languages. |
| **REQ-10** | **Academic Bank of Credits (ABC) & DigiLocker Interoperability** | Standardized JSON export/import schemas aligning with national ABC credit transfer schemas and DigiLocker pull URI protocols. |
