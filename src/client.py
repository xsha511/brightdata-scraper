"""BrightData Web Scraper API client."""

import asyncio
import httpx
from typing import Optional, Any
from enum import Enum

from .config import config, scraper_config


class SnapshotStatus(str, Enum):
    """Snapshot status enum."""
    RUNNING = "running"
    READY = "ready"
    FAILED = "failed"


class BrightDataClient:
    """Client for BrightData Web Scraper API (Datasets API v3)."""

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
        if not self.config.is_configured:
            raise ValueError(
                "BrightData API token not configured. "
                "Set BRIGHTDATA_API_TOKEN in .env file."
            )

        self._client = httpx.AsyncClient(
            timeout=scraper_config.timeout,
            headers=self.config.auth_headers,
        )

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if not self._client:
            raise RuntimeError("Client not started. Use 'async with' or call start() first.")
        return self._client

    async def trigger_collection(
        self,
        dataset_id: str,
        inputs: list[dict],
        notify_url: Optional[str] = None,
        format: str = "json",
    ) -> str:
        """
        Trigger a new data collection (snapshot).

        Args:
            dataset_id: The dataset/scraper ID
            inputs: List of input parameters (URLs, keywords, etc.)
            notify_url: Optional webhook URL for completion notification
            format: Output format (json, csv, etc.)

        Returns:
            snapshot_id: ID of the triggered collection
        """
        url = f"{self.config.api_base_url}/trigger"
        params = {
            "dataset_id": dataset_id,
            "format": format,
            "uncompressed_webhook": "true",
        }
        if notify_url:
            params["notify"] = notify_url

        response = await self.client.post(url, params=params, json=inputs)
        response.raise_for_status()
        result = response.json()
        return result.get("snapshot_id")

    async def get_snapshot_status(self, snapshot_id: str) -> dict:
        """
        Get the status of a snapshot.

        Returns:
            dict with status, progress info, etc.
        """
        url = f"{self.config.api_base_url}/progress/{snapshot_id}"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()

    async def get_snapshot_data(self, snapshot_id: str, format: str = "json") -> Any:
        """
        Get the data from a completed snapshot.

        Args:
            snapshot_id: The snapshot ID
            format: Output format

        Returns:
            The scraped data
        """
        url = f"{self.config.api_base_url}/snapshot/{snapshot_id}"
        params = {"format": format}
        response = await self.client.get(url, params=params)
        response.raise_for_status()

        if format == "json":
            return response.json()
        return response.text

    async def wait_for_snapshot(
        self,
        snapshot_id: str,
        poll_interval: Optional[int] = None,
        max_wait: int = 600,
    ) -> dict:
        """
        Wait for a snapshot to complete.

        Args:
            snapshot_id: The snapshot ID
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait

        Returns:
            Final status dict
        """
        poll_interval = poll_interval or scraper_config.poll_interval
        elapsed = 0

        while elapsed < max_wait:
            status = await self.get_snapshot_status(snapshot_id)
            state = status.get("status")

            if state == SnapshotStatus.READY:
                return status
            elif state == SnapshotStatus.FAILED:
                raise RuntimeError(f"Snapshot failed: {status}")

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(f"Snapshot {snapshot_id} did not complete within {max_wait}s")

    async def collect_and_wait(
        self,
        dataset_id: str,
        inputs: list[dict],
        format: str = "json",
    ) -> Any:
        """
        Trigger collection and wait for results.

        Args:
            dataset_id: The dataset/scraper ID
            inputs: Input parameters
            format: Output format

        Returns:
            The scraped data
        """
        snapshot_id = await self.trigger_collection(dataset_id, inputs, format=format)
        print(f"Triggered snapshot: {snapshot_id}")

        await self.wait_for_snapshot(snapshot_id)
        print(f"Snapshot ready, fetching data...")

        return await self.get_snapshot_data(snapshot_id, format=format)
