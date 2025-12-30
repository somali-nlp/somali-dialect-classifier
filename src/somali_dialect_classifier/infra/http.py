"""HTTP utilities for web scraping processors."""

import time
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class TimeoutHTTPSession(requests.Session):
    """
    HTTP Session with automatic timeout enforcement.

    Automatically applies timeout to all requests if not explicitly provided.
    This prevents silent hangs on network failures.
    """

    def __init__(self, default_timeout: int = 30):
        """
        Initialize session with default timeout.

        Args:
            default_timeout: Default timeout in seconds for all requests
        """
        super().__init__()
        self.default_timeout = default_timeout

    def request(self, method, url, **kwargs):
        """
        Override request to inject timeout if not provided.

        If timeout is not specified in kwargs, uses self.default_timeout.
        """
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.default_timeout
        return super().request(method, url, **kwargs)


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
        timeout: Optional[int] = None,
        allowed_methods: Optional[list[str]] = None,
    ) -> TimeoutHTTPSession:
        """
        Create HTTP session with retry logic, proper headers, and timeout enforcement.

        Args:
            max_retries: Maximum number of retry attempts
            backoff_factor: Backoff factor for exponential backoff
            status_forcelist: List of HTTP status codes to retry on
            user_agent: Custom user agent string (uses default if None)
            timeout: Request timeout in seconds (loads from config if None)
            allowed_methods: List of HTTP methods to retry (default: GET, POST, HEAD, OPTIONS)

        Returns:
            Configured TimeoutHTTPSession with retry logic and automatic timeout
        """
        if status_forcelist is None:
            status_forcelist = [500, 502, 503, 504]

        if allowed_methods is None:
            allowed_methods = ["GET", "POST", "HEAD", "OPTIONS"]

        # Load timeout from config if not provided
        if timeout is None:
            from somali_dialect_classifier.infra.config import get_config

            config = get_config()
            timeout = config.http.request_timeout

        session = TimeoutHTTPSession(default_timeout=timeout)

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
