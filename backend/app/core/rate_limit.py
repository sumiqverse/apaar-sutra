"""Redis-backed sliding window rate limiter and account lockout protection."""

from datetime import datetime, timedelta, timezone
import time
from typing import Dict, List, Optional
import redis

from app.core.config import settings

# Initialize Redis client with connection pooling and timeouts
try:
    redis_client: Optional[redis.Redis] = redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
except Exception:
    redis_client = None

# In-memory fallback sliding window cache for offline/test environments
_memory_cache: Dict[str, List[float]] = {}
_lockout_memory: Dict[str, float] = {}

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


def check_rate_limit(key: str, limit: int, window_seconds: int = 60) -> bool:
    """Check if an action is within allowed rate limit using sliding window.
    
    Returns True if allowed, False if limit exceeded.
    """
    now = time.time()
    cutoff = now - window_seconds

    if redis_client:
        try:
            pipe = redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, cutoff)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, window_seconds + 1)
            _, _, count, _ = pipe.execute()
            return count <= limit
        except Exception:
            pass  # Fall back to in-memory

    # In-memory sliding window fallback
    timestamps = _memory_cache.setdefault(key, [])
    timestamps = [ts for ts in timestamps if ts > cutoff]
    timestamps.append(now)
    _memory_cache[key] = timestamps
    return len(timestamps) <= limit


def is_account_locked(user_email: str, db_locked_until: Optional[datetime] = None) -> Optional[int]:
    """Check if an account is locked due to consecutive failed login attempts.
    
    Returns remaining lockout seconds if locked, or None if active.
    """
    now_utc = datetime.now(timezone.utc)

    # 1. Check DB level lockout timestamp
    if db_locked_until:
        if db_locked_until.tzinfo is None:
            db_locked_until = db_locked_until.replace(tzinfo=timezone.utc)
        if db_locked_until > now_utc:
            remaining = int((db_locked_until - now_utc).total_seconds())
            return max(1, remaining)

    # 2. Check Redis / memory lockout key
    lockout_key = f"lockout:{user_email.lower()}"
    if redis_client:
        try:
            ttl = redis_client.ttl(lockout_key)
            if ttl and ttl > 0:
                return ttl
        except Exception:
            pass

    mem_lock_time = _lockout_memory.get(lockout_key)
    if mem_lock_time and mem_lock_time > time.time():
        return int(mem_lock_time - time.time())

    return None


def register_login_failure(user_email: str) -> int:
    """Register a failed login attempt. Returns current failure count."""
    key = f"failed_logins:{user_email.lower()}"
    lockout_key = f"lockout:{user_email.lower()}"

    if redis_client:
        try:
            count = redis_client.incr(key)
            redis_client.expire(key, LOCKOUT_DURATION_MINUTES * 60)
            if count >= MAX_LOGIN_ATTEMPTS:
                redis_client.setex(lockout_key, LOCKOUT_DURATION_MINUTES * 60, "locked")
            return count
        except Exception:
            pass

    # In-memory fallback
    now = time.time()
    cutoff = now - (LOCKOUT_DURATION_MINUTES * 60)
    timestamps = _memory_cache.setdefault(key, [])
    timestamps = [ts for ts in timestamps if ts > cutoff]
    timestamps.append(now)
    _memory_cache[key] = timestamps
    count = len(timestamps)

    if count >= MAX_LOGIN_ATTEMPTS:
        _lockout_memory[lockout_key] = now + (LOCKOUT_DURATION_MINUTES * 60)

    return count


def clear_login_failures(user_email: str) -> None:
    """Reset failed login attempts and lockout state upon successful authentication."""
    key = f"failed_logins:{user_email.lower()}"
    lockout_key = f"lockout:{user_email.lower()}"

    if redis_client:
        try:
            redis_client.delete(key, lockout_key)
        except Exception:
            pass

    _memory_cache.pop(key, None)
    _lockout_memory.pop(lockout_key, None)
