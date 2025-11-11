"""HTTP utilities for web scraping processors."""

import time
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class HTTPSessionFactory:
    """Factory for creating configured HTTP sessions."""

    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    )

    @staticmethod
    def create_session(
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        status_forcelist: Optional[list[int]] = None,
        user_agent: Optional[str] = None,
        timeout: int = 30,
        allowed_methods: Optional[list[str]] = None,
    ) -> requests.Session:
        """
        Create HTTP session with retry logic and proper headers.

        Args:
            max_retries: Maximum number of retry attempts
            backoff_factor: Backoff factor for exponential backoff
            status_forcelist: List of HTTP status codes to retry on
            user_agent: Custom user agent string (uses default if None)
            timeout: Request timeout in seconds (unused, for documentation)
            allowed_methods: List of HTTP methods to retry (default: GET, POST, HEAD, OPTIONS)

        Returns:
            Configured requests.Session with retry logic
        """
        if status_forcelist is None:
            status_forcelist = [500, 502, 503, 504]

        if allowed_methods is None:
            allowed_methods = ["GET", "POST", "HEAD", "OPTIONS"]

        session = requests.Session()

        # Configure retry strategy
        retries = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            allowed_methods=allowed_methods,
        )

        # Mount adapter with retries
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set headers
        session.headers.update(
            {
                "User-Agent": user_agent or HTTPSessionFactory.DEFAULT_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }
        )

        return session


class RateLimiter:
    """Simple rate limiter for HTTP requests."""

    def __init__(self, calls_per_second: float = 1.0):
        """
        Initialize rate limiter.

        Args:
            calls_per_second: Maximum number of calls per second
        """
        self.delay = 1.0 / calls_per_second
        self.last_call = 0.0

    def wait(self):
        """Wait if necessary to respect rate limit."""
        elapsed = time.time() - self.last_call
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_call = time.time()
