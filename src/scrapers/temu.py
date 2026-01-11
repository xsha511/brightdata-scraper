"""Temu scraper using BrightData SDK."""

import re
from typing import Any, Optional

from .base import BaseScraper
from ..models import Product, ProductImage, SearchResult


class TemuScraper(BaseScraper):
    """
    Scraper for Temu products using BrightData's official SDK.

    The SDK handles authentication, rate limiting, and response parsing.
    """

    platform = "temu"

    async def search(self, query: str, **kwargs) -> SearchResult:
        """Search Temu for products."""
        data = await self.client.scrape_temu_search(query)
        products = self.parse_response(data)

        return SearchResult(
            query=query,
            platform=self.platform,
            products=products,
        )

    async def get_product(self, product_id: str, **kwargs) -> Optional[Product]:
        """Get Temu product by ID or URL."""
        if product_id.startswith("http"):
            data = await self.client.scrape_url(product_id)
        else:
            data = await self.client.scrape_temu_product(product_id)

        products = self.parse_response(data)
        return products[0] if products else None

    async def get_products_by_urls(self, urls: list[str]) -> list[Product]:
        """Get multiple products by their URLs."""
        all_products = []
        for url in urls:
            data = await self.client.scrape_url(url)
            products = self.parse_response(data)
            all_products.extend(products)
        return all_products

    def parse_response(self, data: Any) -> list[Product]:
        """Parse BrightData SDK response into Product models."""
        if not data:
            return []

        # Handle SDK response format
        items = []

        if hasattr(data, 'data'):
            items = data.data if isinstance(data.data, list) else [data.data]
        elif isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = [data]

        products = []
        for item in items:
            if isinstance(item, dict):
                product = self._parse_item(item)
                if product:
                    products.append(product)

        return products

    def _parse_item(self, item: dict) -> Optional[Product]:
        """Parse a single item from SDK response."""
        try:
            # Extract product ID
            product_id = str(
                item.get("product_id") or
                item.get("goods_id") or
                item.get("id") or
                ""
            )

            # Try to extract from URL if no ID
            if not product_id:
                url = item.get("url", "")
                if url:
                    match = re.search(r"/(\d+)\.html", url)
                    if match:
                        product_id = match.group(1)

            if not product_id:
                return None

            # Parse images
            images = []
            image_data = (
                item.get("images") or
                item.get("image_urls") or
                item.get("gallery") or
                []
            )
            if isinstance(image_data, str):
                image_data = [image_data]

            for i, img in enumerate(image_data):
                img_url = img if isinstance(img, str) else img.get("url", "")
                if img_url:
                    if not img_url.startswith("http"):
                        img_url = f"https:{img_url}"
                    images.append(ProductImage(url=img_url, is_primary=i == 0))

            # Main image fallback
            main_image = (
                item.get("image") or
                item.get("main_image") or
                item.get("thumb") or
                item.get("thumbnail")
            )
            if main_image:
                if not main_image.startswith("http"):
                    main_image = f"https:{main_image}"
                if not any(img.url == main_image for img in images):
                    images.insert(0, ProductImage(url=main_image, is_primary=True))
                    if len(images) > 1:
                        images[1].is_primary = False

            # Parse price
            price = self._parse_price(
                item.get("price") or
                item.get("sale_price") or
                item.get("current_price")
            )

            # Build URL
            url = item.get("url")
            if not url:
                url = f"https://www.temu.com/{product_id}.html"

            return Product(
                platform=self.platform,
                product_id=product_id,
                url=url,
                title=(
                    item.get("title") or
                    item.get("name") or
                    item.get("goods_name") or
                    f"Temu Product {product_id}"
                ),
                price=price,
                original_price=self._parse_price(item.get("original_price") or item.get("list_price")),
                currency="USD",
                rating=item.get("rating"),
                review_count=item.get("reviews_count") or item.get("sold_count"),
                description=item.get("description"),
                images=images,
                seller=item.get("seller") or item.get("shop_name"),
                category=item.get("category"),
                in_stock=True,
            )
        except Exception as e:
            print(f"Error parsing Temu item: {e}")
            return None

    def _parse_price(self, price_val: Any) -> Optional[float]:
        """Parse price from various formats."""
        if price_val is None:
            return None

        if isinstance(price_val, (int, float)):
            price = float(price_val)
            # Temu sometimes stores price in cents
            if price > 1000:
                price = price / 100
            return price

        if isinstance(price_val, str):
            price_str = price_val.replace("$", "").replace(",", "").strip()
            try:
                return float(price_str)
            except ValueError:
                return None

        return None
