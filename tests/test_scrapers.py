"""Tests for scrapers."""

import pytest
from src.models import Product, ProductImage


def test_product_model():
    """Test Product model creation."""
    product = Product(
        platform="amazon",
        product_id="B08TEST123",
        url="https://amazon.com/dp/B08TEST123",
        title="Test Product",
        price=29.99,
        images=[
            ProductImage(url="https://example.com/img1.jpg", is_primary=True),
            ProductImage(url="https://example.com/img2.jpg", is_primary=False),
        ],
    )

    assert product.platform == "amazon"
    assert product.product_id == "B08TEST123"
    assert product.price == 29.99
    assert len(product.images) == 2


def test_product_get_primary_image():
    """Test getting primary image."""
    product = Product(
        platform="temu",
        product_id="12345",
        url="https://temu.com/12345.html",
        title="Test Product",
        images=[
            ProductImage(url="https://example.com/img1.jpg", is_primary=False),
            ProductImage(url="https://example.com/img2.jpg", is_primary=True),
        ],
    )

    primary = product.get_primary_image()
    assert primary is not None
    assert primary.url == "https://example.com/img2.jpg"


def test_product_no_primary_image():
    """Test fallback when no primary image."""
    product = Product(
        platform="amazon",
        product_id="TEST123",
        url="https://amazon.com/dp/TEST123",
        title="Test Product",
        images=[
            ProductImage(url="https://example.com/img1.jpg", is_primary=False),
        ],
    )

    primary = product.get_primary_image()
    assert primary is not None
    assert primary.url == "https://example.com/img1.jpg"
