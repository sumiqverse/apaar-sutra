"""Pytest configuration and test client fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Synchronous test client fixture for FastAPI app."""
    return TestClient(app)
