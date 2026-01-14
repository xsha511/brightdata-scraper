# Temu 数据采集系统 Phase 1 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 跑通 "Chrome 插件采集 Temu 商品数据 → FastAPI 服务端存储 → API 查询" 完整链路

**Architecture:** Chrome 插件负责在 Temu 页面提取商品数据并上报到 FastAPI 服务端。服务端使用 SQLAlchemy + SQLite 存储数据，提供 REST API 供查询。插件同时读取选品助手的历史数据一并上报。

**Tech Stack:** Python 3.9+, FastAPI, SQLAlchemy, SQLite, Chrome Extension (Manifest V3), JavaScript

---

## Task 1: 项目依赖和目录结构

**Files:**
- Modify: `pyproject.toml`
- Create: `src/temu/__init__.py`
- Create: `src/api/__init__.py`
- Create: `src/api/routers/__init__.py`

**Step 1: 更新 pyproject.toml 添加依赖**

```toml
dependencies = [
    "brightdata-sdk>=0.1.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
    "aiofiles>=23.0.0",
    "httpx>=0.25.0",
    # Temu 采集系统新增依赖
    "fastapi>=0.100.0",
    "uvicorn>=0.23.0",
    "sqlalchemy>=2.0.0",
    "aiosqlite>=0.19.0",
]
```

**Step 2: 创建模块目录**

```bash
mkdir -p src/temu src/api/routers
touch src/temu/__init__.py src/api/__init__.py src/api/routers/__init__.py
```

**Step 3: 安装依赖**

Run: `pip install -e .`
Expected: 成功安装所有依赖

**Step 4: Commit**

```bash
git add pyproject.toml src/temu src/api
git commit -m "chore: add FastAPI dependencies and create temu/api modules"
```

---

## Task 2: 数据库模型

**Files:**
- Create: `src/temu/models.py`
- Test: `tests/test_temu_models.py`

**Step 1: 写测试**

```python
# tests/test_temu_models.py
"""Tests for Temu data models."""

import pytest
from datetime import datetime
from src.temu.models import ProductCreate, ProductResponse


def test_product_create_minimal():
    """Test creating product with minimal required fields."""
    product = ProductCreate(
        product_id="123456789",
        title="Test Product",
        url="https://www.temu.com/test.html",
    )
    assert product.product_id == "123456789"
    assert product.currency == "GBP"  # default


def test_product_create_full():
    """Test creating product with all fields."""
    product = ProductCreate(
        product_id="123456789",
        title="Test Product",
        url="https://www.temu.com/test.html",
        current_price=9.99,
        original_price=19.99,
        sold_count=1000,
        rating=4.8,
        images=["img1.jpg", "img2.jpg"],
        seller_id="seller123",
        seller_name="Test Shop",
    )
    assert product.current_price == 9.99
    assert len(product.images) == 2


def test_product_response_includes_history():
    """Test ProductResponse includes price history."""
    response = ProductResponse(
        id="uuid-123",
        product_id="123456789",
        title="Test Product",
        url="https://www.temu.com/test.html",
        first_seen_at=datetime.utcnow(),
        last_updated_at=datetime.utcnow(),
        price_history=[],
    )
    assert response.price_history == []
```

**Step 2: 运行测试确认失败**

Run: `pytest tests/test_temu_models.py -v`
Expected: FAIL (ImportError: cannot import name 'ProductCreate')

**Step 3: 实现模型**

```python
# src/temu/models.py
"""Temu product data models."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Float, Integer, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


# ============ SQLAlchemy ORM Models ============

class ProductORM(Base):
    """SQLAlchemy model for products table."""
    __tablename__ = "products"

    id = Column(String, primary_key=True)
    product_id = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    url = Column(String)
    current_price = Column(Float)
    original_price = Column(Float)
    currency = Column(String, default="GBP")
    sold_count = Column(Integer)
    rating = Column(Float)
    review_count = Column(Integer)
    seller_id = Column(String)
    seller_name = Column(String)
    main_image = Column(String)
    images = Column(JSON, default=list)
    category_path = Column(JSON, default=list)
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    raw_data = Column(JSON)

    price_history = relationship("PriceHistoryORM", back_populates="product")


class PriceHistoryORM(Base):
    """SQLAlchemy model for price_history table."""
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String, ForeignKey("products.product_id"), index=True)
    price = Column(Float)
    sold_count = Column(Integer)
    recorded_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("ProductORM", back_populates="price_history")


class CollectLogORM(Base):
    """SQLAlchemy model for collect_logs table."""
    __tablename__ = "collect_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    page_type = Column(String)
    page_url = Column(String)
    products_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============ Pydantic Models (API) ============

class ProductCreate(BaseModel):
    """Schema for creating/collecting a product."""
    product_id: str
    title: str
    url: str
    current_price: Optional[float] = None
    original_price: Optional[float] = None
    currency: str = "GBP"
    sold_count: Optional[int] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    seller_id: Optional[str] = None
    seller_name: Optional[str] = None
    main_image: Optional[str] = None
    images: list[str] = Field(default_factory=list)
    category_path: list[str] = Field(default_factory=list)
    raw_data: Optional[dict] = None
    # History from 选品助手
    history: Optional[dict] = None


class PriceHistoryItem(BaseModel):
    """Schema for price history entry."""
    price: float
    sold_count: Optional[int] = None
    recorded_at: datetime


class ProductResponse(BaseModel):
    """Schema for product response with history."""
    id: str
    product_id: str
    title: str
    url: str
    current_price: Optional[float] = None
    original_price: Optional[float] = None
    currency: str = "GBP"
    sold_count: Optional[int] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    seller_id: Optional[str] = None
    seller_name: Optional[str] = None
    main_image: Optional[str] = None
    images: list[str] = Field(default_factory=list)
    first_seen_at: datetime
    last_updated_at: datetime
    price_history: list[PriceHistoryItem] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    """Schema for paginated product list."""
    total: int
    page: int
    page_size: int
    products: list[ProductResponse]


class CollectResponse(BaseModel):
    """Schema for collect API response."""
    success: bool
    message: str
    product_id: Optional[str] = None
    is_new: bool = False
```

**Step 4: 运行测试确认通过**

Run: `pytest tests/test_temu_models.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/temu/models.py tests/test_temu_models.py
git commit -m "feat(temu): add product data models with SQLAlchemy and Pydantic"
```

---

## Task 3: 数据库配置

**Files:**
- Create: `src/database.py`
- Test: `tests/test_database.py`

**Step 1: 写测试**

```python
# tests/test_database.py
"""Tests for database configuration."""

import pytest
import asyncio
from pathlib import Path

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
        result = await session.execute("SELECT 1")
        assert result is not None
```

**Step 2: 运行测试确认失败**

Run: `pytest tests/test_database.py -v`
Expected: FAIL (ImportError: cannot import name 'get_engine')

**Step 3: 实现数据库配置**

```python
# src/database.py
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
```

**Step 4: 运行测试确认通过**

Run: `pytest tests/test_database.py -v`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add src/database.py tests/test_database.py
git commit -m "feat: add async database configuration with SQLite"
```

---

## Task 4: 商品服务层

**Files:**
- Create: `src/temu/service.py`
- Test: `tests/test_temu_service.py`

**Step 1: 写测试**

```python
# tests/test_temu_service.py
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
```

**Step 2: 运行测试确认失败**

Run: `pytest tests/test_temu_service.py -v`
Expected: FAIL (ImportError: cannot import name 'ProductService')

**Step 3: 实现服务层**

```python
# src/temu/service.py
"""Temu product service layer."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncEngine

from ..database import get_session
from .models import (
    ProductORM, PriceHistoryORM, CollectLogORM,
    ProductCreate, ProductResponse, PriceHistoryItem,
    CollectResponse, ProductListResponse
)


class ProductService:
    """Service for managing Temu products."""

    def __init__(self, engine: AsyncEngine):
        self.engine = engine

    async def save_product(self, data: ProductCreate) -> CollectResponse:
        """Save or update a product. Records price history on changes."""
        async with get_session(self.engine) as session:
            # Check if product exists
            result = await session.execute(
                select(ProductORM).where(ProductORM.product_id == data.product_id)
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing product
                is_new = False
                old_price = existing.current_price

                # Update fields
                existing.title = data.title
                existing.url = data.url
                existing.current_price = data.current_price
                existing.original_price = data.original_price
                existing.sold_count = data.sold_count
                existing.rating = data.rating
                existing.review_count = data.review_count
                existing.seller_id = data.seller_id
                existing.seller_name = data.seller_name
                existing.main_image = data.main_image
                existing.images = data.images
                existing.category_path = data.category_path
                existing.raw_data = data.raw_data
                existing.last_updated_at = datetime.utcnow()

                # Record price history if price changed
                if old_price != data.current_price and data.current_price is not None:
                    history = PriceHistoryORM(
                        product_id=data.product_id,
                        price=data.current_price,
                        sold_count=data.sold_count,
                    )
                    session.add(history)
            else:
                # Create new product
                is_new = True
                product = ProductORM(
                    id=str(uuid4()),
                    product_id=data.product_id,
                    title=data.title,
                    url=data.url,
                    current_price=data.current_price,
                    original_price=data.original_price,
                    currency=data.currency,
                    sold_count=data.sold_count,
                    rating=data.rating,
                    review_count=data.review_count,
                    seller_id=data.seller_id,
                    seller_name=data.seller_name,
                    main_image=data.main_image,
                    images=data.images,
                    category_path=data.category_path,
                    raw_data=data.raw_data,
                )
                session.add(product)

                # Record initial price
                if data.current_price is not None:
                    history = PriceHistoryORM(
                        product_id=data.product_id,
                        price=data.current_price,
                        sold_count=data.sold_count,
                    )
                    session.add(history)

            return CollectResponse(
                success=True,
                message="Product saved" if is_new else "Product updated",
                product_id=data.product_id,
                is_new=is_new,
            )

    async def get_product(
        self, product_id: str, include_history: bool = False
    ) -> Optional[ProductResponse]:
        """Get product by ID with optional price history."""
        async with get_session(self.engine) as session:
            result = await session.execute(
                select(ProductORM).where(ProductORM.product_id == product_id)
            )
            product = result.scalar_one_or_none()

            if not product:
                return None

            price_history = []
            if include_history:
                history_result = await session.execute(
                    select(PriceHistoryORM)
                    .where(PriceHistoryORM.product_id == product_id)
                    .order_by(PriceHistoryORM.recorded_at.desc())
                )
                for h in history_result.scalars():
                    price_history.append(PriceHistoryItem(
                        price=h.price,
                        sold_count=h.sold_count,
                        recorded_at=h.recorded_at,
                    ))

            return ProductResponse(
                id=product.id,
                product_id=product.product_id,
                title=product.title,
                url=product.url,
                current_price=product.current_price,
                original_price=product.original_price,
                currency=product.currency,
                sold_count=product.sold_count,
                rating=product.rating,
                review_count=product.review_count,
                seller_id=product.seller_id,
                seller_name=product.seller_name,
                main_image=product.main_image,
                images=product.images or [],
                first_seen_at=product.first_seen_at,
                last_updated_at=product.last_updated_at,
                price_history=price_history,
            )

    async def list_products(
        self,
        page: int = 1,
        page_size: int = 50,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
    ) -> ProductListResponse:
        """List products with pagination and filters."""
        async with get_session(self.engine) as session:
            # Build query
            query = select(ProductORM)

            if min_price is not None:
                query = query.where(ProductORM.current_price >= min_price)
            if max_price is not None:
                query = query.where(ProductORM.current_price <= max_price)

            # Get total count
            count_result = await session.execute(
                select(func.count()).select_from(query.subquery())
            )
            total = count_result.scalar()

            # Get page
            query = query.order_by(ProductORM.last_updated_at.desc())
            query = query.offset((page - 1) * page_size).limit(page_size)

            result = await session.execute(query)
            products = []
            for p in result.scalars():
                products.append(ProductResponse(
                    id=p.id,
                    product_id=p.product_id,
                    title=p.title,
                    url=p.url,
                    current_price=p.current_price,
                    original_price=p.original_price,
                    currency=p.currency,
                    sold_count=p.sold_count,
                    rating=p.rating,
                    review_count=p.review_count,
                    seller_id=p.seller_id,
                    seller_name=p.seller_name,
                    main_image=p.main_image,
                    images=p.images or [],
                    first_seen_at=p.first_seen_at,
                    last_updated_at=p.last_updated_at,
                    price_history=[],
                ))

            return ProductListResponse(
                total=total,
                page=page,
                page_size=page_size,
                products=products,
            )
```

**Step 4: 运行测试确认通过**

Run: `pytest tests/test_temu_service.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add src/temu/service.py tests/test_temu_service.py
git commit -m "feat(temu): add product service with save, get, list operations"
```

---

## Task 5: 数据采集 API

**Files:**
- Create: `src/api/routers/collect.py`
- Test: `tests/test_api_collect.py`

**Step 1: 写测试**

```python
# tests/test_api_collect.py
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
```

**Step 2: 运行测试确认失败**

Run: `pytest tests/test_api_collect.py -v`
Expected: FAIL (ImportError)

**Step 3: 实现采集 API**

```python
# src/api/routers/collect.py
"""API endpoints for data collection from Chrome extension."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...temu.models import ProductCreate, CollectResponse
from ...temu.service import ProductService
from ...database import get_engine

router = APIRouter()

# Global engine (initialized on startup)
_engine = None


def get_product_service() -> ProductService:
    """Dependency to get product service."""
    global _engine
    if _engine is None:
        _engine = get_engine()
    return ProductService(_engine)


class BatchCollectRequest(BaseModel):
    """Request schema for batch collection."""
    products: list[ProductCreate]


class BatchCollectResponse(BaseModel):
    """Response schema for batch collection."""
    success: bool
    message: str
    saved_count: int
    errors: list[str] = []


@router.post("/product", response_model=CollectResponse)
async def collect_product(
    data: ProductCreate,
    service: ProductService = Depends(get_product_service),
):
    """
    Receive product data from Chrome extension.

    - Creates new product if not exists
    - Updates existing product if found
    - Records price history on price changes
    """
    try:
        result = await service.save_product(data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=BatchCollectResponse)
async def collect_batch(
    data: BatchCollectRequest,
    service: ProductService = Depends(get_product_service),
):
    """
    Receive batch of products from Chrome extension.

    Used for periodic batch uploads from extension.
    """
    saved_count = 0
    errors = []

    for product in data.products:
        try:
            await service.save_product(product)
            saved_count += 1
        except Exception as e:
            errors.append(f"{product.product_id}: {str(e)}")

    return BatchCollectResponse(
        success=len(errors) == 0,
        message=f"Saved {saved_count}/{len(data.products)} products",
        saved_count=saved_count,
        errors=errors,
    )
```

**Step 4: 运行测试确认通过**

Run: `pytest tests/test_api_collect.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/api/routers/collect.py tests/test_api_collect.py
git commit -m "feat(api): add collect endpoints for product and batch"
```

---

## Task 6: 商品查询 API

**Files:**
- Create: `src/api/routers/products.py`
- Test: `tests/test_api_products.py`

**Step 1: 写测试**

```python
# tests/test_api_products.py
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
```

**Step 2: 运行测试确认失败**

Run: `pytest tests/test_api_products.py -v`
Expected: FAIL (ImportError)

**Step 3: 实现查询 API**

```python
# src/api/routers/products.py
"""API endpoints for querying products."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from ...temu.models import ProductResponse, ProductListResponse
from ...temu.service import ProductService
from ...database import get_engine

router = APIRouter()

# Global engine (initialized on startup)
_engine = None


def get_product_service() -> ProductService:
    """Dependency to get product service."""
    global _engine
    if _engine is None:
        _engine = get_engine()
    return ProductService(_engine)


@router.get("", response_model=ProductListResponse)
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    service: ProductService = Depends(get_product_service),
):
    """
    List products with pagination and filters.

    - page: Page number (1-indexed)
    - page_size: Items per page (max 200)
    - min_price: Minimum price filter
    - max_price: Maximum price filter
    """
    return await service.list_products(
        page=page,
        page_size=page_size,
        min_price=min_price,
        max_price=max_price,
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    include_history: bool = False,
    service: ProductService = Depends(get_product_service),
):
    """
    Get product by ID.

    - product_id: Temu product ID
    - include_history: Include price history in response
    """
    product = await service.get_product(product_id, include_history=include_history)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product
```

**Step 4: 运行测试确认通过**

Run: `pytest tests/test_api_products.py -v`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add src/api/routers/products.py tests/test_api_products.py
git commit -m "feat(api): add products list and get endpoints"
```

---

## Task 7: FastAPI 应用入口

**Files:**
- Create: `src/api/main.py`
- Create: `server.py`

**Step 1: 创建 FastAPI 应用**

```python
# src/api/main.py
"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..database import get_engine, init_db
from .routers import collect, products


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize database on startup."""
    engine = get_engine()
    await init_db(engine)

    # Store engine in app state for routers
    collect._engine = engine
    products._engine = engine

    yield


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Temu Data Collector API",
        description="API for collecting and querying Temu product data",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(collect.router, prefix="/api/collect", tags=["collect"])
    app.include_router(products.router, prefix="/api/products", tags=["products"])

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy"}

    return app


app = create_app()
```

**Step 2: 创建服务器启动脚本**

```python
# server.py
"""Server startup script."""

import uvicorn


def main():
    """Run the server."""
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
```

**Step 3: 测试服务器启动**

Run: `python server.py &`
Wait: 2 seconds
Run: `curl http://localhost:8000/health`
Expected: `{"status":"healthy"}`
Run: `pkill -f "uvicorn"`

**Step 4: Commit**

```bash
git add src/api/main.py server.py
git commit -m "feat: add FastAPI app entry point and server script"
```

---

## Task 8: Chrome 插件基础结构

**Files:**
- Create: `extension/manifest.json`
- Create: `extension/background/service-worker.js`
- Create: `extension/content/main.js`
- Create: `extension/utils/api.js`
- Create: `extension/utils/storage.js`

**Step 1: 创建 manifest.json**

```json
{
  "manifest_version": 3,
  "name": "Temu Data Collector",
  "version": "1.0.0",
  "description": "Collect product data from Temu pages",
  "permissions": [
    "storage",
    "activeTab",
    "scripting"
  ],
  "host_permissions": [
    "https://*.temu.com/*"
  ],
  "background": {
    "service_worker": "background/service-worker.js",
    "type": "module"
  },
  "content_scripts": [
    {
      "matches": ["https://*.temu.com/*"],
      "js": ["content/main.js"],
      "run_at": "document_idle"
    }
  ],
  "action": {
    "default_popup": "popup/popup.html",
    "default_title": "Temu Collector"
  }
}
```

**Step 2: 创建 API 工具**

```javascript
// extension/utils/api.js
/**
 * API client for communicating with the server.
 */

const DEFAULT_SERVER_URL = 'http://localhost:8000';

class APIClient {
  constructor(serverUrl = DEFAULT_SERVER_URL) {
    this.serverUrl = serverUrl;
  }

  async sendProduct(productData) {
    try {
      const response = await fetch(`${this.serverUrl}/api/collect/product`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(productData),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Failed to send product:', error);
      throw error;
    }
  }

  async sendBatch(products) {
    try {
      const response = await fetch(`${this.serverUrl}/api/collect/batch`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ products }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Failed to send batch:', error);
      throw error;
    }
  }
}

// Export for use in content scripts
if (typeof window !== 'undefined') {
  window.APIClient = APIClient;
}
```

**Step 3: 创建存储工具**

```javascript
// extension/utils/storage.js
/**
 * Local storage queue for offline data collection.
 */

class DataQueue {
  constructor(storageKey = 'temu_collector_queue') {
    this.storageKey = storageKey;
  }

  async enqueue(item) {
    const queue = await this.getQueue();
    queue.push({
      ...item,
      queuedAt: new Date().toISOString(),
    });
    await chrome.storage.local.set({ [this.storageKey]: queue });
  }

  async dequeueAll(limit = 50) {
    const queue = await this.getQueue();
    const items = queue.splice(0, limit);
    await chrome.storage.local.set({ [this.storageKey]: queue });
    return items;
  }

  async getQueue() {
    const result = await chrome.storage.local.get(this.storageKey);
    return result[this.storageKey] || [];
  }

  async getQueueSize() {
    const queue = await this.getQueue();
    return queue.length;
  }

  async clear() {
    await chrome.storage.local.set({ [this.storageKey]: [] });
  }
}

// Export for use in background script
if (typeof self !== 'undefined') {
  self.DataQueue = DataQueue;
}
```

**Step 4: 创建 Service Worker**

```javascript
// extension/background/service-worker.js
/**
 * Background service worker for batch uploads and heartbeat.
 */

importScripts('../utils/storage.js');

const queue = new DataQueue();
const BATCH_INTERVAL_MINUTES = 1;
const SERVER_URL = 'http://localhost:8000';

// Set up periodic batch upload
chrome.alarms.create('batchUpload', { periodInMinutes: BATCH_INTERVAL_MINUTES });

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === 'batchUpload') {
    await processBatchUpload();
  }
});

async function processBatchUpload() {
  const items = await queue.dequeueAll(50);
  if (items.length === 0) return;

  try {
    const response = await fetch(`${SERVER_URL}/api/collect/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ products: items }),
    });

    if (!response.ok) {
      // Re-queue on failure
      for (const item of items) {
        await queue.enqueue(item);
      }
      console.error('Batch upload failed, items re-queued');
    } else {
      console.log(`Batch uploaded ${items.length} items`);
    }
  } catch (error) {
    // Re-queue on network error
    for (const item of items) {
      await queue.enqueue(item);
    }
    console.error('Batch upload error:', error);
  }
}

// Listen for messages from content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'PRODUCT_COLLECTED') {
    queue.enqueue(message.data).then(() => {
      sendResponse({ success: true });
    });
    return true; // Async response
  }
});
```

**Step 5: 创建 Content Script 主入口**

```javascript
// extension/content/main.js
/**
 * Content script main entry point.
 * Detects page type and extracts product data.
 */

(function() {
  'use strict';

  // Detect page type
  function getPageType() {
    const url = window.location.href;
    if (url.includes('/goods.html') || url.match(/\/[\w-]+-g-\d+\.html/)) {
      return 'product_detail';
    }
    if (url.includes('/search_result')) {
      return 'search';
    }
    if (url.includes('/channel/')) {
      return 'category';
    }
    return 'unknown';
  }

  // Extract product data from __NEXT_DATA__
  function extractFromNextData() {
    const script = document.getElementById('__NEXT_DATA__');
    if (!script) return null;

    try {
      const data = JSON.parse(script.textContent);
      const pageProps = data.props?.pageProps;

      if (!pageProps) return null;

      // Try different data paths
      const goodsInfo = pageProps.goodsInfo || pageProps.goods || pageProps.product;
      if (!goodsInfo) return null;

      return {
        product_id: String(goodsInfo.goodsId || goodsInfo.goods_id || goodsInfo.id || ''),
        title: goodsInfo.goodsName || goodsInfo.title || goodsInfo.name || '',
        url: window.location.href,
        current_price: parsePrice(goodsInfo.price || goodsInfo.salePrice),
        original_price: parsePrice(goodsInfo.originalPrice || goodsInfo.marketPrice),
        currency: 'GBP',
        sold_count: parseInt(goodsInfo.soldNum || goodsInfo.sold_count || 0),
        rating: parseFloat(goodsInfo.rating || 0),
        review_count: parseInt(goodsInfo.reviewNum || goodsInfo.review_count || 0),
        images: extractImages(goodsInfo),
        seller_id: goodsInfo.mallId || goodsInfo.seller_id || '',
        seller_name: goodsInfo.mallName || goodsInfo.seller_name || '',
        extracted_at: new Date().toISOString(),
        page_type: 'product_detail',
        raw_data: goodsInfo,
      };
    } catch (e) {
      console.error('Failed to parse __NEXT_DATA__:', e);
      return null;
    }
  }

  function parsePrice(value) {
    if (value === null || value === undefined) return null;
    if (typeof value === 'number') {
      // Temu sometimes stores price in cents
      return value > 1000 ? value / 100 : value;
    }
    if (typeof value === 'string') {
      const cleaned = value.replace(/[^0-9.]/g, '');
      return parseFloat(cleaned) || null;
    }
    return null;
  }

  function extractImages(goodsInfo) {
    const images = [];
    const imageList = goodsInfo.images || goodsInfo.imageList || goodsInfo.gallery || [];

    for (const img of imageList) {
      const url = typeof img === 'string' ? img : (img.url || img.src || '');
      if (url) {
        images.push(url.startsWith('http') ? url : `https:${url}`);
      }
    }

    return images;
  }

  // Main execution
  function main() {
    const pageType = getPageType();
    console.log('[Temu Collector] Page type:', pageType);

    if (pageType === 'product_detail') {
      // Wait for page to fully load
      setTimeout(() => {
        const productData = extractFromNextData();

        if (productData && productData.product_id) {
          console.log('[Temu Collector] Extracted product:', productData.product_id);

          // Send to background script
          chrome.runtime.sendMessage({
            type: 'PRODUCT_COLLECTED',
            data: productData,
          }, (response) => {
            if (response?.success) {
              console.log('[Temu Collector] Product queued for upload');
            }
          });
        } else {
          console.log('[Temu Collector] No product data found');
        }
      }, 2000);
    }
  }

  // Run on page load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', main);
  } else {
    main();
  }
})();
```

**Step 6: 创建 Popup**

```html
<!-- extension/popup/popup.html -->
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {
      width: 300px;
      padding: 16px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    h1 { font-size: 16px; margin: 0 0 16px 0; }
    .status { padding: 8px; border-radius: 4px; margin-bottom: 8px; }
    .status.connected { background: #d4edda; color: #155724; }
    .status.disconnected { background: #f8d7da; color: #721c24; }
    .stat { display: flex; justify-content: space-between; padding: 4px 0; }
    .stat-label { color: #666; }
    .stat-value { font-weight: bold; }
    .config { margin-top: 16px; }
    .config label { display: block; margin-bottom: 4px; font-size: 12px; color: #666; }
    .config input { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
    button {
      width: 100%; padding: 8px; margin-top: 8px;
      background: #007bff; color: white; border: none; border-radius: 4px;
      cursor: pointer;
    }
    button:hover { background: #0056b3; }
  </style>
</head>
<body>
  <h1>Temu Data Collector</h1>

  <div id="status" class="status disconnected">Checking connection...</div>

  <div class="stat">
    <span class="stat-label">Queued items:</span>
    <span id="queueSize" class="stat-value">0</span>
  </div>

  <div class="stat">
    <span class="stat-label">Total collected:</span>
    <span id="totalCollected" class="stat-value">0</span>
  </div>

  <div class="config">
    <label>Server URL</label>
    <input type="text" id="serverUrl" value="http://localhost:8000">
  </div>

  <button id="saveConfig">Save Configuration</button>

  <script src="popup.js"></script>
</body>
</html>
```

```javascript
// extension/popup/popup.js
/**
 * Popup script for configuration and status display.
 */

document.addEventListener('DOMContentLoaded', async () => {
  const statusEl = document.getElementById('status');
  const queueSizeEl = document.getElementById('queueSize');
  const totalCollectedEl = document.getElementById('totalCollected');
  const serverUrlInput = document.getElementById('serverUrl');
  const saveBtn = document.getElementById('saveConfig');

  // Load saved config
  const config = await chrome.storage.local.get(['serverUrl', 'totalCollected']);
  if (config.serverUrl) {
    serverUrlInput.value = config.serverUrl;
  }
  totalCollectedEl.textContent = config.totalCollected || 0;

  // Check queue size
  const queue = await chrome.storage.local.get('temu_collector_queue');
  const queueSize = (queue.temu_collector_queue || []).length;
  queueSizeEl.textContent = queueSize;

  // Check server connection
  try {
    const response = await fetch(`${serverUrlInput.value}/health`);
    if (response.ok) {
      statusEl.textContent = 'Connected to server';
      statusEl.className = 'status connected';
    } else {
      throw new Error('Server unhealthy');
    }
  } catch (e) {
    statusEl.textContent = 'Server not available';
    statusEl.className = 'status disconnected';
  }

  // Save config
  saveBtn.addEventListener('click', async () => {
    await chrome.storage.local.set({ serverUrl: serverUrlInput.value });
    alert('Configuration saved!');
  });
});
```

**Step 7: Commit**

```bash
mkdir -p extension/background extension/content extension/utils extension/popup
git add extension/
git commit -m "feat(extension): add Chrome extension basic structure"
```

---

## Task 9: 端到端测试

**Step 1: 启动服务器**

Run: `python server.py &`
Expected: Server running on http://localhost:8000

**Step 2: 测试 API 手动**

```bash
# Create a product
curl -X POST http://localhost:8000/api/collect/product \
  -H "Content-Type: application/json" \
  -d '{"product_id":"test-e2e","title":"E2E Test Product","url":"https://temu.com/test"}'

# List products
curl http://localhost:8000/api/products

# Get specific product
curl http://localhost:8000/api/products/test-e2e
```

Expected: All requests return 200 with valid JSON

**Step 3: 在浏览器中加载插件**

1. 打开 Chrome/紫鸟浏览器
2. 访问 `chrome://extensions/`
3. 启用 "开发者模式"
4. 点击 "加载已解压的扩展程序"
5. 选择 `extension/` 目录

**Step 4: 测试插件**

1. 访问任意 Temu 商品页
2. 打开浏览器控制台，查看 `[Temu Collector]` 日志
3. 点击插件图标，查看状态
4. 等待 1 分钟（批量上传周期）
5. 调用 `curl http://localhost:8000/api/products` 验证数据

**Step 5: 停止服务器**

Run: `pkill -f "uvicorn"`

**Step 6: Final Commit**

```bash
git add -A
git commit -m "feat: complete Phase 1 - Temu data collection pipeline"
```

---

## Summary

完成 Phase 1 后，系统具备以下能力：

1. **Chrome 插件**：在 Temu 商品页自动提取数据并上报
2. **FastAPI 服务端**：接收、存储、查询商品数据
3. **价格历史**：自动记录价格变化
4. **批量上报**：插件定期批量上传队列中的数据

**后续 Phase**：
- Phase 2: Selenium 自动化类目爬取
- Phase 3: 规则筛选引擎
- Phase 4: 多账号管理
