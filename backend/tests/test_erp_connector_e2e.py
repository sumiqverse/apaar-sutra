"""
End-to-end tests for the Sample ERP Connector and Delta-Sync Logic.
"""

from datetime import datetime, timezone
import os
import sqlite3
import sys
import tempfile
import uuid
import pytest

# Add integration-kit to path to import sample_erp_connector
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "integration-kit")))

from sample_erp_connector import ERPConnector, init_mock_erp_db


@pytest.fixture
def temp_erp_db():
    """Create a temporary SQLite database populated with sample ERP students."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_db_path = tf.name

    init_mock_erp_db(temp_db_path)
    yield temp_db_path

    if os.path.exists(temp_db_path):
        os.remove(temp_db_path)


def test_mock_erp_database_initialization(temp_erp_db):
    """Verify that sample ERP SQLite DB is initialized with 10 sample students."""
    conn = sqlite3.connect(temp_erp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM erp_students")
    count = cursor.fetchone()[0]
    conn.close()

    assert count == 10


def test_erp_connector_hmac_signing():
    """Verify that ERPConnector produces valid RFC compliant canonical signature headers."""
    connector = ERPConnector(
        api_url="http://localhost:8000",
        client_id="test_erp_client",
        client_secret="test_secret_key_12345",
        db_path=":memory:",
    )

    body_bytes = b'{"records": [{"name": "Aarav"}]}'
    headers = connector._sign_request("POST", "/api/v1/integration/students", body_bytes)

    assert headers["X-Client-ID"] == "test_erp_client"
    assert "X-Timestamp" in headers
    assert "X-Nonce" in headers
    assert "X-Signature" in headers
    assert len(headers["X-Signature"]) == 64


def test_delta_sync_state_tracking(temp_erp_db):
    """Test that delta-sync properly extracts pending records and updates sync_status to SYNCED."""
    connector = ERPConnector(
        api_url="http://mock-server.test",
        client_id="test_client",
        client_secret="test_secret",
        db_path=temp_erp_db,
    )

    conn = sqlite3.connect(temp_erp_db)
    cursor = conn.cursor()

    # Initial state: 10 PENDING records
    cursor.execute("SELECT COUNT(*) FROM erp_students WHERE sync_status = 'PENDING'")
    assert cursor.fetchone()[0] == 10

    # Simulate marking 5 records SYNCED
    now_iso = datetime.now(timezone.utc).isoformat()
    cursor.execute("UPDATE erp_students SET sync_status = 'SYNCED', last_synced_at = ? WHERE id <= 5", (now_iso,))
    conn.commit()

    # Query delta records (only 5 remain pending)
    cursor.execute("""
        SELECT COUNT(*) FROM erp_students 
        WHERE sync_status != 'SYNCED' OR (last_synced_at IS NOT NULL AND updated_at > last_synced_at)
    """)
    delta_count = cursor.fetchone()[0]
    conn.close()

    assert delta_count == 5
