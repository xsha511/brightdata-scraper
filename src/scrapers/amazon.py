"""Amazon scraper using BrightData Web Scraper API."""

from typing import Any, Optional

from .base import BaseScraper
from ..config import config
from ..models import Product, ProductImage


class AmazonScraper(BaseScraper):
    """
    Scraper for Amazon products using BrightData's Amazon dataset.

    BrightData provides pre-built Amazon scrapers that handle:
    - Product search by keyword
    - Product details by URL or ASIN
    - Price, reviews, images, and more

    Dataset documentation:
    https://docs.brightdata.com/scraping-automation/web-data-apis/web-scraper-api/datasets/amazon
    """

    platform = "amazon"

    def __init__(self, client=None):
        super().__init__(client)
        self.dataset_id = config.amazon_dataset_id

    def build_search_input(self, query: str, **kwargs) -> list[dict]:
        """
        Build input for Amazon search.

        BrightData Amazon dataset accepts:
        - keyword: Search keyword
        - url: Direct product or search URL
        - asin: Amazon product ID
        - pages_to_search: Number of search result pages
        """
        pages = kwargs.get("pages", 1)
        country = kwargs.get("country", "us")

        return [{
            "keyword": query,
            "pages_to_search": pages,
            "country": country,
        }]

    def build_product_input(self, product_id: str, **kwargs) -> list[dict]:
        """
        Build input for Amazon product detail.

        Can use ASIN or full URL.
        """
        country = kwargs.get("country", "us")

        # If it looks like a URL, use url parameter
        if product_id.startswith("http"):
            return [{"url": product_id, "country": country}]

        # Otherwise assume it's an ASIN
        return [{"asin": product_id, "country": country}]

    def parse_api_response(self, data: Any) -> list[Product]:
        """
        Parse BrightData Amazon API response.

        The API returns structured data with fields like:
        - asin, title, brand, price, rating, reviews_count
        - images (list), description, features
        - seller info, availability, etc.
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
            asin = item.get("asin") or item.get("product_id") or ""
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
            main_image = item.get("image") or item.get("main_image")
            if main_image and not any(img.url == main_image for img in images):
                images.insert(0, ProductImage(url=main_image, is_primary=True))
                if len(images) > 1:
                    images[1].is_primary = False

            # Parse price
            price = None
            price_val = item.get("price") or item.get("final_price")
            if price_val:
                if isinstance(price_val, (int, float)):
                    price = float(price_val)
                elif isinstance(price_val, str):
                    # Remove currency symbol and parse
                    price_str = price_val.replace("$", "").replace(",", "").strip()
                    try:
                        price = float(price_str)
                    except ValueError:
                        pass

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
            reviews = item.get("reviews_count") or item.get("ratings_total")
            if reviews:
                try:
                    review_count = int(reviews)
                except (ValueError, TypeError):
                    pass

            return Product(
                platform=self.platform,
                product_id=asin,
                url=item.get("url") or f"https://www.amazon.com/dp/{asin}",
                title=item.get("title") or item.get("name") or f"Amazon Product {asin}",
                price=price,
                original_price=item.get("original_price"),
                currency=item.get("currency", "USD"),
                rating=rating,
                review_count=review_count,
                description=item.get("description") or item.get("product_description"),
                images=images,
                seller=item.get("seller") or item.get("sold_by"),
                category=item.get("category") or item.get("breadcrumbs"),
                in_stock=item.get("availability", "").lower() != "out of stock",
            )
        except Exception as e:
            print(f"Error parsing Amazon item: {e}")
            return None
