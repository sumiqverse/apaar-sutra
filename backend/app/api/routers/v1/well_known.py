"""JWKS endpoint exposing sovereign Ed25519 verification public keys."""

from typing import Any, Dict, List
from fastapi import APIRouter

from app.core.signing import get_key_provider

router = APIRouter(tags=["Cryptographic Key Registry"])


@router.get(
    "/.well-known/apaar-sutra-keys.json",
    summary="JWKS Public Verification Key Set",
    description="Returns public keys for sovereign Ed25519 verification of APAAR-Sutra credentials per RFC 8037.",
)
async def get_jwks_keys() -> Dict[str, List[Dict[str, Any]]]:
    provider = get_key_provider()
    return provider.get_jwks()
