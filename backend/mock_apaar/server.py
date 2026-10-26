"""Standalone and mountable mock server mimicking the National APAAR Registry Gateway."""

from typing import Any, Dict
from fastapi import FastAPI, HTTPException, status

from app.validation.apaar_rules import validate_apaar_id

mock_apaar_app = FastAPI(
    title="Mock National APAAR Gateway",
    version="1.0.0",
    docs_url="/docs",
)

# Simulated national registry database
MOCK_NATIONAL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "987654321012": {
        "apaar_id": "987654321012",
        "first_name": "Aarav",
        "last_name": "Sharma",
        "dob": "2003-05-15",
        "gender": "MALE",
        "abc_account_active": True,
        "registry_status": "ACTIVE",
    },
    "876543210987": {
        "apaar_id": "876543210987",
        "first_name": "Ananya",
        "last_name": "Verma",
        "dob": "2004-11-20",
        "gender": "FEMALE",
        "abc_account_active": True,
        "registry_status": "ACTIVE",
    },
}


@mock_apaar_app.get("/verify/{apaar_id}")
async def verify_apaar(apaar_id: str) -> Dict[str, Any]:
    """Verify an APAAR ID against simulated national registry records."""
    is_valid, msg = validate_apaar_id(apaar_id)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"APAAR format validation failed: {msg}",
        )

    # Return registered student or synthetic mock for any mathematically valid ID
    if apaar_id in MOCK_NATIONAL_REGISTRY:
        return MOCK_NATIONAL_REGISTRY[apaar_id]

    return {
        "apaar_id": apaar_id,
        "first_name": "Verified",
        "last_name": "Scholar",
        "dob": "2003-01-01",
        "gender": "OTHER",
        "abc_account_active": True,
        "registry_status": "ACTIVE",
    }
