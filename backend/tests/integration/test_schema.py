import uuid

import pytest
from alembic import command
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.db.enums import BotStatus, DocSource, DocStatus
from app.db.models import EMBEDDING_DIM, Bot, Chunk, Document, User
from tests.integration.conftest import alembic_config

pytestmark = pytest.mark.integration


def _vec(*head: float) -> list[float]:
    """A full-size embedding whose first components are `head`, the rest zero."""
    return [*head, *([0.0] * (EMBEDDING_DIM - len(head)))]


async def _seed_bot(db: AsyncSession) -> tuple[User, Bot, Document]:
    user = User(email="Ada@Example.edu", password_hash="x", full_name="Ada Lovelace")
    db.add(user)
    await db.flush()
    bot = Bot(
        owner_id=user.id,
        course_name="CSE 110",
        system_prompt="Answer from the syllabus.",
        model="gemini:gemini-3.5-flash-lite",
        fallback_message="Please ask your instructor.",
        share_slug=uuid.uuid4().hex[:10],
    )
    db.add(bot)
    await db.flush()
    doc = Document(bot_id=bot.id, filename="syllabus.pdf", storage_key="k/1")
    db.add(doc)
    await db.flush()
    return user, bot, doc


async def test_user_bot_document_chunk_round_trip(session: AsyncSession) -> None:
    user, bot, doc = await _seed_bot(session)
    session.add(
        Chunk(
            bot_id=bot.id,
            document_id=doc.id,
            chunk_index=0,
            section_title="Grading",
            page_start=2,
            page_end=2,
            content="Final exam is worth 30%.",
            token_count=7,
            embedding=_vec(1.0),
            embedding_model="gemini-embedding-2",
        )
    )
    # Read ids before committing: expired attributes can't lazy-load in an async session.
    user_id, bot_id, doc_id = user.id, bot.id, doc.id
    await session.commit()
    session.expire_all()

    chunk = (await session.execute(select(Chunk).where(Chunk.bot_id == bot_id))).scalar_one()
    assert chunk.document_id == doc_id
    assert chunk.section_title == "Grading"
    assert len(chunk.embedding) == EMBEDDING_DIM
    assert chunk.tsv  # generated column is populated

    # Server defaults from the schema
    loaded_bot = await session.get(Bot, bot_id)
    assert loaded_bot is not None
    assert loaded_bot.status is BotStatus.DRAFT
    assert loaded_bot.timezone == "America/Phoenix"
    assert loaded_bot.rate_limit_per_min == 20
    assert loaded_bot.suggested_questions == []
    loaded_doc = await session.get(Document, doc_id)
    assert loaded_doc is not None
    assert loaded_doc.source_type is DocSource.FILE
    assert loaded_doc.status is DocStatus.UPLOADED

    # CITEXT: email lookups are case-insensitive
    found = await session.scalar(select(User.id).where(User.email == "ada@example.edu"))
    assert found == user_id


async def test_cosine_search_orders_by_similarity(session: AsyncSession) -> None:
    _, bot, doc = await _seed_bot(session)
    for i, vec in enumerate([_vec(0.0, 1.0), _vec(1.0, 0.0), _vec(1.0, 1.0)]):
        session.add(
            Chunk(
                bot_id=bot.id,
                document_id=doc.id,
                chunk_index=i,
                content=f"chunk {i}",
                token_count=2,
                embedding=vec,
                embedding_model="test",
            )
        )
    await session.flush()

    distance = Chunk.embedding.cosine_distance(_vec(1.0, 0.0))
    rows = await session.execute(
        select(Chunk.chunk_index, 1 - distance).where(Chunk.bot_id == bot.id).order_by(distance)
    )
    ranked = [(index, round(score, 3)) for index, score in rows]

    assert [index for index, _ in ranked] == [1, 2, 0]
    assert ranked[0][1] == pytest.approx(1.0)


async def test_deleting_a_document_cascades_to_its_chunks(session: AsyncSession) -> None:
    _, bot, doc = await _seed_bot(session)
    session.add(
        Chunk(
            bot_id=bot.id,
            document_id=doc.id,
            chunk_index=0,
            content="c",
            token_count=1,
            embedding=_vec(1.0),
            embedding_model="test",
        )
    )
    await session.flush()

    await session.execute(text("DELETE FROM documents WHERE id = :id"), {"id": doc.id})

    remaining = await session.scalar(select(func.count()).where(Chunk.document_id == doc.id))
    assert remaining == 0


async def test_file_document_requires_storage_key(session: AsyncSession) -> None:
    _, bot, _ = await _seed_bot(session)
    session.add(Document(bot_id=bot.id, source_type=DocSource.FILE, filename="x.pdf"))

    with pytest.raises(IntegrityError, match="ck_documents_source_location"):
        await session.flush()


def test_downgrade_to_base_leaves_nothing_behind(database_url: str) -> None:
    import asyncio

    async def state() -> tuple[int, int, int]:
        engine = create_async_engine(database_url)
        async with engine.connect() as conn:
            tables = await conn.scalar(
                text(
                    "SELECT count(*) FROM pg_tables "
                    "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
                )
            )
            enums = await conn.scalar(text("SELECT count(*) FROM pg_type WHERE typtype = 'e'"))
            exts = await conn.scalar(
                text("SELECT count(*) FROM pg_extension WHERE extname <> 'plpgsql'")
            )
        await engine.dispose()
        return tables or 0, enums or 0, exts or 0

    cfg = alembic_config(database_url)
    assert asyncio.run(state()) == (12, 9, 3)

    command.downgrade(cfg, "base")
    try:
        assert asyncio.run(state()) == (0, 0, 0)
    finally:
        command.upgrade(cfg, "head")  # leave the shared database at head for other tests

    assert asyncio.run(state()) == (12, 9, 3)


def test_models_match_migrations(database_url: str) -> None:
    """Same check as `alembic check`: a model change without a migration fails CI."""
    import asyncio

    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    from app.db.base import Base

    def diff(sync_conn: object) -> list[object]:
        context = MigrationContext.configure(sync_conn)  # type: ignore[arg-type]
        return list(compare_metadata(context, Base.metadata))

    async def run() -> list[object]:
        engine = create_async_engine(database_url)
        async with engine.connect() as conn:
            result = await conn.run_sync(diff)
        await engine.dispose()
        return result

    assert asyncio.run(run()) == []
