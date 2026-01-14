"""Tests for products API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from src.api.routers.products import router, get_product_service
from src.api.routers.collect import router as collect_router
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
    app.include_router(collect_router, prefix="/api/collect")
    app.include_router(router, prefix="/api/products")

    # Override dependency for both routers
    def override_service():
        return service

    app.dependency_overrides[get_product_service] = override_service
    # Import and override from collect router too
    from src.api.routers import collect
    app.dependency_overrides[collect.get_product_service] = override_service

    return app


@pytest.fixture
async def client(app):
    """Create test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def seeded_client(client):
    """Client with pre-seeded products."""
    # Add some products
    for i in range(5):
        await client.post("/api/collect/product", json={
            "product_id": f"product-{i}",
            "title": f"Product {i}",
            "url": f"https://www.temu.com/{i}.html",
            "current_price": 10.0 + i,
        })
    return client


@pytest.mark.asyncio
async def test_list_products(seeded_client):
    """Test GET /api/products."""
    response = await seeded_client.get("/api/products")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["products"]) == 5


@pytest.mark.asyncio
async def test_list_products_pagination(seeded_client):
    """Test pagination."""
    response = await seeded_client.get("/api/products?page=1&page_size=2")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["products"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2


@pytest.mark.asyncio
async def test_get_product(seeded_client):
    """Test GET /api/products/{product_id}."""
    response = await seeded_client.get("/api/products/product-0")

    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] == "product-0"
    assert data["title"] == "Product 0"


@pytest.mark.asyncio
async def test_get_product_not_found(client):
    """Test 404 for non-existent product."""
    response = await client.get("/api/products/nonexistent")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_product_with_history(seeded_client):
    """Test getting product with price history."""
    # Update price to create history
    await seeded_client.post("/api/collect/product", json={
        "product_id": "product-0",
        "title": "Product 0",
        "url": "https://www.temu.com/0.html",
        "current_price": 8.99,
    })

    response = await seeded_client.get("/api/products/product-0?include_history=true")

    assert response.status_code == 200
    data = response.json()
    assert len(data["price_history"]) >= 1
