"""Standalone Mock National APAAR Registry Gateway Service.

This simulates the ABC/DigiLocker APAAR verification API for the hackathon;
production will use an official provider.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import date, datetime
import difflib
import json
import logging
import os
from pathlib import Path
import random
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Header, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

logger = logging.getLogger("mock_apaar")
logging.basicConfig(level=logging.INFO)

API_KEY_ENV = os.getenv("APAAR_MOCK_API_KEY", "mock-apaar-secret-key-2026")
LATENCY_MS_ENV = float(os.getenv("APAAR_MOCK_LATENCY_MS", "0"))
FAILURE_RATE_ENV = float(os.getenv("APAAR_MOCK_FAILURE_RATE", "0.0"))

# In-memory registry loaded from JSON
REGISTRY: Dict[str, Dict[str, Any]] = {}


def resolve_registry_path() -> Path:
    """Resolve data/apaar_registry.json across container and local repository layouts."""
    env_path = os.getenv("APAAR_REGISTRY_PATH")
    if env_path and Path(env_path).is_file():
        return Path(env_path)

    candidates = [
        Path("/app/data/apaar_registry.json"),
        Path(__file__).resolve().parent.parent.parent / "data" / "apaar_registry.json",
        Path(__file__).resolve().parent.parent / "data" / "apaar_registry.json",
        Path("data/apaar_registry.json"),
    ]
    for c in candidates:
        if c.is_file():
            return c
    return candidates[1]


def load_registry_data() -> None:
    """Load JSON registry into memory."""
    global REGISTRY
    path = resolve_registry_path()
    if path.is_file():
        try:
            with open(path, "r", encoding="utf-8") as f:
                REGISTRY = json.load(f)
            logger.info(f"Loaded {len(REGISTRY)} records into Mock APAAR Registry from {path}")
        except Exception as e:
            logger.error(f"Failed to load registry from {path}: {e}")
            REGISTRY = {}
    else:
        logger.warning(f"APAAR registry file not found at {path}. Operating with empty registry.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_registry_data()
    yield


mock_apaar_app = FastAPI(
    title="Mock National APAAR Registry Gateway",
    description="Simulates ABC/DigiLocker APAAR verification API for SIH 26263. Production will use an official provider.",
    version="1.0.0",
    lifespan=lifespan,
)
app = mock_apaar_app



def compute_name_match_score(name1: Optional[str], name2: Optional[str]) -> int:
    """Compute fuzzy match score (0-100) handling case and token reordering."""
    if not name1 or not name2:
        return 0
    clean1 = " ".join(name1.lower().split())
    clean2 = " ".join(name2.lower().split())
    if clean1 == clean2:
        return 100

    tokens1 = sorted(clean1.split())
    tokens2 = sorted(clean2.split())
    if tokens1 == tokens2:
        return 95

    ratio = difflib.SequenceMatcher(None, clean1, clean2).ratio()
    sorted_ratio = difflib.SequenceMatcher(None, " ".join(tokens1), " ".join(tokens2)).ratio()
    return int(round(max(ratio, sorted_ratio) * 100))


def normalize_dob(dob_val: Any) -> Optional[str]:
    """Normalize date to YYYY-MM-DD string."""
    if not dob_val:
        return None
    if isinstance(dob_val, (date, datetime)):
        return dob_val.strftime("%Y-%m-%d")
    s = str(dob_val).strip()
    try:
        # Standard format
        return datetime.strptime(s[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        pass
    return s


# ==============================================================================
# Request & Response Schemas
# ==============================================================================

class VerifySingleRequest(BaseModel):
    apaar_id: str = Field(..., min_length=12, max_length=12, description="12-digit numeric APAAR ID")
    name: Optional[str] = Field(None, description="Expected student name for fuzzy matching")
    dob: Optional[str] = Field(None, description="Expected date of birth (YYYY-MM-DD)")


class VerifySingleResponse(BaseModel):
    apaar_id: str
    found: bool
    status: str = Field(..., description="ACTIVE, INACTIVE, NOT_FOUND")
    name_match_score: int = Field(0, ge=0, le=100)
    dob_match: bool
    last_known_institution: Optional[str] = None


class VerifyBatchRequest(BaseModel):
    items: List[VerifySingleRequest] = Field(..., min_length=1, max_length=500)


class VerifyBatchResponse(BaseModel):
    results: Dict[str, VerifySingleResponse]


# ==============================================================================
# Middleware & Helpers
# ==============================================================================

async def apply_chaos_and_auth(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None),
) -> None:
    """Validate API Key and simulate configurable latency/failures."""
    # 1. API Key Auth
    provided_key = x_api_key
    if not provided_key and authorization and authorization.lower().startswith("bearer "):
        provided_key = authorization.split(" ", 1)[1].strip()

    expected_key = os.getenv("APAAR_MOCK_API_KEY", API_KEY_ENV)
    if expected_key and provided_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing APAAR Gateway API key.",
        )

    # 2. Injected Latency
    latency_ms = float(os.getenv("APAAR_MOCK_LATENCY_MS", str(LATENCY_MS_ENV)))
    if latency_ms > 0:
        await asyncio.sleep(latency_ms / 1000.0)

    # 3. Injected Outage / Failure Rate
    failure_rate = float(os.getenv("APAAR_MOCK_FAILURE_RATE", str(FAILURE_RATE_ENV)))
    if failure_rate > 0 and random.random() < failure_rate:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Simulated Gateway Outage: APAAR National Registry temporarily unavailable.",
        )


def _process_single(req: VerifySingleRequest) -> VerifySingleResponse:
    clean_id = req.apaar_id.strip()
    record = REGISTRY.get(clean_id)

    if not record:
        return VerifySingleResponse(
            apaar_id=clean_id,
            found=False,
            status="NOT_FOUND",
            name_match_score=0,
            dob_match=False,
            last_known_institution=None,
        )

    rec_name = record.get("full_name") or record.get("name") or f"{record.get('first_name', '')} {record.get('last_name', '')}".strip()
    name_score = compute_name_match_score(req.name, rec_name) if req.name else 100

    rec_dob = normalize_dob(record.get("dob"))
    input_dob = normalize_dob(req.dob)
    dob_matches = bool(input_dob and rec_dob and input_dob == rec_dob) if req.dob else True

    rec_status = (record.get("registry_status") or record.get("status") or "ACTIVE").upper()

    return VerifySingleResponse(
        apaar_id=clean_id,
        found=True,
        status=rec_status,
        name_match_score=name_score,
        dob_match=dob_matches,
        last_known_institution=record.get("institution_name") or record.get("last_known_institution"),
    )


# ==============================================================================
# Endpoints
# ==============================================================================

@mock_apaar_app.get("/health", summary="Health check probe")
async def health():
    return {
        "status": "HEALTHY",
        "service": "Mock National APAAR Gateway",
        "loaded_records": len(REGISTRY),
    }


@mock_apaar_app.post(
    "/apaar/verify",
    response_model=VerifySingleResponse,
    summary="Verify a single APAAR ID with name and DOB validation",
)
async def verify_single(
    req: VerifySingleRequest,
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None),
) -> VerifySingleResponse:
    """Verify single APAAR ID against national registry with name score & DOB comparison."""
    await apply_chaos_and_auth(request, x_api_key, authorization)
    return _process_single(req)


@mock_apaar_app.post(
    "/apaar/verify-batch",
    response_model=VerifyBatchResponse,
    summary="Batch verify up to 500 APAAR IDs",
)
async def verify_batch(
    req: VerifyBatchRequest,
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None),
) -> VerifyBatchResponse:
    """Verify a batch of up to 500 APAAR records in a single payload."""
    await apply_chaos_and_auth(request, x_api_key, authorization)
    results = {}
    for item in req.items:
        results[item.apaar_id] = _process_single(item)
    return VerifyBatchResponse(results=results)
