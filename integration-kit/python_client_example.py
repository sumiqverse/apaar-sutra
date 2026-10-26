#!/usr/bin/env python3
"""
APAAR-Sutra Python Integration Client Example
Demonstrates HMAC-SHA256 authenticated batch ingestion, status polling, and report hash verification.
"""

from datetime import datetime, timezone
import hashlib
import hmac
import json
import time
from typing import Any, Dict, List, Optional
import urllib.parse
import urllib.request
import uuid


class ApaarSutraClient:
    """Production-ready client wrapper for APAAR-Sutra System-to-System APIs."""

    def __init__(self, base_url: str, client_id: str, client_secret: str):
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret

    def _sign_request(
        self, method: str, path: str, body_bytes: bytes = b""
    ) -> Dict[str, str]:
        """Calculates RFC 8785 canonical hash and HMAC-SHA256 signature headers."""
        timestamp = str(int(time.time()))
        nonce = f"n_{uuid.uuid4().hex[:16]}"
        body_hash = hashlib.sha256(body_bytes).hexdigest()

        # Canonical string: METHOD\nPATH\nTIMESTAMP\nNONCE\nBODY_HASH
        canonical = f"{method.upper()}\n{path}\n{timestamp}\n{nonce}\n{body_hash}"
        signature = hmac.new(
            self.client_secret.encode("utf-8"),
            canonical.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return {
            "X-Client-ID": self.client_id,
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "X-Signature": signature,
        }

    def _request(
        self,
        method: str,
        path: str,
        payload: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Performs signed HTTP request."""
        url = f"{self.base_url}{path}"
        body_bytes = b""
        req_headers = {"Accept": "application/json"}

        if payload is not None:
            # Canonical JSON serialization: sorted keys, compact separators
            body_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            req_headers["Content-Type"] = "application/json"

        # Add HMAC auth headers
        auth_headers = self._sign_request(method, path, body_bytes)
        req_headers.update(auth_headers)

        if headers:
            req_headers.update(headers)

        req = urllib.request.Request(url, data=body_bytes if body_bytes else None, headers=req_headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                data = resp.read().decode("utf-8")
                return json.loads(data) if data else {}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            raise RuntimeError(f"HTTP {e.code}: {err_body}")

    def push_students_batch(
        self, students: List[Dict[str, Any]], idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Ingests a batch of student enrolment records into APAAR-Sutra."""
        path = "/api/v1/integration/students"
        headers = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        else:
            headers["Idempotency-Key"] = f"idemp_{uuid.uuid4().hex}"

        return self._request("POST", path, payload=students, headers=headers)

    def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """Checks the processing status and counts of an ingested batch."""
        path = f"/api/v1/integration/batches/{batch_id}"
        return self._request("GET", path)

    def verify_report(self, report_hash: str) -> Dict[str, Any]:
        """Verifies statutory report provenance and authenticity via SHA-256 hash."""
        path = f"/api/v1/reports/verify?hash={urllib.parse.quote(report_hash)}"
        return self._request("GET", path)


# --- Example Usage ---
if __name__ == "__main__":
    BASE_URL = "http://localhost:8000"
    CLIENT_ID = "erp_demo_client_001"
    CLIENT_SECRET = "sec_demo_secret_key_sutrapass_2026"

    client = ApaarSutraClient(BASE_URL, CLIENT_ID, CLIENT_SECRET)

    # 1. Sample student record
    sample_students = [
        {
            "student_ref_id": f"ERP-{int(time.time())}-01",
            "apaar_id": "987654321012",
            "name": "Ishaani Sen",
            "dob": "2004-11-03",
            "gender": "FEMALE",
            "parent_name": "Alok Sen",
            "contact": {"email": "ishaani.sen@example.ac.in", "phone": "9876543299"},
            "program_name": "B.Tech Computer Science & Engineering",
            "branch": "CSE",
            "academic_year": "2025-26",
            "admission_category": "GEN",
            "quota_type": "REGULAR",
            "is_nri": False,
            "admission_date": "2025-07-20",
            "status": "ACTIVE",
        }
    ]

    print("[1] Pushing student batch with HMAC signature...")
    try:
        res = client.push_students_batch(sample_students)
        print(f"Batch Response: status={res.get('status')}, batch_id={res.get('batch_id')}")

        batch_id = res.get("batch_id")
        if batch_id:
            print("[2] Polling batch status...")
            status_res = client.get_batch_status(batch_id)
            print(f"Batch Status: {status_res}")
    except Exception as exc:
        print(f"Client call demo error (ensure server is running): {exc}")
