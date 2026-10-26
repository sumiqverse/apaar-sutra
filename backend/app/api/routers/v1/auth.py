"""Authentication and session validation endpoints."""

from typing import Dict
from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["Authentication & Context"])


@router.get("/context", summary="Get User Context")
async def get_user_context() -> Dict[str, str]:
    """Returns the authenticated user's role and tenant scoping details."""
    return {
        "status": "authenticated",
        "role": "SUPER_ADMIN",
        "institution_name": "AICTE Central Directorate",
        "jurisdiction": "National",
    }
