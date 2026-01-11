#!/usr/bin/env python3
"""
Main script demonstrating BrightData Web Scraper API usage.

This script shows how to:
1. Search products on Amazon and Temu
2. Get product details
3. Download product images
"""

import asyncio
import json
from pathlib import Path

from src.scrapers import AmazonScraper, TemuScraper
from src.utils import ImageDownloader


async def scrape_amazon(query: str, download_images: bool = True):
    """Scrape Amazon products using BrightData API."""
    print(f"\n{'='*50}")
    print(f"Searching Amazon for: {query}")
    print("=" * 50)

    async with AmazonScraper() as scraper:
        # Search products
        results = await scraper.search(query, pages=1, country="us")

        print(f"Found {len(results.products)} products")

        for product in results.products[:5]:
            print(f"\n- {product.title[:60]}...")
            print(f"  ID: {product.product_id}")
            print(f"  Price: ${product.price}" if product.price else "  Price: N/A")
            print(f"  Rating: {product.rating}" if product.rating else "  Rating: N/A")
            print(f"  Images: {len(product.images)}")

        # Download images
        if download_images and results.products:
            print("\nDownloading images...")
            async with ImageDownloader() as downloader:
                updated = await downloader.download_all(results.products[:5])
                for p in updated:
                    downloaded = [img for img in p.images if img.local_path]
                    print(f"  {p.product_id}: {len(downloaded)} images downloaded")

        return results


async def scrape_temu(query: str, download_images: bool = True):
    """Scrape Temu products using BrightData API."""
    print(f"\n{'='*50}")
    print(f"Searching Temu for: {query}")
    print("=" * 50)

    async with TemuScraper() as scraper:
        # Search products
        results = await scraper.search(query)

        print(f"Found {len(results.products)} products")

        for product in results.products[:5]:
            print(f"\n- {product.title[:60]}...")
            print(f"  ID: {product.product_id}")
            print(f"  Price: ${product.price}" if product.price else "  Price: N/A")
            print(f"  Images: {len(product.images)}")

        # Download images
        if download_images and results.products:
            print("\nDownloading images...")
            async with ImageDownloader() as downloader:
                updated = await downloader.download_all(results.products[:5])
                for p in updated:
                    downloaded = [img for img in p.images if img.local_path]
                    print(f"  {p.product_id}: {len(downloaded)} images downloaded")

        return results


async def get_product_by_asin(asin: str):
    """Get a single Amazon product by ASIN."""
    print(f"\n{'='*50}")
    print(f"Getting Amazon product: {asin}")
    print("=" * 50)

    async with AmazonScraper() as scraper:
        product = await scraper.get_product(asin)

        if product:
            print(f"Title: {product.title}")
            print(f"Price: ${product.price}" if product.price else "Price: N/A")
            print(f"Rating: {product.rating}/5 ({product.review_count} reviews)")
            print(f"Images: {len(product.images)}")
            if product.description:
                print(f"Description: {product.description[:200]}...")
        else:
            print("Product not found")

        return product


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

    print("\n" + "=" * 60)
    print("BrightData Web Scraper API Demo")
    print("=" * 60)

    # Scrape both platforms
    try:
        amazon_results = await scrape_amazon(query, download_images=True)
        await save_results(amazon_results, "amazon_results.json")
    except Exception as e:
        print(f"Amazon scraping failed: {e}")

    try:
        temu_results = await scrape_temu(query, download_images=True)
        await save_results(temu_results, "temu_results.json")
    except Exception as e:
        print(f"Temu scraping failed: {e}")

    # Example: Get single product by ASIN
    # await get_product_by_asin("B0CHWRXH8B")

    print("\n" + "=" * 60)
    print("Scraping complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
