# APAAR-Sutra: Entity Relationship Diagram & Index Specification

**Platform**: AICTE Student Data Management and Verification Platform (SIH 26263)  
**Schema Revision**: Phase 1 Production Baseline  

---

## 1. Visual Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    states ||--o{ institutions : "houses"
    institutions ||--o{ programs : "offers"
    institutions ||--o{ enrolments : "registers"
    institutions ||--o{ upload_batches : "uploads"
    institutions ||--o{ validation_issues : "incurs"
    institutions ||--o{ user_institutions : "binds"
    institutions ||--o{ api_clients : "owns"
    institutions ||--o{ webhook_subscriptions : "subscribes"

    programs ||--o{ enrolments : "contains"
    programs ||--o{ validation_issues : "targets"

    students ||--o{ enrolments : "holds"
    students ||--o{ consent_requests : "authorizes"

    enrolments ||--o{ enrolment_history : "records_mutations"
    enrolments ||--o{ validation_issues : "triggers"
    enrolments ||--o{ issued_records : "generates"
    enrolments ||--o{ verification_logs : "queried_by"

    upload_batches ||--o{ enrolments : "batches"
    upload_batches ||--o{ validation_issues : "generates"

    users ||--o{ user_roles : "assigned"
    roles ||--o{ user_roles : "grants"
    roles ||--o{ role_permissions : "includes"
    permissions ||--o{ role_permissions : "defines"
    users ||--o{ user_institutions : "tenant_scoped_to"
    users ||--o{ refresh_tokens : "authenticates"
    users ||--o{ mfa_secrets : "secures"

    states {
        uuid id PK
        string code UK
        string name UK
    }

    institutions {
        uuid id PK
        string aicte_id UK
        string name
        uuid state_id FK
        string district
        string institution_type
        string status
        string email
        int approved_total_intake
        boolean is_deleted
    }

    programs {
        uuid id PK
        uuid institution_id FK
        string name
        string level
        string branch
        string academic_year
        int approved_intake
        float supernumerary_cap_pct
        int duration_years
        boolean is_deleted
    }

    students {
        uuid id PK
        string apaar_id "Plaintext indexable, masked on output"
        string apaar_status
        text name_enc "AES-256-GCM encrypted"
        text dob_enc "AES-256-GCM encrypted"
        text parent_name_enc "AES-256-GCM encrypted"
        text contact_enc "AES-256-GCM encrypted JSON"
        string gender
        string name_bidx "HMAC-SHA256 blind index"
        string dob_bidx "HMAC-SHA256 blind index"
        string parent_bidx "HMAC-SHA256 blind index"
        boolean is_deleted
    }

    enrolments {
        uuid id PK
        uuid student_id FK
        uuid program_id FK
        uuid institution_id FK
        string academic_year
        string student_ref_id
        string admission_category
        string quota_type
        boolean is_nri
        boolean oci_status
        boolean is_foreign_national
        string nationality
        text sponsor_details_enc "AES-256-GCM encrypted"
        date admission_date
        string status
        string validation_status
        float risk_score
        uuid source_batch_id FK
        boolean is_deleted
    }

    audit_logs {
        uuid id PK
        bigint seq UK
        string actor_id
        string action
        string entity_type
        string entity_id
        jsonb payload "GIN indexed"
        string prev_hash "Cryptographic chain"
        string hash "Tamper-evident SHA-256"
        timestamp timestamp
    }
```

---

## 2. Rationale for Constraints & Indexes

### A. Primary Key and Foreign Key Strategy
- **UUIDv4 Primary Keys**: Every entity uses a cryptographically random UUIDv4 (`as_uuid=True`), preventing sequential enumeration attacks and cross-tenant leakage.
- **Cascading Deletions**:
  - Dependent entities (`programs`, `enrolments`, `user_roles`) specify `ondelete="CASCADE"` when their parent record is deleted.
  - Foreign keys to historical references (e.g. `upload_batches.uploaded_by`, `validation_issues.resolved_by`) specify `ondelete="SET NULL"` to preserve auditability even after an administrative user account is removed.

### B. Unique Constraints vs. Anomaly Detection Strategy
- **`uq_programs_inst_name_branch_ay` on `(institution_id, name, branch, academic_year)`**:
  Guarantees that a single institution cannot define overlapping duplicate programs for the same cohort.
- **`uq_enrolments_student_inst_prog_ay` on `(student_id, institution_id, program_id, academic_year)`**:
  Guarantees that a student cannot be doubly enrolled in the *same* program within the *same* institution.
- **CRITICAL DESIGN RATIONALE: Cross-Institution Active Enrolments**:
  A global unique constraint on `(student_id, academic_year)` is **deliberately avoided**. In the real world, students illegally or mistakenly register for two full-time degrees across different universities. The platform's mission is to **ingest, identify, flag, and quarantine** fraudulent duplicate enrolments through the rule engine rather than throwing a raw database integrity error that drops the record from tracking!

### C. Check Constraints
- **`ck_students_apaar_id_format`**:
  `CHECK (apaar_id ~ '^[0-9]{12}$' OR apaar_id IS NULL)`
  Enforces that if an APAAR ID is present, it must strictly be 12 numeric digits. Missing or pending APAAR IDs are stored as `NULL` and flagged with status `UNVERIFIED` or `PENDING`.

### D. Composite & Performance Indexes
| Index Name | Table | Columns | Type / Method | Operational Rationale |
| :--- | :--- | :--- | :--- | :--- |
| `ix_enrolments_inst_ay` | `enrolments` | `(institution_id, academic_year)` | B-Tree | High-throughput college intake reconciliation and semester quota verification. |
| `ix_enrolments_student_id` | `enrolments` | `(student_id)` | B-Tree | Rapid retrieval of student academic history across institutions. |
| `ix_enrolments_ay_status` | `enrolments` | `(academic_year, status)` | B-Tree | National-level queries aggregating active student counts for a given academic year. |
| `ix_students_apaar_id` | `students` | `(apaar_id)` | B-Tree | Instant primary lookup by 12-digit APAAR ID from the verification portal and external gateways. |
| `ix_students_name_bidx` | `students` | `(name_bidx)` | B-Tree | Exact-match equality search on encrypted student names without decryption. |
| `ix_students_dob_bidx` | `students` | `(dob_bidx)` | B-Tree | Exact-match equality search on encrypted student dates of birth. |
| `ix_audit_logs_payload_gin` | `audit_logs` | `(payload)` | GIN | High-speed JSONB sub-key querying for forensic auditing and compliance investigations. |
| `ix_validation_rules_params_gin` | `validation_rules` | `(params)` | GIN | Enables dynamic parameter matching inside rule evaluation pipelines. |
| `ix_validation_issues_explanation_gin` | `validation_issues` | `(explanation)` | GIN | Filters and aggregates anomaly classifications across millions of validation issues. |
| `ix_audit_logs_seq` | `audit_logs` | `(seq)` | B-Tree Unique | Strict monotonic sequencing for tamper-evident cryptographic hash verification. |
