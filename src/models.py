"""Data models for scraped products."""

from typing import Optional
from pydantic import BaseModel, Field


class ProductImage(BaseModel):
    """Product image data."""

    url: str
    alt: Optional[str] = None
    is_primary: bool = False
    local_path: Optional[str] = None


class Product(BaseModel):
    """Product data model."""

    platform: str = Field(..., description="Source platform (amazon/temu)")
    product_id: str = Field(..., description="Platform-specific product ID")
    url: str = Field(..., description="Product page URL")
    title: str = Field(..., description="Product title")
    price: Optional[float] = Field(None, description="Current price")
    original_price: Optional[float] = Field(None, description="Original price before discount")
    currency: str = Field(default="USD", description="Currency code")
    rating: Optional[float] = Field(None, ge=0, le=5, description="Product rating")
    review_count: Optional[int] = Field(None, ge=0, description="Number of reviews")
    description: Optional[str] = Field(None, description="Product description")
    images: list[ProductImage] = Field(default_factory=list, description="Product images")

    # Additional metadata
    seller: Optional[str] = None
    category: Optional[str] = None
    in_stock: bool = True

    def get_primary_image(self) -> Optional[ProductImage]:
        """Get the primary product image."""
        for img in self.images:
            if img.is_primary:
                return img
        return self.images[0] if self.images else None


class SearchResult(BaseModel):
    """Search results container."""

    query: str
    platform: str
    total_results: Optional[int] = None
    products: list[Product] = Field(default_factory=list)
    next_page_url: Optional[str] = None
