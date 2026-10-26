"""Circuit Breaker implementation for external integration fault tolerance."""

from enum import Enum
import logging
import time
from typing import Callable

logger = logging.getLogger("apaar_circuit_breaker")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Outage detected, fail-fast
    HALF_OPEN = "HALF_OPEN"# Testing recovery with limited traffic


class CircuitBreakerOpenException(Exception):
    """Raised when request is rejected because the circuit is OPEN."""
    pass


class CircuitBreaker:
    """In-memory Circuit Breaker with exponential recovery timeouts."""

    def __init__(
        self,
        name: str = "APAAR_GATEWAY",
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 30.0,
        recovery_timeout: Optional[float] = None,
        half_open_success_threshold: int = 1,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout if recovery_timeout is not None else recovery_timeout_seconds
        self.half_open_success_threshold = half_open_success_threshold

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.success_count = 0

    def can_execute(self) -> bool:
        """Check whether execution is allowed through the circuit."""
        now = time.time()
        if self.state == CircuitState.OPEN:
            if now - self.last_failure_time >= self.recovery_timeout_seconds:
                logger.info(f"[{self.name}] Circuit transitioning from OPEN to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                return True
            return False
        return True

    def record_success(self) -> None:
        """Record successful call through the circuit."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.half_open_success_threshold:
                logger.info(f"[{self.name}] Circuit recovered: HALF_OPEN -> CLOSED")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def record_failure(self) -> None:
        """Record failed call through the circuit."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            logger.warning(f"[{self.name}] Call failed in HALF_OPEN. Tripping back to OPEN.")
            self.state = CircuitState.OPEN
        elif self.failure_count >= self.failure_threshold:
            logger.error(
                f"[{self.name}] Failure threshold {self.failure_threshold} reached. Tripping circuit to OPEN."
            )
            self.state = CircuitState.OPEN

    def __enter__(self):
        if not self.can_execute():
            raise CircuitBreakerOpenException(f"Circuit {self.name} is OPEN. Calls are rejected.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and not issubclass(exc_type, CircuitBreakerOpenException):
            self.record_failure()
        elif exc_type is None:
            self.record_success()
        return False

