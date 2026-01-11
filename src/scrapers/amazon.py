"""Amazon scraper implementation."""

import re
import json
from typing import Optional
from urllib.parse import urlencode, quote_plus

from .base import BaseScraper
from ..models import Product, ProductImage, SearchResult


class AmazonScraper(BaseScraper):
    """Scraper for Amazon products."""

    platform = "amazon"
    BASE_URL = "https://www.amazon.com"

    async def search(self, query: str, page: int = 1) -> SearchResult:
        """Search Amazon for products."""
        params = {
            "k": query,
            "page": page,
        }
        url = f"{self.BASE_URL}/s?{urlencode(params)}"

        html = await self.client.get_html(url)
        products = self._parse_search_results(html)

        return SearchResult(
            query=query,
            platform=self.platform,
            products=products,
            next_page_url=f"{self.BASE_URL}/s?{urlencode({'k': query, 'page': page + 1})}",
        )

    async def get_product(self, product_id: str) -> Optional[Product]:
        """Get Amazon product by ASIN."""
        url = f"{self.BASE_URL}/dp/{product_id}"
        html = await self.client.get_html(url)
        return self.parse_product_html(html, url)

    def _parse_search_results(self, html: str) -> list[Product]:
        """Parse search results page."""
        products = []

        # Extract product cards using regex patterns
        # Pattern for data-asin attribute
        asin_pattern = r'data-asin="([A-Z0-9]{10})"'
        asins = set(re.findall(asin_pattern, html))

        for asin in asins:
            if not asin:
                continue

            # Try to extract basic info from search result
            product = self._extract_search_product(html, asin)
            if product:
                products.append(product)

        return products

    def _extract_search_product(self, html: str, asin: str) -> Optional[Product]:
        """Extract product info from search results."""
        # Find the section containing this ASIN
        pattern = rf'data-asin="{asin}"[^>]*>(.*?)</div>\s*</div>\s*</div>'
        match = re.search(pattern, html, re.DOTALL)

        if not match:
            # Create minimal product with just the ASIN
            return Product(
                platform=self.platform,
                product_id=asin,
                url=f"{self.BASE_URL}/dp/{asin}",
                title=f"Amazon Product {asin}",
            )

        section = match.group(1)

        # Extract title
        title_match = re.search(
            r'<span[^>]*class="[^"]*a-text-normal[^"]*"[^>]*>([^<]+)</span>', section
        )
        title = title_match.group(1).strip() if title_match else f"Amazon Product {asin}"

        # Extract price
        price = None
        price_match = re.search(r'<span class="a-price-whole">([0-9,]+)</span>', section)
        if price_match:
            price_str = price_match.group(1).replace(",", "")
            try:
                price = float(price_str)
            except ValueError:
                pass

        # Extract image
        images = []
        img_match = re.search(r'<img[^>]*src="([^"]+)"[^>]*class="[^"]*s-image[^"]*"', section)
        if img_match:
            images.append(ProductImage(url=img_match.group(1), is_primary=True))

        # Extract rating
        rating = None
        rating_match = re.search(r'<span class="a-icon-alt">([0-9.]+) out of 5', section)
        if rating_match:
            try:
                rating = float(rating_match.group(1))
            except ValueError:
                pass

        return Product(
            platform=self.platform,
            product_id=asin,
            url=f"{self.BASE_URL}/dp/{asin}",
            title=title,
            price=price,
            rating=rating,
            images=images,
        )

    def parse_product_html(self, html: str, url: str) -> Optional[Product]:
        """Parse Amazon product detail page."""
        # Extract ASIN from URL
        asin_match = re.search(r"/dp/([A-Z0-9]{10})", url)
        if not asin_match:
            return None
        asin = asin_match.group(1)

        # Extract title
        title_match = re.search(r'<span[^>]*id="productTitle"[^>]*>([^<]+)</span>', html)
        title = title_match.group(1).strip() if title_match else f"Amazon Product {asin}"

        # Extract price
        price = None
        price_patterns = [
            r'<span class="a-price-whole">([0-9,]+)</span>',
            r'"priceAmount":([0-9.]+)',
            r'<span[^>]*id="priceblock_ourprice"[^>]*>\$([0-9,.]+)</span>',
        ]
        for pattern in price_patterns:
            match = re.search(pattern, html)
            if match:
                price_str = match.group(1).replace(",", "")
                try:
                    price = float(price_str)
                    break
                except ValueError:
                    continue

        # Extract images
        images = self._extract_product_images(html)

        # Extract rating
        rating = None
        rating_match = re.search(r'"acrPopover"[^>]*title="([0-9.]+) out of 5', html)
        if rating_match:
            try:
                rating = float(rating_match.group(1))
            except ValueError:
                pass

        # Extract review count
        review_count = None
        review_match = re.search(r'"acrCustomerReviewText"[^>]*>([0-9,]+) ratings', html)
        if review_match:
            try:
                review_count = int(review_match.group(1).replace(",", ""))
            except ValueError:
                pass

        # Extract description
        description = None
        desc_match = re.search(
            r'<div[^>]*id="productDescription"[^>]*>.*?<p[^>]*>([^<]+)</p>', html, re.DOTALL
        )
        if desc_match:
            description = desc_match.group(1).strip()

        return Product(
            platform=self.platform,
            product_id=asin,
            url=url,
            title=title,
            price=price,
            rating=rating,
            review_count=review_count,
            description=description,
            images=images,
        )

    def _extract_product_images(self, html: str) -> list[ProductImage]:
        """Extract product images from detail page."""
        images = []

        # Try to find image data in JavaScript
        img_data_match = re.search(r"'colorImages':\s*\{\s*'initial':\s*(\[.*?\])\s*\}", html)
        if img_data_match:
            try:
                img_data = json.loads(img_data_match.group(1))
                for i, img in enumerate(img_data):
                    if "hiRes" in img and img["hiRes"]:
                        images.append(ProductImage(url=img["hiRes"], is_primary=i == 0))
                    elif "large" in img and img["large"]:
                        images.append(ProductImage(url=img["large"], is_primary=i == 0))
            except json.JSONDecodeError:
                pass

        # Fallback: extract from img tags
        if not images:
            img_matches = re.findall(
                r'<img[^>]*id="landingImage"[^>]*src="([^"]+)"', html
            )
            for i, img_url in enumerate(img_matches):
                images.append(ProductImage(url=img_url, is_primary=i == 0))

        return images
