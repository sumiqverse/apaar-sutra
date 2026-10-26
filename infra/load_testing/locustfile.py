"""
APAAR-Sutra High-Concurrency Load Testing Suite (Locust).
Simulates 500 concurrent users across realistic production traffic profiles:
- 60% Dashboard & Analytics Readers (AICTE & Institution dashboards)
- 25% Third-Party & Public Verifiers (APAAR ID verification with consent tokens)
- 15% Institutional ERP Ingestion (HMAC-signed batch push)
"""

from datetime import datetime, timezone
import hashlib
import hmac
import json
import random
import time
import uuid
from locust import HttpUser, between, task


class DashboardReaderUser(HttpUser):
    """Simulates AICTE regulators and college registrars browsing analytics and reports."""
    weight = 60
    wait_time = between(1.0, 3.0)

    def on_start(self):
        self.auth_headers = {
            "Authorization": "Bearer mock_super_admin_token",
            "Accept": "application/json",
        }

    @task(3)
    def view_analytics_overview(self):
        """Read overall AICTE national KPI metrics."""
        self.client.get("/api/v1/analytics/overview?academic_year=2025-26", headers=self.auth_headers)

    @task(2)
    def view_state_breakdown(self):
        """Read state-wise enrollment and sanctioned intake distribution."""
        self.client.get("/api/v1/analytics/state-breakdown?academic_year=2025-26", headers=self.auth_headers)

    @task(2)
    def view_reports_catalog(self):
        """Inspect available statutory reports."""
        self.client.get("/api/v1/reports/catalog", headers=self.auth_headers)

    @task(1)
    def view_reports_history(self):
        """Check audit history of generated reports."""
        self.client.get("/api/v1/reports/history", headers=self.auth_headers)


class VerifierUser(HttpUser):
    """Simulates employers and universities verifying credentials via APAAR IDs."""
    weight = 25
    wait_time = between(0.5, 2.0)

    @task(3)
    def verify_report_hash(self):
        """Cryptographic provenance verification of statutory report SHA-256 hash."""
        sample_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        self.client.get(f"/api/v1/reports/verify?hash={sample_hash}")

    @task(2)
    def fetch_public_jwks(self):
        """Fetch well-known Ed25519 public verification keys."""
        self.client.get("/.well-known/apaar-sutra-keys.json")

    @task(1)
    def health_check(self):
        """Verify API availability probe."""
        self.client.get("/api/v1/health")


class BatchUploaderUser(HttpUser):
    """Simulates institutional ERP systems ingesting student batches with HMAC signatures."""
    weight = 15
    wait_time = between(2.0, 5.0)

    def on_start(self):
        self.client_id = "erp_demo_client_001"
        self.client_secret = "sec_demo_secret_key_sutrapass_2026"

    @task(1)
    def push_student_batch(self):
        """Submits signed batch of student enrolment records."""
        path = "/api/v1/integration/students"
        records = [
            {
                "student_ref_id": f"LOCUST-{uuid.uuid4().hex[:8]}",
                "apaar_id": f"9876{random.randint(10000000, 99999999)}",
                "name": f"Student {random.randint(100, 999)}",
                "dob": "2004-06-15",
                "gender": "FEMALE",
                "program_name": "B.Tech Computer Science",
                "branch": "CSE",
                "academic_year": "2025-26",
                "admission_category": "GEN",
                "quota_type": "REGULAR",
                "is_nri": False,
                "admission_date": "2025-07-15",
                "status": "ACTIVE",
            }
            for _ in range(5)
        ]

        body_bytes = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
        timestamp = str(int(time.time()))
        nonce = f"n_{uuid.uuid4().hex[:16]}"
        body_hash = hashlib.sha256(body_bytes).hexdigest()
        canonical = f"POST\n{path}\n{timestamp}\n{nonce}\n{body_hash}"
        signature = hmac.new(self.client_secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-Client-ID": self.client_id,
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "X-Signature": signature,
            "Idempotency-Key": f"idemp_{uuid.uuid4().hex}",
        }

        self.client.post(path, data=body_bytes, headers=headers)
