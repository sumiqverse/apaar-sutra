# APAAR-Sutra: Architecture Documentation

**Platform**: AICTE Student Data Management and Verification Platform  
**Problem Statement**: SIH 26263  
**Design Reference**: C4 Architecture Model & National Ingestion Pipeline  

---

## 1. System Context Diagram (C4 Level 1)

The system context diagram illustrates the external actors and systems interacting with **APAAR-Sutra**.

```mermaid
graph TD
    subgraph Users["Platform Stakeholders"]
        InstAdmin["Institutional Admin (Registrar / Dean)"]
        StudentUser["Student / Credential Holder"]
        VerifierUser["Third-Party Verifier (Employer / Higher-Ed)"]
        AicteAdmin["AICTE Directorate (Super Admin)"]
    end

    subgraph Platform["APAAR-Sutra Platform Boundary"]
        ApaarSystem["APAAR-Sutra Core System"]
    end

    subgraph ExternalSystems["External National Ecosystem"]
        NationalApaar["National APAAR Registry Gateway"]
        DigiLocker["DigiLocker / ABC API"]
        AadhaarVault["UIDAI Aadhaar Tokenizer / e-KYC"]
    end

    InstAdmin -->|"Batch upload student records (CSV/Excel)"| ApaarSystem
    StudentUser -->|"View academic ledger, manage consent"| ApaarSystem
    VerifierUser -->|"Submit verification query with APAAR ID"| ApaarSystem
    AicteAdmin -->|"Monitor national enrollment and fraud metrics"| ApaarSystem

    ApaarSystem -->|"Verify APAAR ID syntax and checksum"| NationalApaar
    ApaarSystem -->|"Sync academic credits and award transcripts"| DigiLocker
    ApaarSystem -->|"Validate identity tokens"| AadhaarVault
```

---

## 2. Container Diagram (C4 Level 2)

The container diagram displays the internal micro-services, databases, proxies, and background processing workers that comprise **APAAR-Sutra**.

```mermaid
graph TB
    ClientBrowser["Client Browser (Desktop / Mobile)"]

    subgraph EdgeTier["Edge Gateway"]
        NginxProxy["Nginx Reverse Proxy (Port 80/443)"]
    end

    subgraph PresentationTier["Presentation Layer"]
        FrontendSPA["Frontend SPA (React 18, Vite, TypeScript, Tailwind, i18next)"]
    end

    subgraph ApplicationTier["Application & API Layer"]
        FastApiBackend["FastAPI Backend (Python 3.12, Pydantic v2, SQLAlchemy 2.0)"]
        CeleryWorker["Celery Worker Nodes (Batch Processing & Validation)"]
        CeleryBeat["Celery Beat Scheduler (Periodic Tasks & Audits)"]
    end

    subgraph StorageTier["Data & Cache Layer"]
        PostgresDB[("PostgreSQL 16 (Primary Relational Store)")]
        RedisStore[("Redis 7 (Broker, Cache, Result Backend)")]
    end

    subgraph IntegrationTier["Integration Adapters"]
        MockApaarService["Mock National APAAR Gateway Service"]
    end

    ClientBrowser -->|"HTTPS /"| NginxProxy
    NginxProxy -->|"Static Assets / SPA Routing"| FrontendSPA
    NginxProxy -->|"Proxy API Requests /api/v1"| FastApiBackend

    FastApiBackend -->|"Read / Write Academic & Audit Data"| PostgresDB
    FastApiBackend -->|"Session Cache & Rate Limiting"| RedisStore
    FastApiBackend -->|"Enqueue Ingestion & Verification Jobs"| RedisStore

    RedisStore -->|"Consume Task Queue"| CeleryWorker
    CeleryBeat -->|"Schedule Recurring Jobs"| RedisStore
    CeleryWorker -->|"Write Ingestion Status & Anomaly Flags"| PostgresDB
    CeleryWorker -->|"Verify APAAR IDs"| MockApaarService
    FastApiBackend -->|"Direct APAAR Lookups"| MockApaarService
```

---

## 3. Data Flow Diagram: Ingestion, Validation & Verification

This diagram depicts the end-to-end data lifecycle:  
**Institution $\rightarrow$ Upload $\rightarrow$ APAAR Validation $\rightarrow$ Rule Engine + Anomaly Detection $\rightarrow$ Verified $\rightarrow$ AICTE Central Repository $\rightarrow$ Analytics $\rightarrow$ Authorized Verification**.

```mermaid
flowchart TD
    A["1. Institution Admin"] -->|"Uploads bulk student batch (CSV/JSON)"| B["2. Ingestion Gateway (FastAPI)"]
    B -->|"Validates file structure & generates upload batch ID"| C["3. Redis Task Queue"]
    C -->|"Dispatches ingestion job"| D["4. Celery Worker Pipeline"]

    subgraph ProcessingPipeline["Asynchronous Processing & Validation Engine"]
        D --> E["5. APAAR Validation: 12-digit format, Luhn/Verhoeff checksum check"]
        E -->|"Valid checksum"| F["6. Rule Engine: Academic eligibility, credit sum, prerequisite logic"]
        E -->|"Invalid format"| ErrSink["Reject Record & Log Error"]
        F --> G["7. Anomaly & Duplicate Detection: Cross-college double-enrollment checks"]
        G -->|"Anomaly flagged"| FlagSink["Quarantine Record for Review"]
        G -->|"Passed validation"| H["8. Verified Academic Record"]
    end

    H -->|"Commit with cryptographic audit hash"| I[("9. AICTE Central Repository (PostgreSQL 16)")]
    
    subgraph DownstreamServices["Consumer Services"]
        I -->|"Aggregate metrics and anomaly reports"| J["10. Real-time National Analytics (Recharts Dashboard)"]
        I -->|"Fetch validated credentials with student consent"| K["11. Authorized Verification Portal (Employers / Agencies)"]
    end
```

---

## 4. Key Architectural Safeguards

1. **Strict Multi-Tenancy**:
   - Each database transaction initiated by an `INSTITUTION_ADMIN` enforces `institution_id = current_tenant.id` through repository-level filtering.
2. **Deterministic & Anomaly Detection Pipeline**:
   - Level 1: Deterministic syntax check (12-digit format, Luhn/Verhoeff checksum).
   - Level 2: Semantic check against mock/live government registry.
   - Level 3: Cross-college anomaly detection ensuring no student is concurrently enrolled in two full-time degree programs.
3. **Audit Trail Immutability**:
   - Write actions to records produce append-only audit entries containing before-and-after payloads, actor ID, client IP, and UTC timestamps.
