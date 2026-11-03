import asyncio
import logging
from collections.abc import Awaitable
from typing import Literal

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])

CHECK_TIMEOUT_S = 2.0

CheckStatus = Literal["ok", "error"]


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: CheckStatus
    redis: CheckStatus


async def check_database(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def check_redis(client: Redis) -> None:
    await client.ping()


async def _run(name: str, check: Awaitable[None]) -> CheckStatus:
    try:
        await asyncio.wait_for(check, timeout=CHECK_TIMEOUT_S)
    except Exception:
        logger.warning("health check failed: %s", name, exc_info=True)
        return "error"
    return "ok"


@router.get("/health", response_model=HealthResponse)
async def health(request: Request, response: Response) -> HealthResponse:
    database, redis = await asyncio.gather(
        _run("database", check_database(request.app.state.db_engine)),
        _run("redis", check_redis(request.app.state.redis)),
    )
    healthy = database == "ok" and redis == "ok"
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(status="ok" if healthy else "degraded", database=database, redis=redis)
