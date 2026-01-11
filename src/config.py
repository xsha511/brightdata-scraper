"""Configuration management."""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class BrightDataConfig:
    """BrightData Web Scraper API configuration."""

    # Web Scraper API token (Bearer token)
    api_token: str = os.getenv("BRIGHTDATA_API_TOKEN", "")

    # Dataset IDs for different platforms
    # These are BrightData's pre-built scraper IDs
    amazon_dataset_id: str = os.getenv(
        "BRIGHTDATA_AMAZON_DATASET_ID",
        "gd_l7q7dkf244hwjntr0"  # Amazon Products dataset
    )
    temu_dataset_id: str = os.getenv(
        "BRIGHTDATA_TEMU_DATASET_ID",
        "gd_lz6e6n1k2pgo51vy9d"  # Temu Products dataset (if available)
    )

    # API endpoints
    api_base_url: str = "https://api.brightdata.com/datasets/v3"

    @property
    def is_configured(self) -> bool:
        """Check if BrightData API is properly configured."""
        return bool(self.api_token)

    @property
    def auth_headers(self) -> dict:
        """Get authentication headers for API requests."""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }


@dataclass
class ScraperConfig:
    """General scraper configuration."""

    data_dir: str = "data"
    images_dir: str = "data/images"
    max_retries: int = 3
    timeout: int = 120  # API requests may take longer
    concurrent_requests: int = 5
    poll_interval: int = 10  # Seconds between status checks


config = BrightDataConfig()
scraper_config = ScraperConfig()
