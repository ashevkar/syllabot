from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from testcontainers.community.postgres import PostgresContainer

# Keep in sync with the postgres image in docker-compose.yml.
PGVECTOR_IMAGE = "pgvector/pgvector:0.8.7-pg16"
ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def alembic_config(database_url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.attributes["database_url"] = database_url
    return cfg


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    """A throwaway Postgres + pgvector, migrated to head with the real migrations."""
    with PostgresContainer(PGVECTOR_IMAGE, driver="asyncpg") as pg:
        url = pg.get_connection_url()
        command.upgrade(alembic_config(url), "head")
        yield url


@pytest.fixture
async def session(database_url: str) -> AsyncIterator[AsyncSession]:
    """A session whose work is rolled back after each test, even if the test commits."""
    engine = create_async_engine(database_url)
    async with engine.connect() as conn:
        outer = await conn.begin()
        db = AsyncSession(bind=conn, join_transaction_mode="create_savepoint")
        try:
            yield db
        finally:
            await db.close()
            await outer.rollback()
    await engine.dispose()
