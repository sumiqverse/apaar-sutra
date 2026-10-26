# APAAR-Sutra: Pre-Configured Demo Accounts & RBAC Matrix

**Platform**: AICTE Student Data Management and Verification Platform  
**Environment**: Development / Staging / Demonstration  

---

## 1. Demo Credentials Matrix

The following accounts are automatically provisioned when executing `make seed` or `scripts/generate_data.py`. Passwords can be overridden via environment variables in `.env`.

| Role | Email Address | Default Password | Environment Variable Override | Scope / Tenant Access |
| :--- | :--- | :--- | :--- | :--- |
| **`SUPER_ADMIN`** | `superadmin@aicte.gov.in` | `SuperAdmin@AICTE2026!` | `DEMO_SUPERADMIN_PASSWORD` | Global (All AICTE institutions pan-India, audit logs, national telemetry) |
| **`INSTITUTION_ADMIN`** | `director.iitm@aicte.gov.in` | `InstAdmin@AICTE2026!` | `DEMO_INSTITUTION_PASSWORD` | Scoped to **IITM Mumbai** (`1-100234901`) |
| **`INSTITUTION_ADMIN`** | `registrar.dtu@aicte.gov.in` | `InstAdmin@AICTE2026!` | `DEMO_INSTITUTION_PASSWORD` | Scoped to **DTU Delhi** (`1-100234902`) |
| **`STUDENT`** | `student.demo@aicte.gov.in` | `Student@AICTE2026!` | `DEMO_STUDENT_PASSWORD` | Personal academic ledger, consent management |
| **`VERIFIER`** | `verifier.tcs@tcs.com` | `Verifier@TCS2026!` | `DEMO_VERIFIER_PASSWORD` | Third-party background verification querying APAAR records |

---

## 2. Pre-Configured Roles and Permissions

```text
SUPER_ADMIN
├── institution:create, institution:read, institution:update, institution:delete
├── program:manage, program:read
├── student:read, student:write, student:audit
├── enrolment:read, enrolment:flag, enrolment:override
├── anomaly:view_all, anomaly:resolve_pan_india
├── audit:read_all, audit:export
└── system:configure, api_clients:manage

INSTITUTION_ADMIN (Tenant-Scoped)
├── institution:read_own, institution:update_own
├── program:create_own, program:read_own
├── batch:upload, batch:view_status
├── student:read_own, student:register_own
├── enrolment:create_own, enrolment:read_own, enrolment:update_own
├── anomaly:view_own, anomaly:acknowledge_own
└── api_client:manage_own

STUDENT
├── student:read_self
├── enrolment:read_self
├── credential:view_self, credential:download_transcript
└── consent:create, consent:revoke

VERIFIER
├── verification:query
├── credential:verify
└── consent:validate_token
```

---

## 3. Password Hashing Specification
All passwords are encrypted using **Argon2id** / PBKDF2 with SHA-256 and salted randomly. Plaintext passwords are never stored in the database.
