"""Temu scraper using BrightData Web Scraper API."""

from typing import Any, Optional

from .base import BaseScraper
from ..config import config
from ..models import Product, ProductImage


class TemuScraper(BaseScraper):
    """
    Scraper for Temu products using BrightData's Temu dataset.

    BrightData provides pre-built Temu scrapers that handle:
    - Product search by keyword
    - Product details by URL
    - Price, images, and product info

    Note: Check BrightData's dataset marketplace for the latest
    Temu dataset ID and available fields.
    """

    platform = "temu"

    def __init__(self, client=None):
        super().__init__(client)
        self.dataset_id = config.temu_dataset_id

    def build_search_input(self, query: str, **kwargs) -> list[dict]:
        """
        Build input for Temu search.

        BrightData Temu dataset accepts:
        - keyword: Search keyword
        - url: Direct product or search URL
        """
        # Build search URL for Temu
        search_url = f"https://www.temu.com/search_result.html?search_key={query}"

        return [{
            "url": search_url,
            "keyword": query,
        }]

    def build_product_input(self, product_id: str, **kwargs) -> list[dict]:
        """
        Build input for Temu product detail.

        Can use product ID or full URL.
        """
        # If it looks like a URL, use it directly
        if product_id.startswith("http"):
            return [{"url": product_id}]

        # Otherwise build URL from product ID
        url = f"https://www.temu.com/{product_id}.html"
        return [{"url": url}]

    def parse_api_response(self, data: Any) -> list[Product]:
        """
        Parse BrightData Temu API response.

        The API returns structured data with fields like:
        - product_id, title, price
        - images (list)
        - seller info, etc.
        """
        if not data:
            return []

        # Handle both single item and list responses
        items = data if isinstance(data, list) else [data]
        products = []

        for item in items:
            product = self._parse_item(item)
            if product:
                products.append(product)

        return products

    def _parse_item(self, item: dict) -> Optional[Product]:
        """Parse a single item from API response."""
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
                    # Extract ID from URL like /12345.html
                    import re
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
                    # Ensure full URL
                    if not img_url.startswith("http"):
                        img_url = f"https:{img_url}"
                    images.append(ProductImage(url=img_url, is_primary=i == 0))

            # Main image/thumbnail fallback
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
            price = None
            price_val = (
                item.get("price") or
                item.get("sale_price") or
                item.get("current_price")
            )
            if price_val:
                if isinstance(price_val, (int, float)):
                    # Temu sometimes stores price in cents
                    price = float(price_val)
                    if price > 1000:  # Likely in cents
                        price = price / 100
                elif isinstance(price_val, str):
                    price_str = price_val.replace("$", "").replace(",", "").strip()
                    try:
                        price = float(price_str)
                    except ValueError:
                        pass

            # Parse original price
            original_price = None
            orig_val = item.get("original_price") or item.get("list_price")
            if orig_val:
                if isinstance(orig_val, (int, float)):
                    original_price = float(orig_val)
                    if original_price > 1000:
                        original_price = original_price / 100
                elif isinstance(orig_val, str):
                    try:
                        original_price = float(orig_val.replace("$", "").replace(",", ""))
                    except ValueError:
                        pass

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
                original_price=original_price,
                currency="USD",
                rating=item.get("rating"),
                review_count=item.get("reviews_count") or item.get("sold_count"),
                description=item.get("description"),
                images=images,
                seller=item.get("seller") or item.get("shop_name"),
                category=item.get("category"),
                in_stock=True,  # Temu doesn't always provide this
            )
        except Exception as e:
            print(f"Error parsing Temu item: {e}")
            return None
