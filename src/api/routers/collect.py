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
