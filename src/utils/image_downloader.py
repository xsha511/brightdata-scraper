"""Image downloader utility."""

import asyncio
import hashlib
import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import aiofiles
import httpx

from ..config import scraper_config
from ..models import Product, ProductImage


class ImageDownloader:
    """Download and manage product images."""

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir or scraper_config.images_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=30, follow_redirects=True)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if not self._client:
            raise RuntimeError("Downloader not initialized. Use 'async with' context manager.")
        return self._client

    def _get_filename(self, url: str, product_id: str, index: int) -> str:
        """Generate filename for image."""
        # Get extension from URL
        parsed = urlparse(url)
        path = parsed.path
        ext = os.path.splitext(path)[1] or ".jpg"

        # Clean extension
        ext = ext.split("?")[0]
        if not ext.startswith("."):
            ext = f".{ext}"
        if ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            ext = ".jpg"

        # Generate filename
        return f"{product_id}_{index}{ext}"

    async def download_image(
        self, url: str, product_id: str, index: int = 0
    ) -> Optional[str]:
        """Download a single image."""
        try:
            filename = self._get_filename(url, product_id, index)
            filepath = self.output_dir / filename

            # Skip if already exists
            if filepath.exists():
                return str(filepath)

            response = await self.client.get(url)
            response.raise_for_status()

            async with aiofiles.open(filepath, "wb") as f:
                await f.write(response.content)

            return str(filepath)
        except Exception as e:
            print(f"Failed to download {url}: {e}")
            return None

    async def download_product_images(
        self, product: Product, max_images: int = 5
    ) -> Product:
        """Download all images for a product."""
        tasks = []
        images_to_download = product.images[:max_images]

        for i, image in enumerate(images_to_download):
            task = self.download_image(image.url, product.product_id, i)
            tasks.append((i, task))

        # Download concurrently
        results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)

        # Update product images with local paths
        for i, result in enumerate(results):
            if isinstance(result, str) and i < len(product.images):
                product.images[i].local_path = result

        return product

    async def download_all(
        self, products: list[Product], max_images_per_product: int = 5
    ) -> list[Product]:
        """Download images for multiple products."""
        tasks = [
            self.download_product_images(p, max_images_per_product) for p in products
        ]

        # Process in batches to avoid overwhelming the server
        batch_size = scraper_config.concurrent_requests
        results = []

        for i in range(0, len(tasks), batch_size):
            batch = tasks[i : i + batch_size]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            for result in batch_results:
                if isinstance(result, Product):
                    results.append(result)
                elif isinstance(result, Exception):
                    print(f"Error downloading images: {result}")

        return results
