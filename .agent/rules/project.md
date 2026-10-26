# Project Rules & Guidelines: APAAR-Sutra

This project is governed by the engineering and architecture contract defined in:
[PROJECT_CONTEXT.md](file:///c:/Users/sumit/OneDrive/Desktop/SIH/PROJECT_CONTEXT.md)

## Critical Directives:
1. **Fixed Stack**: React 18 + Vite + TypeScript + TailwindCSS + shadcn/ui + Recharts + TanStack Query + i18next (Frontend); Python 3.12 + FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2 (Backend); PostgreSQL 16; Redis 7; Celery + Beat; Docker Compose; Nginx. No substitutions allowed.
2. **Standard Error Envelope**: All API error responses MUST follow `{ "error": { "code": str, "message": str, "details": dict, "request_id": str } }`.
3. **Request Tracing**: Propagate `X-Request-ID` across all handlers, middleware, logs, and HTTP responses.
4. **Tenant Isolation**: Always enforce repository-level tenant scoping (`institution_id`) for non-superadmin actions.
5. **Security & Privacy**: Never log or store raw PII (Aadhaar/APAAR) in plaintext. Run non-root containers in Docker.
6. **Timestamps**: Always store and serialize timestamps in UTC (`TIMESTAMPTZ` / ISO 8601 UTC).
