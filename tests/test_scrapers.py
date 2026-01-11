"""Tests for scrapers."""

import pytest
from src.models import Product, ProductImage, SearchResult
from src.scrapers.amazon import AmazonScraper
from src.scrapers.temu import TemuScraper


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


def test_search_result_model():
    """Test SearchResult model."""
    result = SearchResult(
        query="test query",
        platform="amazon",
        products=[
            Product(
                platform="amazon",
                product_id="TEST1",
                url="https://amazon.com/dp/TEST1",
                title="Product 1",
            ),
            Product(
                platform="amazon",
                product_id="TEST2",
                url="https://amazon.com/dp/TEST2",
                title="Product 2",
            ),
        ],
    )

    assert result.query == "test query"
    assert result.platform == "amazon"
    assert len(result.products) == 2


def test_amazon_scraper_build_search_input():
    """Test Amazon scraper input building."""
    scraper = AmazonScraper.__new__(AmazonScraper)
    scraper._client = None
    scraper._own_client = True

    inputs = scraper.build_search_input("headphones", pages=2, country="uk")

    assert len(inputs) == 1
    assert inputs[0]["keyword"] == "headphones"
    assert inputs[0]["pages_to_search"] == 2
    assert inputs[0]["country"] == "uk"


def test_amazon_scraper_build_product_input_asin():
    """Test Amazon scraper product input with ASIN."""
    scraper = AmazonScraper.__new__(AmazonScraper)
    scraper._client = None
    scraper._own_client = True

    inputs = scraper.build_product_input("B08TEST123")

    assert len(inputs) == 1
    assert inputs[0]["asin"] == "B08TEST123"


def test_amazon_scraper_build_product_input_url():
    """Test Amazon scraper product input with URL."""
    scraper = AmazonScraper.__new__(AmazonScraper)
    scraper._client = None
    scraper._own_client = True

    url = "https://amazon.com/dp/B08TEST123"
    inputs = scraper.build_product_input(url)

    assert len(inputs) == 1
    assert inputs[0]["url"] == url


def test_amazon_scraper_parse_api_response():
    """Test Amazon API response parsing."""
    scraper = AmazonScraper.__new__(AmazonScraper)
    scraper._client = None
    scraper._own_client = True
    scraper.platform = "amazon"

    api_response = [
        {
            "asin": "B08TEST123",
            "title": "Test Headphones",
            "price": 49.99,
            "rating": 4.5,
            "reviews_count": 1234,
            "images": ["https://example.com/img1.jpg", "https://example.com/img2.jpg"],
            "url": "https://amazon.com/dp/B08TEST123",
        }
    ]

    products = scraper.parse_api_response(api_response)

    assert len(products) == 1
    assert products[0].product_id == "B08TEST123"
    assert products[0].title == "Test Headphones"
    assert products[0].price == 49.99
    assert products[0].rating == 4.5
    assert products[0].review_count == 1234
    assert len(products[0].images) == 2


def test_temu_scraper_build_search_input():
    """Test Temu scraper input building."""
    scraper = TemuScraper.__new__(TemuScraper)
    scraper._client = None
    scraper._own_client = True

    inputs = scraper.build_search_input("phone case")

    assert len(inputs) == 1
    assert inputs[0]["keyword"] == "phone case"
    assert "search_result.html" in inputs[0]["url"]


def test_temu_scraper_parse_api_response():
    """Test Temu API response parsing."""
    scraper = TemuScraper.__new__(TemuScraper)
    scraper._client = None
    scraper._own_client = True
    scraper.platform = "temu"

    api_response = [
        {
            "product_id": "12345",
            "title": "Test Phone Case",
            "price": 5.99,
            "images": ["https://temu.com/img1.jpg"],
        }
    ]

    products = scraper.parse_api_response(api_response)

    assert len(products) == 1
    assert products[0].product_id == "12345"
    assert products[0].title == "Test Phone Case"
    assert products[0].price == 5.99
