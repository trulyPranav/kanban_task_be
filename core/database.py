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


def _build_connect_args() -> dict:
    """Return driver-specific connect_args based on the configured database URL."""
    if _is_sqlite:
        # Prevent SQLite threading errors in async context
        return {"check_same_thread": False}
    if settings.DB_SSL:
        # Supabase Transaction Pooler uses an intermediate CA not trusted by
        # Windows' default cert store, so we use ssl="require" which enforces
        # encryption without strict certificate chain verification.
        return {"ssl": "require"}
    return {}


# Pool settings only apply to PostgreSQL; SQLAlchemy ignores them for SQLite.
_pool_kwargs = (
    {}
    if _is_sqlite
    else {
        "pool_size": 5,          # Supabase free tier allows ~15 connections; keep headroom
        "max_overflow": 10,      # Extra connections allowed beyond pool_size under burst load
        "pool_timeout": 30,      # Seconds to wait for a free connection before raising
        "pool_recycle": 1800,    # Recycle connections after 30 min to avoid stale TCP issues
        "pool_pre_ping": True,   # Cheaply verify a connection is alive before using it
    }
)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=_build_connect_args(),
    **_pool_kwargs,
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
