"""Configuration management."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class BrightDataConfig:
    """BrightData SDK configuration.

    The official SDK automatically loads API token from:
    1. BRIGHTDATA_API_TOKEN environment variable
    2. .env file

    Get your API token from BrightData dashboard:
    Account Settings -> API Key
    """

    # API token (SDK auto-loads from env, but we keep for reference)
    api_token: str = os.getenv("BRIGHTDATA_API_TOKEN", "")

    @property
    def is_configured(self) -> bool:
        """Check if BrightData API is properly configured."""
        return bool(self.api_token)


@dataclass
class ScraperConfig:
    """General scraper configuration."""

    data_dir: str = "data"
    images_dir: str = "data/images"
    concurrent_requests: int = 5


config = BrightDataConfig()
scraper_config = ScraperConfig()
