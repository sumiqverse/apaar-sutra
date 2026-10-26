# APAAR-Sutra High-Scale Architecture & Capacity Roadmap

**Blueprint**: Scaling to 15,000+ AICTE Institutions & 3+ Crore (30,000,000) Student Records  
**Document Status**: Official Architecture Specification  

---

## 1. Scale Target Metrics & Throughput Assumptions

| Metric | Target Dimension |
| :--- | :--- |
| **Total Regulated Institutions** | 15,000+ Engineering, Management, and Technical Colleges across India |
| **Active Enrolment Database Size** | 30,000,000+ (3+ Crore) records across a rolling 4-year undergraduate cycle |
| **Annual New Enrolments** | ~7,500,000 students / year |
| **Peak Admission Season Throughput** | 10,000 batch uploads / hour during July–September cut-off window |
| **Third-Party Verification Traffic** | 500 requests / second during national recruitment cycles |
| **Latency SLA Targets** | Analytics Dashboards p95 < 250ms; Verifications p99 < 150ms |

---

## 2. PostgreSQL Declarative Table Partitioning

The `enrolments` and `audit_logs` tables represent >85% of total database volume. At 3 crore rows, standard B-tree indexes exceed RAM cache limits.

### 2.1 Range Partitioning by `academic_year`
We enforce PostgreSQL 16 declarative range partitioning on `enrolments`:

```sql
-- Parent Table Partitioned by Range
CREATE TABLE enrolments_partitioned (
    id UUID NOT NULL,
    student_id UUID NOT NULL,
    institution_id UUID NOT NULL,
    program_id UUID NOT NULL,
    academic_year VARCHAR(20) NOT NULL,
    student_ref_id VARCHAR(100) NOT NULL,
    quota_type VARCHAR(30) DEFAULT 'REGULAR',
    admission_category VARCHAR(30) DEFAULT 'GEN',
    status VARCHAR(30) DEFAULT 'ACTIVE',
    admission_date DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()),
    PRIMARY KEY (id, academic_year)
) PARTITION BY LIST (academic_year);

-- Annual Partitions
CREATE TABLE enrolments_y2023_24 PARTITION OF enrolments_partitioned FOR VALUES IN ('2023-24');
CREATE TABLE enrolments_y2024_25 PARTITION OF enrolments_partitioned FOR VALUES IN ('2024-25');
CREATE TABLE enrolments_y2025_26 PARTITION OF enrolments_partitioned FOR VALUES IN ('2025-26');
CREATE TABLE enrolments_y2026_27 PARTITION OF enrolments_partitioned FOR VALUES IN ('2026-27');
```

### 2.2 Benefits
- **Partition Pruning**: Queries with `WHERE academic_year = '2025-26'` scan only the active 7.5M row partition, reducing disk I/O by 75%.
- **Zero-Downtime Archival**: Past academic years (e.g. 2018-19) can be detached and migrated to cold columnar storage (Parquet / S3) without table locking.

---

## 3. Database Connection Pooling with PgBouncer & Read Replicas

```mermaid
graph TD
    A["API Pods / Celery Workers (FastAPI / Celery)"] -->|Hundreds of Connections| B["PgBouncer Poolers (Transaction Mode)"]
    B -->|Persistent Low Connections (max 100)| C["Primary PostgreSQL 16 (Writes & Critical Read)"]
    C -->|Streaming WAL Replication| D["Read Replica 1 (Analytics Queries)"]
    C -->|Streaming WAL Replication| E["Read Replica 2 (Verifier Portal & Reports)"]
```

1. **PgBouncer Configuration**:
   - `pool_mode = transaction`: Recycles server connections after every single transaction block. Allows 5,000+ FastAPI and Celery worker workers to be serviced by 150 dedicated backend Postgres connections.
2. **Read Replica Routing in SQLAlchemy**:
   - Read replicas service `/api/v1/analytics/` and `/api/v1/reports/` read traffic.
   - Primary database handles `POST /api/v1/integration/students` and state mutations with strict write serialization.

---

## 4. Celery Queue Separation & Horizontal Autoscaling

To prevent large institutional batch uploads from blocking real-time anomaly alerts or webhook dispatches, Celery queues are isolated into distinct Kubernetes deployments / worker pools:

| Queue Name | Concurrency Strategy | Worker Autoscaling Metric |
| :--- | :--- | :--- |
| `ingestion_queue` | Gevent / prefork workers (chunk size 500) | Scaled on RabbitMQ/Redis queue depth (`> 500 tasks`) |
| `reports_queue` | Memory-optimized workers (ReportLab / Pandas) | Scaled on CPU utilization (`> 75%`) |
| `webhooks_queue` | High-concurrency async I/O event loops | Scaled on pending HTTP retries |
| `anomalies_queue` | Celery Beat scheduled nightly isolation forest runs | Fixed batch worker allocation |

---

## 5. Multi-Tier Caching Architecture

1. **L1 In-Memory Cache (Python Process)**:
   - Caches immutable system validation rules and well-known public keys for 5 minutes (`cachetools.TTLCache`).
2. **L2 Distributed Cache (Redis 7 Cluster)**:
   - **National Dashboard Metrics**: Pre-aggregated national KPI totals and state breakdown cached with 60-second TTL.
   - **Active Nonces**: Anti-replay tokens stored with 300-second TTL (`SETNX`).
   - **Idempotency Replay Cache**: API client responses cached for 24 hours.
3. **Invalidation Strategy**:
   - Cache tags invalidated on `batch.completed` events for the specific `institution_id` and state.

---

## 6. Object Storage (S3 / MinIO) & Edge CDN

- **Bulk CSV / Excel Staging**:
  - Uploaded institutional files stored in S3 bucket (`s3://apaar-sutra-ingestion-uploads/`) with SSE-S3 AES-256 server-side encryption and 30-day lifecycle auto-purge.
- **Compiled PDF Certificates & Statutory Reports**:
  - Server-side generated PDFs uploaded to private bucket with signed pre-signed URLs (15-minute expiry).
- **Edge CDN (Cloudflare / AWS CloudFront)**:
  - Serves compiled React SPA assets, fonts, and localization bundles (`/locales/en/translation.json`, `/locales/hi/translation.json`) with `Cache-Control: public, max-age=31536000, immutable`.

---

## 7. Cloud Infrastructure Cost Estimate Outline (Annual)

| Component | Specification | Annual Cost Estimate (USD / INR) |
| :--- | :--- | :--- |
| **Primary DB Cluster** | PostgreSQL 16 (64 vCPU, 256GB RAM, 2TB NVMe SSD) + 2 Read Replicas | $14,400 / ₹12,00,000 |
| **PgBouncer & Cache** | 3-Node Redis 7 Cluster (32GB RAM each) | $2,880 / ₹2,40,000 |
| **API & Ingestion Cluster** | Kubernetes (EKS/GKE): 12x c6g.2xlarge worker nodes (Autoscaling) | $18,200 / ₹15,10,000 |
| **Object Storage & CDN** | 10TB S3 storage + 50TB CloudFront CDN egress | $3,600 / ₹3,00,000 |
| **KMS & Security** | AWS KMS key usage + Cloudflare Enterprise DDoS & WAF | $4,800 / ₹4,00,000 |
| **Total Estimated Annual Cost** | **Production High-Availability Scale (15,000 Institutions)** | **~$43,880 / ~₹36,50,000** |
