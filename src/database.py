"""Database configuration and session management."""

import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from .temu.models import Base


def get_database_url(db_path: str = None) -> str:
    """Get database URL from path or environment."""
    if db_path is None:
        db_path = os.getenv("DATABASE_PATH", "data/temu.db")

    # Ensure directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    return f"sqlite+aiosqlite:///{db_path}"


def get_engine(db_path: str = None) -> AsyncEngine:
    """Create async database engine."""
    url = get_database_url(db_path)
    return create_async_engine(url, echo=False)


async def init_db(engine: AsyncEngine) -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
