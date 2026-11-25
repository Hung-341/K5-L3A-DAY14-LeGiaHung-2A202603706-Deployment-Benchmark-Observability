"""Production-ready mock AI agent for the Day 14 lab."""
from contextlib import asynccontextmanager
import json
import logging
import math
import time

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, record_cost
from app.rate_limiter import check_rate_limit
from app.redis_client import r, redis_healthy
from utils.mock_llm import ask as llm_ask


logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("day14.agent")


def log_event(event: str, **fields: object) -> None:
    logger.info(json.dumps({"event": event, **fields}, ensure_ascii=False))


@asynccontextmanager
async def lifespan(_: FastAPI):
    log_event("startup", environment=settings.environment, port=settings.port)
    try:
        yield
    finally:
        r.close()
        log_event("shutdown", message="Agent stopped gracefully")


app = FastAPI(title="Production AI Agent", lifespan=lifespan)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness: process is alive, independent of Redis availability."""
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, bool]:
    """Readiness: accept traffic only when Redis can be reached."""
    if not redis_healthy():
        raise HTTPException(status_code=503, detail="Redis is not ready")
    return {"ready": True}


@app.post("/ask")
def ask(body: AskRequest, api_key: str = Depends(verify_api_key)) -> dict[str, str]:
    started = time.perf_counter()
    check_rate_limit(api_key)
    check_budget()

    answer = llm_ask(body.question)
    input_tokens = max(1, math.ceil(len(body.question) / 4))
    output_tokens = max(1, math.ceil(len(answer) / 4))
    cost = record_cost(input_tokens, output_tokens)

    log_event(
        "agent_request",
        path="/ask",
        status=200,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=round(cost, 8),
        ms=round((time.perf_counter() - started) * 1000, 1),
    )
    return {"question": body.question, "answer": answer}
