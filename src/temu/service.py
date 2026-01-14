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
