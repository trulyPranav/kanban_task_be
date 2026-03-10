import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import settings

logger = logging.getLogger(__name__)

# ─── Engine ───────────────────────────────────────────────────────────────────
_is_sqlite = "sqlite" in settings.DATABASE_URL

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    # SQLite-specific: keep a single connection to avoid locking issues
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# ─── Dependency ───────────────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ─── Init ─────────────────────────────────────────────────────────────────────
async def init_db() -> None:
    """Create all tables on startup (idempotent)."""
    # Import models so SQLAlchemy registers them before create_all
    import models  # noqa: F401

    from models.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified / created.")
