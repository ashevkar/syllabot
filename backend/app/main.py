import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.config import get_settings
from app.db.session import create_engine
from app.providers.registry import ProviderRegistry
from app.routers import health


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings = get_settings()
    app.state.db_engine = create_engine(settings)
    app.state.redis = Redis.from_url(str(settings.redis_url))
    app.state.providers = ProviderRegistry(settings)
    try:
        yield
    finally:
        await app.state.providers.aclose()
        await app.state.redis.aclose()
        await app.state.db_engine.dispose()


def create_app() -> FastAPI:
    # Read settings here so a bad environment fails at import, before uvicorn starts serving.
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    app = FastAPI(title="Syllabot API", version="0.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    return app


app = create_app()
