"""Configuration management."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class BrightDataConfig:
    """BrightData configuration."""

    # Proxy authentication
    username: str = os.getenv("BRIGHTDATA_USERNAME", "")
    password: str = os.getenv("BRIGHTDATA_PASSWORD", "")
    host: str = os.getenv("BRIGHTDATA_HOST", "brd.superproxy.io")
    port: int = int(os.getenv("BRIGHTDATA_PORT", "22225"))

    # Zone-based auth (alternative)
    zone: str = os.getenv("BRIGHTDATA_ZONE", "")
    customer_id: str = os.getenv("BRIGHTDATA_CUSTOMER_ID", "")

    # Web Scraper API
    scraper_api_key: str = os.getenv("BRIGHTDATA_SCRAPER_API_KEY", "")

    @property
    def proxy_url(self) -> str:
        """Get proxy URL for requests."""
        if self.zone and self.customer_id:
            auth = f"brd-customer-{self.customer_id}-zone-{self.zone}"
            return f"http://{auth}:{self.password}@{self.host}:{self.port}"
        return f"http://{self.username}:{self.password}@{self.host}:{self.port}"

    @property
    def is_configured(self) -> bool:
        """Check if BrightData is properly configured."""
        has_proxy = bool(self.username and self.password)
        has_zone = bool(self.zone and self.customer_id and self.password)
        has_api = bool(self.scraper_api_key)
        return has_proxy or has_zone or has_api


@dataclass
class ScraperConfig:
    """General scraper configuration."""

    data_dir: str = "data"
    images_dir: str = "data/images"
    max_retries: int = 3
    timeout: int = 30
    concurrent_requests: int = 5


config = BrightDataConfig()
scraper_config = ScraperConfig()
