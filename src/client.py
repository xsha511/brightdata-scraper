"""BrightData HTTP client."""

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Optional

from .config import config, scraper_config


class BrightDataClient:
    """HTTP client using BrightData proxy."""

    def __init__(self):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self):
        """Initialize the HTTP client."""
        if self.config.is_configured:
            # Use BrightData proxy
            self._client = httpx.AsyncClient(
                proxy=self.config.proxy_url,
                timeout=scraper_config.timeout,
                follow_redirects=True,
                headers=self._get_default_headers(),
            )
        else:
            # Fallback to direct connection (for testing)
            self._client = httpx.AsyncClient(
                timeout=scraper_config.timeout,
                follow_redirects=True,
                headers=self._get_default_headers(),
            )

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_default_headers(self) -> dict:
        """Get default request headers."""
        return {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        }

    @retry(
        stop=stop_after_attempt(scraper_config.max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def get(self, url: str, headers: Optional[dict] = None) -> httpx.Response:
        """Make a GET request through BrightData proxy."""
        if not self._client:
            raise RuntimeError("Client not started. Use 'async with' or call start() first.")

        merged_headers = {**self._get_default_headers(), **(headers or {})}
        response = await self._client.get(url, headers=merged_headers)
        response.raise_for_status()
        return response

    async def get_html(self, url: str) -> str:
        """Get HTML content from URL."""
        response = await self.get(url)
        return response.text

    async def get_json(self, url: str) -> dict:
        """Get JSON content from URL."""
        response = await self.get(url, headers={"Accept": "application/json"})
        return response.json()
