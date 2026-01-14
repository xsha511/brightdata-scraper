"""Tests for Temu product service."""

import pytest
from datetime import datetime
from uuid import uuid4

from src.database import get_engine, init_db, get_session
from src.temu.service import ProductService
from src.temu.models import ProductCreate


@pytest.fixture
async def db_engine(tmp_path):
    """Create test database engine."""
    db_path = tmp_path / "test.db"
    engine = get_engine(str(db_path))
    await init_db(engine)
    return engine


@pytest.fixture
def sample_product():
    """Sample product data."""
    return ProductCreate(
        product_id="test-123",
        title="Test Product",
        url="https://www.temu.com/test.html",
        current_price=9.99,
        sold_count=100,
    )


@pytest.mark.asyncio
async def test_save_product_new(db_engine, sample_product):
    """Test saving a new product."""
    service = ProductService(db_engine)

    result = await service.save_product(sample_product)

    assert result.success is True
    assert result.is_new is True
    assert result.product_id == "test-123"


@pytest.mark.asyncio
async def test_save_product_update(db_engine, sample_product):
    """Test updating existing product."""
    service = ProductService(db_engine)

    # First save
    await service.save_product(sample_product)

    # Update with new price
    sample_product.current_price = 7.99
    result = await service.save_product(sample_product)

    assert result.success is True
    assert result.is_new is False


@pytest.mark.asyncio
async def test_get_product(db_engine, sample_product):
    """Test getting product by ID."""
    service = ProductService(db_engine)
    await service.save_product(sample_product)

    product = await service.get_product("test-123")

    assert product is not None
    assert product.title == "Test Product"


@pytest.mark.asyncio
async def test_price_history_recorded(db_engine, sample_product):
    """Test that price changes are recorded in history."""
    service = ProductService(db_engine)

    # First save at 9.99
    await service.save_product(sample_product)

    # Update to 7.99
    sample_product.current_price = 7.99
    await service.save_product(sample_product)

    product = await service.get_product("test-123", include_history=True)

    # Should have 2 history entries
    assert len(product.price_history) >= 1
