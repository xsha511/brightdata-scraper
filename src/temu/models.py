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
