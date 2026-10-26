"""Common Pydantic v2 response schemas and envelopes."""

from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Machine-readable error classification code")
    message: str = Field(..., description="Human-readable explanation of error")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed diagnostic context")
    request_id: str = Field(..., description="Correlation request ID matching X-Request-ID")


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class HealthStatus(BaseModel):
    status: str = Field("healthy", description="Application liveness status")
    app_name: str
    environment: str
    version: str
    timestamp: str
    request_id: str


class ComponentHealth(BaseModel):
    status: str = Field(..., description="Dependency health: 'connected' or 'degraded'")
    latency_ms: Optional[float] = None
    message: Optional[str] = None


class ReadyStatus(BaseModel):
    status: str = Field(..., description="'ready' or 'unhealthy'")
    database: ComponentHealth
    redis: ComponentHealth
    timestamp: str
    request_id: str


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1, description="Page number starting at 1")
    page_size: int = Field(20, ge=1, le=100, description="Items per page (max 100)")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total_items: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)
