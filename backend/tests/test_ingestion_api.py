"""Integration tests for Ingestion Endpoints (Single Enrol, Bulk Batches, Programs, and ERP HMAC API)."""

import io
import time
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

import unittest.mock
from datetime import date
from typing import Optional, List, Dict, Any

from app.api.deps import get_db
from app.core.crypto import encrypt_field
from app.core.hmac_auth import compute_hmac_signature
from app.core.jwt import create_access_token
from app.integrations.apaar.base import ApaarProvider, ApaarVerificationResult
import app.integrations.apaar as apaar_pkg
from app.main import app
from app.models.base import Base
from app.models.state import State
from app.models.institution import Institution
from app.models.rbac import ApiClient, Permission, Role, RolePermission, User, UserInstitution, UserRole
from app.models.program import Program


class FastTestApaarProvider(ApaarProvider):
    async def verify(self, apaar_id: str, name: Optional[str] = None, dob: Optional[date] = None) -> ApaarVerificationResult:
        return ApaarVerificationResult(
            apaar_id=apaar_id,
            is_valid=True,
            status="ACTIVE",
            found=True,
            name_match_score=100.0,
            dob_match=True,
            last_known_institution="Delhi Institute of Technology",
        )

    async def verify_batch(self, items: List[Dict[str, Any]]) -> Dict[str, ApaarVerificationResult]:
        return {
            item["apaar_id"]: ApaarVerificationResult(
                apaar_id=item["apaar_id"],
                is_valid=True,
                status="ACTIVE",
                found=True,
                name_match_score=100.0,
                dob_match=True,
                last_known_institution="Delhi Institute of Technology",
            )
            for item in items
        }


@pytest.fixture
async def ingestion_test_env():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as session:
        # Create State & Institution
        st = State(id=uuid.uuid4(), code="DL", name="Delhi")
        session.add(st)
        await session.flush()

        inst = Institution(
            id=uuid.uuid4(),
            aicte_id="1-TEST-001",
            name="Delhi Institute of Technology",
            state_id=st.id,
            district="New Delhi",
            institution_type="UNIVERSITY",
            status="ACTIVE",
            email="admin@dit.ac.in",
            approved_total_intake=300,
        )
        session.add(inst)
        await session.flush()

        # Roles and Permissions
        perm_read = Permission(id=uuid.uuid4(), code="students:read")
        perm_write = Permission(id=uuid.uuid4(), code="students:write")
        perm_batch = Permission(id=uuid.uuid4(), code="batches:read")
        perm_upload = Permission(id=uuid.uuid4(), code="batches:upload")
        role_admin = Role(id=uuid.uuid4(), name="INSTITUTION_ADMIN")
        session.add_all([perm_read, perm_write, perm_batch, perm_upload, role_admin])
        await session.flush()

        session.add_all([
            RolePermission(role_id=role_admin.id, permission_id=perm_read.id),
            RolePermission(role_id=role_admin.id, permission_id=perm_write.id),
            RolePermission(role_id=role_admin.id, permission_id=perm_batch.id),
            RolePermission(role_id=role_admin.id, permission_id=perm_upload.id),
        ])

        # User
        user = User(
            id=uuid.uuid4(),
            email="admin@dit.ac.in",
            password_hash="hashed_dummy",
            full_name="Dr. Registrar",
            is_active=True,
            is_verified=True,
        )
        session.add(user)
        await session.flush()
        session.add(UserRole(user_id=user.id, role_id=role_admin.id))
        session.add(UserInstitution(user_id=user.id, institution_id=inst.id))

        # HMAC API Client
        api_secret = "TestHmacSecret2026!HighEntropyKey"
        api_client = ApiClient(
            id=uuid.uuid4(),
            key_id="erp-client-test-01",
            secret_hash=encrypt_field(api_secret),
            institution_id=inst.id,
            scopes=["students:write", "batches:read", "batches:upload"],
            active=True,
        )
        session.add(api_client)
        await session.commit()

        token = create_access_token(
            user_id=user.id,
            roles=["INSTITUTION_ADMIN"],
            institution_ids=[str(inst.id)],
            permissions=["students:read", "students:write", "batches:read", "batches:upload"],
        )

        orig_provider = apaar_pkg._provider_instance
        apaar_pkg._provider_instance = FastTestApaarProvider()
        try:
            yield {
                "session": session,
                "engine": engine,
                "institution": inst,
                "user": user,
                "token": token,
                "api_client": api_client,
                "api_secret": api_secret,
                "AsyncSessionLocal": AsyncSessionLocal,
            }
        finally:
            apaar_pkg._provider_instance = orig_provider

    await engine.dispose()


@pytest.mark.asyncio
async def test_single_student_enrol_and_history(ingestion_test_env):
    """POST /students/enrol registers full 21 fields, checks APAAR, encrypts PII, and logs history."""
    env = ingestion_test_env
    app.dependency_overrides[get_db] = lambda: env["AsyncSessionLocal"]()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"Authorization": f"Bearer {env['token']}"}
        payload = {
            "apaar_id": "200000000010",
            "student_ref_id": "DIT/2025/CS/001",
            "name": "Manish Sharma",
            "dob": "2004-06-12",
            "gender": "MALE",
            "parent_name": "Rakesh Sharma",
            "contact": {"email": "manish@example.com", "phone": "9876543210"},
            "program_name": "Computer Science and Engineering",
            "branch": "CSE",
            "academic_year": "2025-26",
            "admission_category": "GEN",
            "quota_type": "REGULAR",
            "is_nri": False,
            "oci_status": False,
            "is_foreign_national": False,
            "nationality": "INDIAN",
            "admission_date": "2025-08-01",
            "status": "ACTIVE",
        }

        resp = await ac.post("/api/v1/students/enrol", json=payload, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["masked_apaar_id"] == "XXXXXXXX0010"
        assert "student_id" in data
        assert "enrolment_id" in data
        assert data["status"] == "ACTIVE"

        student_id = data["student_id"]

        # Duplicate enrolment for same student, program, and year is rejected
        dup_resp = await ac.post("/api/v1/students/enrol", json=payload, headers=headers)
        assert dup_resp.status_code in (400, 422)
        assert "already enrolled" in str(dup_resp.json()).lower()

        # Update enrolment attributes with diff history tracking
        update_payload = {
            "name": "Manish R Sharma",
            "admission_category": "OBC",
        }
        update_resp = await ac.put(f"/api/v1/students/{student_id}/enrolment", json=update_payload, headers=headers)
        assert update_resp.status_code == 200
        up_data = update_resp.json()
        assert up_data["name"] == "Manish R Sharma"
        assert up_data["diff"]["name"]["new"] == "[PROTECTED]"
        assert up_data["diff"]["admission_category"]["new"] == "OBC"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_check_apaar_pre_check_endpoint(ingestion_test_env):
    """POST /students/check-apaar verifies format and registry status on-the-fly."""
    env = ingestion_test_env
    app.dependency_overrides[get_db] = lambda: env["AsyncSessionLocal"]()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"Authorization": f"Bearer {env['token']}"}

        # Valid 12 digits
        resp = await ac.post(
            "/api/v1/students/check-apaar",
            json={"apaar_id": "200000000010", "name": "Test Student"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid_format"] is True

        # Invalid format (< 12 digits)
        resp_inv = await ac.post(
            "/api/v1/students/check-apaar",
            json={"apaar_id": "12345"},
            headers=headers,
        )
        assert resp_inv.status_code == 200
        inv_data = resp_inv.json()
        assert inv_data["valid_format"] is False
        assert inv_data["status"] == "INVALID"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_program_intake_declaration_and_summary(ingestion_test_env):
    """POST /programs/intake-declaration and GET /programs/intake-summary calculate utilization."""
    env = ingestion_test_env
    app.dependency_overrides[get_db] = lambda: env["AsyncSessionLocal"]()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"Authorization": f"Bearer {env['token']}"}

        # 1. Declare intake
        declare_payload = {
            "program_name": "Mechanical Engineering",
            "level": "UG",
            "branch": "ME",
            "academic_year": "2025-26",
            "approved_intake": 120,
            "supernumerary_seats": 18,
            "supernumerary_cap_pct": 15.0,
            "declared_enrolment": 115,
        }
        res = await ac.post("/api/v1/programs/intake-declaration", json=declare_payload, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["approved_intake"] == 120
        assert data["supernumerary_seats"] == 18
        assert data["capacity_status"] in ("WITHIN_CAPACITY", "WARNING_NEAR_CAPACITY")

        # 2. Get intake summary
        summary_res = await ac.get("/api/v1/programs/intake-summary?academic_year=2025-26", headers=headers)
        assert summary_res.status_code == 200
        items = summary_res.json()
        assert len(items) >= 1
        assert any(p["branch"] == "ME" for p in items)

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_bulk_batch_upload_flow(ingestion_test_env):
    """POST /batches uploads file, performs duplicate check, and provides telemetry."""
    env = ingestion_test_env
    app.dependency_overrides[get_db] = lambda: env["AsyncSessionLocal"]()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"Authorization": f"Bearer {env['token']}"}

        # Prepare test CSV
        csv_data = (
            "apaar_id,student_ref_id,name,dob,gender,program_name,branch,academic_year\n"
            "200000000010,REF-101,Aakash Roy,2003-04-10,MALE,Electrical Eng,EE,2025-26\n"
            "200000000020,REF-102,Sneha Das,2004-09-18,FEMALE,Electrical Eng,EE,2025-26\n"
        ).encode("utf-8")

        files = {"file": ("students_test.csv", io.BytesIO(csv_data), "text/csv")}
        form_data = {"academic_year": "2025-26"}

        with unittest.mock.patch("app.api.routers.v1.batches.process_bulk_student_upload.delay"):
            upload_res = await ac.post("/api/v1/batches", data=form_data, files=files, headers=headers)
            assert upload_res.status_code == 202
            batch_info = upload_res.json()
            batch_id = batch_info["batch_id"]
            assert batch_info["status"] in ("PENDING", "PROCESSING", "COMPLETED")

            # Re-upload identical file triggers duplicate warning
            files_dup = {"file": ("students_test.csv", io.BytesIO(csv_data), "text/csv")}
            dup_res = await ac.post("/api/v1/batches", data=form_data, files=files_dup, headers=headers)
            assert dup_res.status_code == 202
            assert dup_res.json().get("warning") is not None
            assert "duplicate" in dup_res.json()["warning"].lower()
            assert "identical" in dup_res.json()["warning"].lower()

        # List batches
        list_res = await ac.get("/api/v1/batches", headers=headers)
        assert list_res.status_code == 200
        batches = list_res.json()
        assert any(b["id"] == batch_id for b in batches)

        # Get batch status
        detail_res = await ac.get(f"/api/v1/batches/{batch_id}", headers=headers)
        assert detail_res.status_code == 200
        assert detail_res.json()["id"] == batch_id

        # Get error report (JSON and CSV)
        errors_json = await ac.get(f"/api/v1/batches/{batch_id}/errors?format=json", headers=headers)
        assert errors_json.status_code == 200
        errors_csv = await ac.get(f"/api/v1/batches/{batch_id}/errors?format=csv", headers=headers)
        assert errors_csv.status_code == 200

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_integration_hmac_erp_api(ingestion_test_env):
    """POST /integration/students allows institutional ERPs to submit student records via HMAC."""
    env = ingestion_test_env
    app.dependency_overrides[get_db] = lambda: env["AsyncSessionLocal"]()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        records = [
            {
                "apaar_id": "200000000030",
                "student_ref_id": "ERP/2025/001",
                "name": "Kunal Sen",
                "dob": "2003-03-21",
                "gender": "MALE",
                "program_name": "Information Technology",
                "branch": "IT",
                "academic_year": "2025-26",
            },
            {
                "apaar_id": "200000000040",
                "student_ref_id": "ERP/2025/002",
                "name": "Meera Joshi",
                "dob": "2004-10-11",
                "gender": "FEMALE",
                "program_name": "Information Technology",
                "branch": "IT",
                "academic_year": "2025-26",
            },
        ]
        body_bytes = io.BytesIO()
        import json
        body_raw = json.dumps(records).encode("utf-8")

        # Generate HMAC Headers
        key_id = env["api_client"].key_id
        secret = env["api_secret"]
        timestamp = str(time.time())
        nonce = str(uuid.uuid4())
        method = "POST"
        path = "/api/v1/integration/students"

        sig = compute_hmac_signature(
            secret=secret,
            method=method,
            path=path,
            timestamp=timestamp,
            nonce=nonce,
            body=body_raw,
        )

        headers = {
            "Content-Type": "application/json",
            "X-Key-Id": key_id,
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "X-Signature": sig,
        }

        resp = await ac.post(path, content=body_raw, headers=headers)
        assert resp.status_code in (200, 202)
        data = resp.json()
        assert "batch_id" in data
        assert data["total_records"] == 2
        batch_id = data["batch_id"]

        # Status check via HMAC
        get_path = f"/api/v1/integration/batches/{batch_id}"
        get_ts = str(time.time())
        get_nonce = str(uuid.uuid4())
        get_sig = compute_hmac_signature(secret, "GET", get_path, get_ts, get_nonce, b"")

        get_headers = {
            "X-Key-Id": key_id,
            "X-Timestamp": get_ts,
            "X-Nonce": get_nonce,
            "X-Signature": get_sig,
        }
        status_resp = await ac.get(get_path, headers=get_headers)
        assert status_resp.status_code == 200
        assert status_resp.json()["id"] == batch_id

    app.dependency_overrides.clear()
