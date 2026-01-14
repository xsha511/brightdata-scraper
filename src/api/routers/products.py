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
