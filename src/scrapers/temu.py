"""Temu scraper implementation."""

import re
import json
from typing import Optional
from urllib.parse import urlencode, quote_plus

from .base import BaseScraper
from ..models import Product, ProductImage, SearchResult


class TemuScraper(BaseScraper):
    """Scraper for Temu products."""

    platform = "temu"
    BASE_URL = "https://www.temu.com"

    async def search(self, query: str, page: int = 1) -> SearchResult:
        """Search Temu for products."""
        # Temu uses a different URL structure for search
        encoded_query = quote_plus(query)
        url = f"{self.BASE_URL}/search_result.html?search_key={encoded_query}&page={page}"

        html = await self.client.get_html(url)
        products = self._parse_search_results(html)

        return SearchResult(
            query=query,
            platform=self.platform,
            products=products,
            next_page_url=f"{self.BASE_URL}/search_result.html?search_key={encoded_query}&page={page + 1}",
        )

    async def get_product(self, product_id: str) -> Optional[Product]:
        """Get Temu product by ID."""
        # Temu product URLs follow pattern: /goods_id.html
        url = f"{self.BASE_URL}/{product_id}.html"
        html = await self.client.get_html(url)
        return self.parse_product_html(html, url)

    def _parse_search_results(self, html: str) -> list[Product]:
        """Parse Temu search results page."""
        products = []

        # Temu stores product data in JSON within the page
        # Look for the SSR data or product listings
        json_data = self._extract_json_data(html)

        if json_data:
            products = self._parse_json_products(json_data)
        else:
            # Fallback to HTML parsing
            products = self._parse_html_products(html)

        return products

    def _extract_json_data(self, html: str) -> Optional[dict]:
        """Extract JSON data from Temu page."""
        # Temu embeds product data in script tags
        patterns = [
            r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
            r'<script[^>]*id="__NEXT_DATA__"[^>]*>({.*?})</script>',
            r'"goodsList"\s*:\s*(\[.*?\])',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue

        return None

    def _parse_json_products(self, data: dict) -> list[Product]:
        """Parse products from JSON data."""
        products = []

        # Navigate through possible data structures
        goods_list = []
        if isinstance(data, list):
            goods_list = data
        elif "goodsList" in data:
            goods_list = data["goodsList"]
        elif "pageProps" in data:
            props = data["pageProps"]
            if "goodsList" in props:
                goods_list = props["goodsList"]
            elif "searchResult" in props:
                goods_list = props["searchResult"].get("goodsList", [])

        for item in goods_list:
            product = self._json_item_to_product(item)
            if product:
                products.append(product)

        return products

    def _json_item_to_product(self, item: dict) -> Optional[Product]:
        """Convert JSON item to Product model."""
        try:
            product_id = str(item.get("goods_id") or item.get("goodsId") or "")
            if not product_id:
                return None

            # Extract title
            title = item.get("goods_name") or item.get("goodsName") or f"Temu Product {product_id}"

            # Extract price
            price = None
            price_val = item.get("price") or item.get("salePrice")
            if price_val:
                if isinstance(price_val, (int, float)):
                    price = float(price_val) / 100  # Temu often stores cents
                elif isinstance(price_val, str):
                    price = float(price_val.replace("$", "").replace(",", ""))

            # Extract images
            images = []
            img_url = item.get("thumb") or item.get("image") or item.get("goods_thumb")
            if img_url:
                # Ensure full URL
                if not img_url.startswith("http"):
                    img_url = f"https:{img_url}"
                images.append(ProductImage(url=img_url, is_primary=True))

            # Extract gallery images
            gallery = item.get("gallery") or item.get("images") or []
            for i, img in enumerate(gallery):
                img_url = img if isinstance(img, str) else img.get("url")
                if img_url:
                    if not img_url.startswith("http"):
                        img_url = f"https:{img_url}"
                    images.append(ProductImage(url=img_url, is_primary=len(images) == 0))

            return Product(
                platform=self.platform,
                product_id=product_id,
                url=f"{self.BASE_URL}/{product_id}.html",
                title=title,
                price=price,
                images=images,
            )
        except Exception:
            return None

    def _parse_html_products(self, html: str) -> list[Product]:
        """Fallback HTML parsing for Temu products."""
        products = []

        # Look for product cards in HTML
        # Pattern for product links
        product_pattern = r'href="[^"]*?/(\d+)\.html"[^>]*>.*?<img[^>]*src="([^"]+)"[^>]*>'
        matches = re.findall(product_pattern, html, re.DOTALL)

        seen_ids = set()
        for product_id, img_url in matches:
            if product_id in seen_ids:
                continue
            seen_ids.add(product_id)

            # Clean image URL
            if not img_url.startswith("http"):
                img_url = f"https:{img_url}"

            products.append(
                Product(
                    platform=self.platform,
                    product_id=product_id,
                    url=f"{self.BASE_URL}/{product_id}.html",
                    title=f"Temu Product {product_id}",
                    images=[ProductImage(url=img_url, is_primary=True)],
                )
            )

        return products

    def parse_product_html(self, html: str, url: str) -> Optional[Product]:
        """Parse Temu product detail page."""
        # Extract product ID from URL
        id_match = re.search(r"/(\d+)\.html", url)
        if not id_match:
            return None
        product_id = id_match.group(1)

        # Try to get structured data first
        json_data = self._extract_json_data(html)

        if json_data:
            # Look for product detail in JSON
            product_data = None
            if "goodsDetail" in json_data:
                product_data = json_data["goodsDetail"]
            elif "pageProps" in json_data:
                product_data = json_data["pageProps"].get("goodsDetail")

            if product_data:
                return self._json_item_to_product(product_data)

        # Fallback to HTML parsing
        # Extract title
        title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        title = title_match.group(1).strip() if title_match else f"Temu Product {product_id}"

        # Extract price
        price = None
        price_match = re.search(r'\$([0-9,.]+)', html)
        if price_match:
            try:
                price = float(price_match.group(1).replace(",", ""))
            except ValueError:
                pass

        # Extract images
        images = []
        img_matches = re.findall(r'<img[^>]*src="([^"]*temu[^"]*)"[^>]*>', html)
        for i, img_url in enumerate(img_matches[:10]):  # Limit to 10 images
            if not img_url.startswith("http"):
                img_url = f"https:{img_url}"
            images.append(ProductImage(url=img_url, is_primary=i == 0))

        return Product(
            platform=self.platform,
            product_id=product_id,
            url=url,
            title=title,
            price=price,
            images=images,
        )
