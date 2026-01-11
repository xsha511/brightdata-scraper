"""BrightData client wrapper using official SDK."""

from typing import Optional, Any

try:
    from brightdata import BrightDataClient as OfficialClient
    HAS_SDK = True
except ImportError:
    HAS_SDK = False
    OfficialClient = None

from .config import config


class BrightDataClient:
    """
    Wrapper around BrightData's official Python SDK.

    The SDK handles:
    - Authentication (auto-loads from BRIGHTDATA_API_TOKEN env var)
    - Rate limiting and retries
    - Response parsing

    Usage:
        async with BrightDataClient() as client:
            results = await client.scrape_amazon("B08TEST123")
    """

    def __init__(self, api_token: Optional[str] = None):
        if not HAS_SDK:
            raise ImportError(
                "brightdata-sdk not installed. Run: pip install brightdata-sdk"
            )

        self._token = api_token or config.api_token
        self._client: Optional[OfficialClient] = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self):
        """Initialize the SDK client."""
        if not self._token:
            raise ValueError(
                "BrightData API token not configured. "
                "Set BRIGHTDATA_API_TOKEN in .env file or pass token to constructor."
            )
        # Official SDK initialization
        self._client = OfficialClient(token=self._token)

    async def close(self):
        """Close the client (if needed)."""
        # Official SDK may not need explicit cleanup
        self._client = None

    @property
    def client(self) -> OfficialClient:
        if not self._client:
            raise RuntimeError("Client not started. Use 'async with' or call start() first.")
        return self._client

    async def scrape_url(self, url: str, dataset_id: Optional[str] = None) -> Any:
        """
        Scrape a single URL.

        Args:
            url: The URL to scrape
            dataset_id: Optional dataset ID for specific scrapers

        Returns:
            Scraped data
        """
        # Use SDK's scrape method
        if hasattr(self.client, 'scrape'):
            return self.client.scrape(url=url, dataset_id=dataset_id)
        # Fallback for different SDK versions
        return self.client.web_scraper.scrape(url=url)

    async def scrape_amazon_product(self, asin: str) -> Any:
        """Scrape Amazon product by ASIN."""
        url = f"https://www.amazon.com/dp/{asin}"
        return await self.scrape_url(url)

    async def scrape_amazon_search(self, query: str) -> Any:
        """Search Amazon products."""
        # Use SDK's Amazon-specific method if available
        if hasattr(self.client, 'amazon'):
            return self.client.amazon.search(query=query)
        # Fallback to URL-based scraping
        url = f"https://www.amazon.com/s?k={query}"
        return await self.scrape_url(url)

    async def scrape_temu_product(self, product_id: str) -> Any:
        """Scrape Temu product by ID."""
        url = f"https://www.temu.com/{product_id}.html"
        return await self.scrape_url(url)

    async def scrape_temu_search(self, query: str) -> Any:
        """Search Temu products."""
        url = f"https://www.temu.com/search_result.html?search_key={query}"
        return await self.scrape_url(url)
