# APAAR-Sutra Role-Based Access Control (RBAC) Matrix

**Platform**: AICTE APAAR-Sutra  
**Document**: RBAC & Authorization Specification  
**Version**: 1.0 (Phase 2 Security Core)  

---

## 1. System Roles Overview

| Role Code | Role Name | Jurisdiction / Tenant Boundary | MFA Mandatory |
| :--- | :--- | :--- | :---: |
| **`SUPER_ADMIN`** | AICTE National Super Administrator | Pan-India (All institutions, all states) | **Yes** |
| **`AICTE_OFFICER`** | AICTE Directorate Nodal Officer | Pan-India (All institutions) | **Yes** |
| **`AICTE_ANALYST`** | AICTE Policy & Data Analyst | Pan-India (Read-only analytics & reports) | No |
| **`INSTITUTION_ADMIN`**| College Principal / Registrar / Dean | Institution-Scoped (`institution_ids`) | **Yes** |
| **`INSTITUTION_OPERATOR`**| College Academic Data Operator | Institution-Scoped (`institution_ids`) | No |
| **`VERIFIER`** | Authorized Employer / University Verifier| Cross-tenant verification via consent | No |
| **`AUDITOR`** | Statutory Compliance & Audit Inspector | Pan-India (Append-only audit logs & chain) | **Yes** |
| **`STUDENT`** | Student Academic Record Holder | Self-Record Scoped (`student_id`) | No |

---

## 2. Permissions Definition

| Permission Code | Description | Sensitive / PII |
| :--- | :--- | :---: |
| `students:read` | View student list and academic records (masked APAAR `XXXXXXXX1234`) | No |
| `students:read_full` | View unmasked 12-digit APAAR ID and demographic PII | **Yes** |
| `students:write` | Enroll, modify, and manage student demographic records | **Yes** |
| `batches:upload` | Upload bulk ingestion files (CSV/XLSX) | No |
| `batches:read` | View ingestion batch status, row metrics, and parsing issues | No |
| `rules:manage` | Configure validation rules, anomaly thresholds, and weights | No |
| `rules:read` | View active rule configurations and explanations | No |
| `audit:read` | Query and filter immutable system audit trails | **Yes** |
| `audit:verify` | Run cryptographic SHA-256 hash chain verification | No |
| `reports:generate` | Download analytical reports, YoY trends, and enrollment digests | No |
| `verification:request` | Submit verification requests for student credentials | No |
| `verification:verify` | Access verification results and cryptographic digital proofs | No |
| `users:manage` | Create, invite, deactivate users and assign institutional roles | **Yes** |
| `users:read` | View user profiles and active sessions within scope | No |

---

## 3. Role-Permission Assignment Matrix

| Permission | `SUPER_ADMIN` | `AICTE_OFFICER` | `AICTE_ANALYST` | `INSTITUTION_ADMIN` | `INSTITUTION_OPERATOR` | `VERIFIER` | `AUDITOR` | `STUDENT` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `students:read` |  |  |  |  |  |  |  | (Self) |
| `students:read_full` |  |  | ❌ |  | ❌ | ❌ | ❌ | (Self) |
| `students:write` |  |  | ❌ |  |  | ❌ | ❌ | ❌ |
| `batches:upload` |  | ❌ | ❌ |  |  | ❌ | ❌ | ❌ |
| `batches:read` |  |  |  |  |  | ❌ | ❌ | ❌ |
| `rules:manage` |  |  | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `rules:read` |  |  |  |  |  | ❌ |  | ❌ |
| `audit:read` |  | ❌ | ❌ | ❌ | ❌ | ❌ |  | ❌ |
| `audit:verify` |  | ❌ | ❌ | ❌ | ❌ | ❌ |  | ❌ |
| `reports:generate` |  |  |  |  | ❌ | ❌ |  | ❌ |
| `verification:request`|  |  | ❌ |  | ❌ |  | ❌ | ❌ |
| `verification:verify` |  |  | ❌ | ❌ | ❌ |  | ❌ | ❌ |
| `users:manage` |  |  | ❌ |  (Own Inst) | ❌ | ❌ | ❌ | ❌ |
| `users:read` |  |  |  |  | ❌ | ❌ |  | ❌ |

---

## 4. API Route Authorization Matrix

| Endpoint | HTTP Method | Required Permission / Role | Tenant-Scoped? |
| :--- | :---: | :--- | :---: |
| `/api/v1/auth/login` | `POST` | Public (Rate-limited: 5/min) | No |
| `/api/v1/auth/mfa/verify` | `POST` | Public with `temp_token` | No |
| `/api/v1/auth/mfa/enroll` | `POST` | Authenticated User | No |
| `/api/v1/auth/mfa/confirm` | `POST` | Authenticated User | No |
| `/api/v1/auth/refresh` | `POST` | Public with `refresh_token` | No |
| `/api/v1/auth/logout` | `POST` | Public with `refresh_token` | No |
| `/api/v1/auth/logout-all` | `POST` | Authenticated User | No |
| `/api/v1/auth/me` | `GET` | Authenticated User | No |
| `/api/v1/auth/change-password` | `POST` | Authenticated User | No |
| `/api/v1/students` | `GET` | `students:read` | **Yes** |
| `/api/v1/students/{apaar_id}` | `GET` | `students:read` | **Yes** |
| `/api/v1/audit` | `GET` | `audit:read` (`AUDITOR`, `SUPER_ADMIN`) | Pan-India |
| `/api/v1/audit/verify-chain` | `GET` | `audit:verify` (`AUDITOR`, `SUPER_ADMIN`) | Pan-India |

---

## 5. Non-Bypassable Repository Isolation Guarantees

1. **Repository Auto-Scoping**:
   - `BaseRepository` queries unconditionally inspect `tenant_context`.
   - If caller is institutional (`INSTITUTION_ADMIN`, `INSTITUTION_OPERATOR`), `institution_id.in_(tenant_context.institution_ids)` is appended to SQL queries at the ORM layer.
   - Direct database access bypassing FastAPI route controllers cannot leak records outside the user's institutional jurisdiction.

2. **Output Masking**:
   - All student responses sanitize `apaar_id` to `XXXXXXXX1234` unless caller possesses `students:read_full`.
   - Demographic fields (`name`, `dob`, `parent_name`) are obfuscated for verifiers or non-administrative staff.
