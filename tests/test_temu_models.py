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
