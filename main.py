#!/usr/bin/env python3
"""Main script demonstrating scraper usage."""

import asyncio
import json
from pathlib import Path

from src.scrapers import AmazonScraper, TemuScraper
from src.utils import ImageDownloader


async def scrape_amazon(query: str, download_images: bool = True):
    """Scrape Amazon products."""
    print(f"\n{'='*50}")
    print(f"Searching Amazon for: {query}")
    print("=" * 50)

    async with AmazonScraper() as scraper:
        results = await scraper.search(query)

        print(f"Found {len(results.products)} products")

        for product in results.products[:5]:  # Limit to 5 for demo
            print(f"\n- {product.title[:60]}...")
            print(f"  ID: {product.product_id}")
            print(f"  Price: ${product.price}" if product.price else "  Price: N/A")
            print(f"  Rating: {product.rating}" if product.rating else "  Rating: N/A")
            print(f"  Images: {len(product.images)}")

        if download_images and results.products:
            print("\nDownloading images...")
            async with ImageDownloader() as downloader:
                updated = await downloader.download_all(results.products[:5])
                for p in updated:
                    downloaded = [img for img in p.images if img.local_path]
                    print(f"  {p.product_id}: {len(downloaded)} images downloaded")

        return results


async def scrape_temu(query: str, download_images: bool = True):
    """Scrape Temu products."""
    print(f"\n{'='*50}")
    print(f"Searching Temu for: {query}")
    print("=" * 50)

    async with TemuScraper() as scraper:
        results = await scraper.search(query)

        print(f"Found {len(results.products)} products")

        for product in results.products[:5]:  # Limit to 5 for demo
            print(f"\n- {product.title[:60]}...")
            print(f"  ID: {product.product_id}")
            print(f"  Price: ${product.price}" if product.price else "  Price: N/A")
            print(f"  Images: {len(product.images)}")

        if download_images and results.products:
            print("\nDownloading images...")
            async with ImageDownloader() as downloader:
                updated = await downloader.download_all(results.products[:5])
                for p in updated:
                    downloaded = [img for img in p.images if img.local_path]
                    print(f"  {p.product_id}: {len(downloaded)} images downloaded")

        return results


async def save_results(results, filename: str):
    """Save results to JSON file."""
    output_path = Path("data") / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "query": results.query,
        "platform": results.platform,
        "total_products": len(results.products),
        "products": [p.model_dump() for p in results.products],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to: {output_path}")


async def main():
    """Main entry point."""
    # Example search query
    query = "wireless headphones"

    # Scrape both platforms
    amazon_results = await scrape_amazon(query, download_images=True)
    temu_results = await scrape_temu(query, download_images=True)

    # Save results
    await save_results(amazon_results, "amazon_results.json")
    await save_results(temu_results, "temu_results.json")

    print("\n" + "=" * 50)
    print("Scraping complete!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
