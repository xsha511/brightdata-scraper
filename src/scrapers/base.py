"""Base scraper class."""

from abc import ABC, abstractmethod
from typing import Optional

from ..client import BrightDataClient
from ..models import Product, SearchResult


class BaseScraper(ABC):
    """Abstract base class for platform scrapers."""

    platform: str = "unknown"

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
    async def search(self, query: str, page: int = 1) -> SearchResult:
        """Search for products."""
        pass

    @abstractmethod
    async def get_product(self, product_id: str) -> Optional[Product]:
        """Get product details by ID."""
        pass

    @abstractmethod
    def parse_product_html(self, html: str, url: str) -> Optional[Product]:
        """Parse product from HTML."""
        pass
