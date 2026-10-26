"""Tests for Mock APAAR Verification Gateway service."""

import os
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from mock_apaar.server import app, REGISTRY as APAAR_REGISTRY, API_KEY_ENV as API_KEY


@pytest.fixture
def mock_client():
    return TestClient(app)


def test_mock_apaar_health(mock_client):
    """Liveness probe test for mock server."""
    resp = mock_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "HEALTHY"


def test_mock_apaar_unauthorized(mock_client):
    """Missing or invalid API key returns 401."""
    resp = mock_client.post("/apaar/verify", json={"apaar_id": "200000000010"})
    assert resp.status_code == 401

    resp = mock_client.post(
        "/apaar/verify",
        json={"apaar_id": "200000000010"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert resp.status_code == 401


def test_mock_apaar_verify_found_active(mock_client):
    """Verify an active student with fuzzy name matching and DOB verification."""
    # Ensure test entry in registry
    test_id = "999999999999"
    APAAR_REGISTRY[test_id] = {
        "status": "ACTIVE",
        "name": "Aarav Sharma",
        "dob": "2003-05-15",
        "gender": "MALE",
        "last_known_institution": "IIT Delhi",
    }

    headers = {"X-API-Key": API_KEY}
    resp = mock_client.post(
        "/apaar/verify",
        json={
            "apaar_id": test_id,
            "name": "Aarav Sharma",
            "dob": "2003-05-15",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["found"] is True
    assert data["status"] == "ACTIVE"
    assert data["name_match_score"] == 100
    assert data["dob_match"] is True
    assert data["last_known_institution"] == "IIT Delhi"


def test_mock_apaar_verify_fuzzy_name(mock_client):
    """Fuzzy name matching calculates correct similarity score."""
    test_id = "888888888888"
    APAAR_REGISTRY[test_id] = {
        "status": "ACTIVE",
        "name": "Priya Rajesh Patel",
        "dob": "2004-11-20",
        "gender": "FEMALE",
        "last_known_institution": "NIT Surat",
    }

    headers = {"X-API-Key": API_KEY}
    # Slight typo in input name
    resp = mock_client.post(
        "/apaar/verify",
        json={
            "apaar_id": test_id,
            "name": "Priya R Patel",
            "dob": "2004-11-20",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["found"] is True
    assert data["name_match_score"] >= 75
    assert data["dob_match"] is True


def test_mock_apaar_verify_not_found(mock_client):
    """Non-existent APAAR ID returns NOT_FOUND status."""
    headers = {"X-API-Key": API_KEY}
    resp = mock_client.post(
        "/apaar/verify",
        json={"apaar_id": "000000000000"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["found"] is False
    assert data["status"] == "NOT_FOUND"
    assert data["name_match_score"] == 0
    assert data["dob_match"] is False


def test_mock_apaar_verify_batch(mock_client):
    """Batch verification handles up to 500 IDs."""
    test_id_1 = "777777777771"
    test_id_2 = "777777777772"
    APAAR_REGISTRY[test_id_1] = {"status": "ACTIVE", "name": "Rohit Verma"}
    APAAR_REGISTRY[test_id_2] = {"status": "INACTIVE", "name": "Suresh Gupta"}

    headers = {"X-API-Key": API_KEY}
    items = [
        {"apaar_id": test_id_1, "name": "Rohit Verma"},
        {"apaar_id": test_id_2, "name": "Suresh Gupta"},
        {"apaar_id": "000000000099"},
    ]
    resp = mock_client.post(
        "/apaar/verify-batch",
        json={"items": items},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    results = data["results"]
    assert len(results) == 3
    assert results[test_id_1]["status"] == "ACTIVE"
    assert results[test_id_2]["status"] == "INACTIVE"
    assert results["000000000099"]["status"] == "NOT_FOUND"


def test_mock_apaar_batch_limit_exceeded(mock_client):
    """Batch size > 500 is rejected."""
    headers = {"X-API-Key": API_KEY}
    items = [{"apaar_id": f"{i:012d}"} for i in range(501)]
    resp = mock_client.post(
        "/apaar/verify-batch",
        json={"items": items},
        headers=headers,
    )
    assert resp.status_code in (400, 422)
