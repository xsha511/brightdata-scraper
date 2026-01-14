"""Tests for collect API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from src.api.routers.collect import router, get_product_service
from src.database import get_engine, init_db
from src.temu.service import ProductService


@pytest.fixture
async def app(tmp_path):
    """Create test app with temporary database."""
    db_path = tmp_path / "test.db"
    engine = get_engine(str(db_path))
    await init_db(engine)

    service = ProductService(engine)

    app = FastAPI()
    app.include_router(router, prefix="/api/collect")
    app.dependency_overrides[get_product_service] = lambda: service

    return app


@pytest.fixture
async def client(app):
    """Create test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_collect_product(client):
    """Test POST /api/collect/product."""
    response = await client.post("/api/collect/product", json={
        "product_id": "test-123",
        "title": "Test Product",
        "url": "https://www.temu.com/test.html",
        "current_price": 9.99,
    })

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["product_id"] == "test-123"
    assert data["is_new"] is True


@pytest.mark.asyncio
async def test_collect_product_update(client):
    """Test updating product via collect endpoint."""
    # First create
    await client.post("/api/collect/product", json={
        "product_id": "test-123",
        "title": "Test Product",
        "url": "https://www.temu.com/test.html",
        "current_price": 9.99,
    })

    # Then update
    response = await client.post("/api/collect/product", json={
        "product_id": "test-123",
        "title": "Test Product Updated",
        "url": "https://www.temu.com/test.html",
        "current_price": 7.99,
    })

    assert response.status_code == 200
    data = response.json()
    assert data["is_new"] is False


@pytest.mark.asyncio
async def test_collect_batch(client):
    """Test POST /api/collect/batch."""
    response = await client.post("/api/collect/batch", json={
        "products": [
            {"product_id": "batch-1", "title": "Product 1", "url": "https://temu.com/1"},
            {"product_id": "batch-2", "title": "Product 2", "url": "https://temu.com/2"},
        ]
    })

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["saved_count"] == 2
