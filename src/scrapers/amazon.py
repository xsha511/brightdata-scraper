"""Amazon scraper using BrightData SDK."""

from typing import Any, Optional

from .base import BaseScraper
from ..models import Product, ProductImage, SearchResult


class AmazonScraper(BaseScraper):
    """
    Scraper for Amazon products using BrightData's official SDK.

    The SDK handles authentication, rate limiting, and response parsing.
    """

    platform = "amazon"

    async def search(self, query: str, **kwargs) -> SearchResult:
        """Search Amazon for products."""
        data = await self.client.scrape_amazon_search(query)
        products = self.parse_response(data)

        return SearchResult(
            query=query,
            platform=self.platform,
            products=products,
        )

    async def get_product(self, product_id: str, **kwargs) -> Optional[Product]:
        """Get Amazon product by ASIN or URL."""
        # If it's a URL, extract ASIN or use directly
        if product_id.startswith("http"):
            data = await self.client.scrape_url(product_id)
        else:
            data = await self.client.scrape_amazon_product(product_id)

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
        # The SDK may return data in different formats
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
            # Extract ASIN
            asin = (
                item.get("asin") or
                item.get("product_id") or
                item.get("id") or
                ""
            )
            if not asin:
                return None

            # Parse images
            images = []
            image_data = item.get("images") or item.get("image_urls") or []
            if isinstance(image_data, str):
                image_data = [image_data]

            for i, img in enumerate(image_data):
                img_url = img if isinstance(img, str) else img.get("url", "")
                if img_url:
                    images.append(ProductImage(url=img_url, is_primary=i == 0))

            # Main image fallback
            main_image = item.get("image") or item.get("main_image") or item.get("thumbnail")
            if main_image and not any(img.url == main_image for img in images):
                images.insert(0, ProductImage(url=main_image, is_primary=True))
                if len(images) > 1:
                    images[1].is_primary = False

            # Parse price
            price = self._parse_price(item.get("price") or item.get("final_price"))

            # Parse rating
            rating = None
            rating_val = item.get("rating") or item.get("stars")
            if rating_val:
                try:
                    rating = float(rating_val)
                except (ValueError, TypeError):
                    pass

            # Parse review count
            review_count = None
            reviews = item.get("reviews_count") or item.get("ratings_total") or item.get("reviews")
            if reviews:
                try:
                    review_count = int(reviews)
                except (ValueError, TypeError):
                    pass

            return Product(
                platform=self.platform,
                product_id=str(asin),
                url=item.get("url") or f"https://www.amazon.com/dp/{asin}",
                title=item.get("title") or item.get("name") or f"Amazon Product {asin}",
                price=price,
                original_price=self._parse_price(item.get("original_price")),
                currency=item.get("currency", "USD"),
                rating=rating,
                review_count=review_count,
                description=item.get("description") or item.get("product_description"),
                images=images,
                seller=item.get("seller") or item.get("sold_by"),
                category=item.get("category") or item.get("breadcrumbs"),
                in_stock=str(item.get("availability", "")).lower() != "out of stock",
            )
        except Exception as e:
            print(f"Error parsing Amazon item: {e}")
            return None

    def _parse_price(self, price_val: Any) -> Optional[float]:
        """Parse price from various formats."""
        if price_val is None:
            return None

        if isinstance(price_val, (int, float)):
            return float(price_val)

        if isinstance(price_val, str):
            price_str = price_val.replace("$", "").replace(",", "").strip()
            try:
                return float(price_str)
            except ValueError:
                return None

        return None
