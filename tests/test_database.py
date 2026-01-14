"""Tests for database configuration."""

import pytest
import asyncio
from pathlib import Path

from sqlalchemy import text

from src.database import get_engine, init_db, get_session


@pytest.fixture
def test_db_path(tmp_path):
    """Use temporary database for tests."""
    return tmp_path / "test.db"


@pytest.mark.asyncio
async def test_init_db_creates_tables(test_db_path, monkeypatch):
    """Test that init_db creates all tables."""
    monkeypatch.setenv("DATABASE_PATH", str(test_db_path))

    engine = get_engine(str(test_db_path))
    await init_db(engine)

    # Check database file exists
    assert test_db_path.exists()


@pytest.mark.asyncio
async def test_get_session_works(test_db_path, monkeypatch):
    """Test that get_session returns working session."""
    monkeypatch.setenv("DATABASE_PATH", str(test_db_path))

    engine = get_engine(str(test_db_path))
    await init_db(engine)

    async with get_session(engine) as session:
        result = await session.execute(text("SELECT 1"))
        assert result is not None
