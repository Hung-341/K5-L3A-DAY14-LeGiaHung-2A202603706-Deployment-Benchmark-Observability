"""Redis-backed, atomic sliding-window rate limiter."""
import hashlib
import time
import uuid

import redis
from fastapi import HTTPException

from app.config import settings
from app.redis_client import r


_WINDOW_MS = 60_000
_CHECK_AND_ADD = r.register_script(
    """
    local key = KEYS[1]
    local now = tonumber(ARGV[1])
    local window = tonumber(ARGV[2])
    local limit = tonumber(ARGV[3])
    redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)
    local count = redis.call('ZCARD', key)
    if count >= limit then
        local first = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
        local retry = 1
        if first[2] then
            retry = math.max(1, math.ceil((tonumber(first[2]) + window - now) / 1000))
        end
        return {0, retry}
    end
    redis.call('ZADD', key, now, ARGV[4])
    redis.call('EXPIRE', key, math.ceil(window / 1000) + 1)
    return {1, 0}
    """
)


def check_rate_limit(key: str) -> None:
    """Allow at most N requests per API key in the last 60 seconds."""
    key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
    now_ms = int(time.time() * 1000)
    try:
        allowed, retry_after = _CHECK_AND_ADD(
            keys=[f"agent:rate:{key_hash}"],
            args=[
                now_ms,
                _WINDOW_MS,
                settings.rate_limit_per_minute,
                f"{now_ms}:{uuid.uuid4().hex}",
            ],
        )
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail="Rate limiter unavailable") from exc

    if not int(allowed):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(int(retry_after))},
        )
