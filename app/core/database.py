"""
app/core/database.py

Async SQLAlchemy 2.x database engine and session factory.

Extension points for Backend Developer #2:
  - Add new ORM models by importing them in the models/__init__.py.
  - Use `get_db` dependency in any new router to get a DB session.
  - Alembic will auto-detect new models if they are imported before
    `alembic revision --autogenerate` is run.

NEVER import business models here. Keep this file infrastructure-only.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """
    SQLAlchemy declarative base for all ORM models.

    All models in `app/models/` must inherit from this class.
    Alembic uses this metadata to auto-generate migration scripts.

    Usage (in any model file):
        from app.core.database import Base

        class MyModel(Base):
            __tablename__ = "my_table"
            ...
    """

    pass


def _create_engine() -> AsyncEngine:
    """Create and return the async SQLAlchemy engine."""
    engine_kwargs: dict[str, object] = {
        "echo": settings.debug,          # Log SQL in debug mode
    }
    
    if "postgres" in settings.database_url:
        engine_kwargs.update({
            "pool_pre_ping": True,           # Validate connections before use
            "pool_size": 10,                 # Base connection pool size
            "max_overflow": 20,              # Extra connections allowed under load
            "pool_recycle": 3600,            # Recycle connections every hour
        })

    logger.info("Creating database engine | url=%s", settings.database_url.split("@")[-1])
    return create_async_engine(settings.database_url, **engine_kwargs)


# ─── Module-level singletons ─────────────────────────────────────────────────
engine: AsyncEngine = _create_engine()

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,   # Objects remain usable after commit
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async database session.

    Usage in any router:
        from app.core.database import get_db

        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_db)):
            ...

    The session is automatically committed on success and rolled back
    on any exception, then closed in the finally block.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_all_tables() -> None:
    """
    Create all tables defined in Base.metadata.

    Used ONLY in tests (with SQLite in-memory database).
    In production, use Alembic migrations exclusively.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created via Base.metadata.create_all")


async def drop_all_tables() -> None:
    """Drop all tables. Used in tests only."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped via Base.metadata.drop_all")
