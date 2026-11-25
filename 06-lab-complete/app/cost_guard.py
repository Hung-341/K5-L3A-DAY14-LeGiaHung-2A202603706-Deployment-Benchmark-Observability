"""Daily cost accounting in Redis."""
from datetime import datetime, timedelta, timezone
import math

import redis
from fastapi import HTTPException

from app.config import settings
from app.redis_client import r


PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006


def _cost_key() -> str:
    day = datetime.now(timezone.utc).date().isoformat()
    return f"agent:cost:daily:{day}"


def _seconds_until_utc_midnight() -> int:
    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).date()
    midnight = datetime.combine(tomorrow, datetime.min.time(), tzinfo=timezone.utc)
    return max(1, math.ceil((midnight - now).total_seconds()))


def check_budget() -> None:
    """Reject new work after the configured daily budget has been spent."""
    try:
        current = float(r.get(_cost_key()) or 0)
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail="Cost guard unavailable") from exc
    if current >= settings.daily_budget_usd:
        raise HTTPException(status_code=402, detail="Daily budget exceeded")


def record_cost(input_tokens: int, output_tokens: int) -> float:
    """Store this request's estimated token cost and return the amount."""
    cost = (
        input_tokens * PRICE_INPUT_PER_1K + output_tokens * PRICE_OUTPUT_PER_1K
    ) / 1000
    try:
        key = _cost_key()
        r.incrbyfloat(key, cost)
        r.expire(key, _seconds_until_utc_midnight())
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail="Cost guard unavailable") from exc
    return cost
