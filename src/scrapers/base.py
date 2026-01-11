"""Base scraper class for BrightData Web Scraper API."""

from abc import ABC, abstractmethod
from typing import Optional, Any

from ..client import BrightDataClient
from ..models import Product, SearchResult


class BaseScraper(ABC):
    """Abstract base class for platform scrapers using BrightData API."""

    platform: str = "unknown"
    dataset_id: str = ""

    def __init__(self, client: Optional[BrightDataClient] = None):
        self._client = client
        self._own_client = client is None

    async def __aenter__(self):
        if self._own_client:
            self._client = BrightDataClient()
            await self._client.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._own_client and self._client:
            await self._client.close()

    @property
    def client(self) -> BrightDataClient:
        if not self._client:
            raise RuntimeError("Scraper not initialized. Use 'async with' context manager.")
        return self._client

    @abstractmethod
    def build_search_input(self, query: str, **kwargs) -> list[dict]:
        """Build input payload for search request."""
        pass

    @abstractmethod
    def build_product_input(self, product_id: str, **kwargs) -> list[dict]:
        """Build input payload for product detail request."""
        pass

    @abstractmethod
    def parse_api_response(self, data: Any) -> list[Product]:
        """Parse API response into Product models."""
        pass

    async def search(self, query: str, **kwargs) -> SearchResult:
        """Search for products using BrightData API."""
        inputs = self.build_search_input(query, **kwargs)
        data = await self.client.collect_and_wait(self.dataset_id, inputs)
        products = self.parse_api_response(data)

        return SearchResult(
            query=query,
            platform=self.platform,
            products=products,
        )

    async def get_product(self, product_id: str, **kwargs) -> Optional[Product]:
        """Get product details using BrightData API."""
        inputs = self.build_product_input(product_id, **kwargs)
        data = await self.client.collect_and_wait(self.dataset_id, inputs)
        products = self.parse_api_response(data)
        return products[0] if products else None

    async def get_products_by_urls(self, urls: list[str]) -> list[Product]:
        """Get multiple products by their URLs."""
        inputs = [{"url": url} for url in urls]
        data = await self.client.collect_and_wait(self.dataset_id, inputs)
        return self.parse_api_response(data)
