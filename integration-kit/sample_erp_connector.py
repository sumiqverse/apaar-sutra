#!/usr/bin/env python3
"""
APAAR-Sutra Sample ERP Connector
Synchronizes student enrolment records from a college ERP / SIS (SQLite database)
to the central APAAR-Sutra platform with delta-sync and retry resilience.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional
import urllib.parse
import urllib.request
import uuid

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mock_erp.db")


def init_mock_erp_db(db_path: str = DB_PATH) -> None:
    """Initializes the mock college ERP SQLite database with schema and sample records."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS erp_students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT UNIQUE NOT NULL,
        apaar_id TEXT NOT NULL,
        full_name TEXT NOT NULL,
        dob TEXT NOT NULL,
        gender TEXT NOT NULL,
        parent_name TEXT,
        email TEXT,
        phone TEXT,
        program TEXT NOT NULL,
        branch TEXT NOT NULL,
        academic_year TEXT NOT NULL,
        category TEXT NOT NULL,
        quota TEXT NOT NULL,
        is_nri INTEGER DEFAULT 0,
        admission_date TEXT NOT NULL,
        status TEXT NOT NULL,
        sync_status TEXT DEFAULT 'PENDING',
        last_synced_at TEXT,
        updated_at TEXT NOT NULL
    )
    """)

    # Check if empty, insert 10 sample students if so
    cursor.execute("SELECT COUNT(*) FROM erp_students")
    if cursor.fetchone()[0] == 0:
        now_str = datetime.now(timezone.utc).isoformat()
        sample_records = [
            ("ERP-2025-001", "123456789012", "Aarav Sharma", "2004-05-14", "MALE", "Rajesh Sharma", "aarav@example.edu", "9876543210", "B.Tech Computer Science", "CSE", "2025-26", "GEN", "REGULAR", 0, "2025-07-15", "ACTIVE", "PENDING", None, now_str),
            ("ERP-2025-002", "234567890123", "Ananya Patel", "2004-09-21", "FEMALE", "Mukesh Patel", "ananya@example.edu", "9876543211", "B.Tech Information Technology", "IT", "2025-26", "OBC", "REGULAR", 0, "2025-07-16", "ACTIVE", "PENDING", None, now_str),
            ("ERP-2025-003", "345678901234", "Rohan Verma", "2003-12-05", "MALE", "Sunil Verma", "rohan@example.edu", "9876543212", "B.Tech Electrical Engineering", "EE", "2025-26", "SC", "REGULAR", 0, "2025-07-16", "ACTIVE", "PENDING", None, now_str),
            ("ERP-2025-004", "456789012345", "Sneha Rao", "2004-02-18", "FEMALE", "Venkatesh Rao", "sneha@example.edu", "9876543213", "B.Tech Electronics & Comm", "ECE", "2025-26", "GEN", "EWS", 0, "2025-07-17", "ACTIVE", "PENDING", None, now_str),
            ("ERP-2025-005", "567890123456", "Vikram Singh", "2004-08-30", "MALE", "Harjit Singh", "vikram@example.edu", "9876543214", "B.Tech Mechanical Engineering", "MECH", "2025-26", "GEN", "MANAGEMENT", 0, "2025-07-18", "ACTIVE", "PENDING", None, now_str),
            ("ERP-2025-006", "678901234567", "Priya Nair", "2004-04-11", "FEMALE", "Suresh Nair", "priya@example.edu", "9876543215", "B.Tech Civil Engineering", "CIVIL", "2025-26", "GEN", "TFW", 0, "2025-07-19", "ACTIVE", "PENDING", None, now_str),
            ("ERP-2025-007", "789012345678", "Zaid Khan", "2004-11-25", "MALE", "Tariq Khan", "zaid@example.edu", "9876543216", "B.Tech Artificial Intelligence", "AI_DS", "2025-26", "GEN", "REGULAR", 0, "2025-07-20", "ACTIVE", "PENDING", None, now_str),
            ("ERP-2025-008", "890123456789", "Divya Menon", "2004-06-08", "FEMALE", "Ramesh Menon", "divya@example.edu", "9876543217", "B.Tech Computer Science", "CSE", "2025-26", "ST", "REGULAR", 0, "2025-07-21", "ACTIVE", "PENDING", None, now_str),
            ("ERP-2025-009", "901234567890", "Kevin Mathew", "2003-10-14", "MALE", "Thomas Mathew", "kevin@example.edu", "9876543218", "B.Tech Data Science", "AI_DS", "2025-26", "GEN", "NRI", 1, "2025-07-22", "ACTIVE", "PENDING", None, now_str),
            ("ERP-2025-010", "112233445566", "Neha Gupta", "2004-01-29", "FEMALE", "Anil Gupta", "neha@example.edu", "9876543219", "B.Tech Computer Science", "CSE", "2025-26", "GEN", "PMSSS", 0, "2025-07-23", "ACTIVE", "PENDING", None, now_str),
        ]
        cursor.executemany("""
        INSERT INTO erp_students (
            student_id, apaar_id, full_name, dob, gender, parent_name, email, phone,
            program, branch, academic_year, category, quota, is_nri, admission_date, status,
            sync_status, last_synced_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_records)
        conn.commit()
    conn.close()


class ERPConnector:
    """Connects to local ERP SQLite database and pushes records to APAAR-Sutra."""

    def __init__(self, api_url: str, client_id: str, client_secret: str, db_path: str = DB_PATH):
        self.api_url = api_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.db_path = db_path
        init_mock_erp_db(self.db_path)

    def _sign_request(self, method: str, path: str, body_bytes: bytes) -> Dict[str, str]:
        timestamp = str(int(time.time()))
        nonce = f"n_{uuid.uuid4().hex[:16]}"
        body_hash = hashlib.sha256(body_bytes).hexdigest()
        canonical = f"{method.upper()}\n{path}\n{timestamp}\n{nonce}\n{body_hash}"
        signature = hmac.new(self.client_secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()
        return {
            "X-Client-ID": self.client_id,
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "X-Signature": signature,
        }

    def _post_with_retry(self, path: str, payload: List[Dict[str, Any]], max_retries: int = 3) -> Dict[str, Any]:
        url = f"{self.api_url}{path}"
        body_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        auth_headers = self._sign_request("POST", path, body_bytes)

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Idempotency-Key": f"sync_{int(time.time())}_{uuid.uuid4().hex[:8]}",
            **auth_headers,
        }

        delay = 1.0
        for attempt in range(1, max_retries + 1):
            try:
                req = urllib.request.Request(url, data=body_bytes, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=15) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as he:
                err_text = he.read().decode("utf-8")
                # 4xx client errors except 429 should not be retried blindly
                if 400 <= he.code < 500 and he.code != 429:
                    raise RuntimeError(f"HTTP {he.code} client error: {err_text}")
                print(f"[Attempt {attempt}/{max_retries}] HTTP {he.code} error: {err_text}. Retrying in {delay}s...")
            except Exception as e:
                print(f"[Attempt {attempt}/{max_retries}] Network exception: {e}. Retrying in {delay}s...")

            time.sleep(delay)
            delay *= 2.0

        raise RuntimeError(f"Failed to push batch after {max_retries} attempts.")

    def run_sync(self, delta_mode: bool = True, batch_size: int = 50) -> Dict[str, Any]:
        """Extracts students from ERP DB and synchronizes with APAAR-Sutra."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if delta_mode:
            print("[ERP Connector] Running in DELTA-SYNC mode (pending or modified records only)...")
            cursor.execute("""
                SELECT * FROM erp_students 
                WHERE sync_status != 'SYNCED' OR (last_synced_at IS NOT NULL AND updated_at > last_synced_at)
                LIMIT ?
            """, (batch_size,))
        else:
            print("[ERP Connector] Running in FULL-SYNC mode (all records)...")
            cursor.execute("SELECT * FROM erp_students LIMIT ?", (batch_size,))

        rows = cursor.fetchall()
        if not rows:
            print("[ERP Connector] No records requiring synchronization.")
            conn.close()
            return {"status": "NO_CHANGES", "records_synced": 0}

        print(f"[ERP Connector] Extracted {len(rows)} records from ERP database.")

        records_payload = []
        erp_ids = []
        for r in rows:
            erp_ids.append(r["id"])
            records_payload.append({
                "student_ref_id": r["student_id"],
                "apaar_id": r["apaar_id"],
                "name": r["full_name"],
                "dob": r["dob"],
                "gender": r["gender"],
                "parent_name": r["parent_name"],
                "contact": {"email": r["email"], "phone": r["phone"]},
                "program_name": r["program"],
                "branch": r["branch"],
                "academic_year": r["academic_year"],
                "admission_category": r["category"],
                "quota_type": r["quota"],
                "is_nri": bool(r["is_nri"]),
                "admission_date": r["admission_date"],
                "status": r["status"],
            })

        try:
            res = self._post_with_retry("/api/v1/integration/students", records_payload)
            now_iso = datetime.now(timezone.utc).isoformat()
            # Update sync status in ERP
            cursor.executemany(
                "UPDATE erp_students SET sync_status = 'SYNCED', last_synced_at = ? WHERE id = ?",
                [(now_iso, eid) for eid in erp_ids],
            )
            conn.commit()
            print(f"[ERP Connector] Sync successful! Batch ID: {res.get('batch_id')}, Accepted: {res.get('accepted')}, Rejected: {res.get('rejected')}")
            return res
        except Exception as err:
            cursor.executemany(
                "UPDATE erp_students SET sync_status = 'FAILED' WHERE id = ?",
                [(eid,) for eid in erp_ids],
            )
            conn.commit()
            print(f"[ERP Connector] Sync failed: {err}")
            raise
        finally:
            conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="APAAR-Sutra ERP Connector")
    parser.add_argument("--mode", choices=["delta", "full"], default="delta", help="Sync mode: delta (default) or full")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of APAAR-Sutra API")
    parser.add_argument("--client-id", default="erp_demo_client_001", help="API Client ID")
    parser.add_argument("--secret", default="sec_demo_secret_key_sutrapass_2026", help="Client HMAC Secret")
    args = parser.parse_args()

    connector = ERPConnector(args.url, args.client_id, args.secret)
    try:
        connector.run_sync(delta_mode=(args.mode == "delta"))
    except Exception as exc:
        print(f"Connector completed with info: {exc}")
