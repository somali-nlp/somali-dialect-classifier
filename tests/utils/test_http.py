"""Tests for HTTP utilities."""

import time

import pytest
import requests

from somali_dialect_classifier.utils.http import HTTPSessionFactory, RateLimiter


class TestHTTPSessionFactory:
    """Test cases for HTTPSessionFactory."""

    def test_create_session_default_params(self):
        """Test HTTP session creation with default parameters."""
        session = HTTPSessionFactory.create_session()

        assert isinstance(session, requests.Session)
        assert "User-Agent" in session.headers
        assert session.headers["User-Agent"] == HTTPSessionFactory.DEFAULT_USER_AGENT
        assert "Accept" in session.headers
        assert "Accept-Language" in session.headers

    def test_create_session_custom_retries(self):
        """Test HTTP session with custom retry configuration."""
        session = HTTPSessionFactory.create_session(max_retries=5)

        assert session is not None
        # Access adapter to check retries
        adapter = session.adapters["http://"]
        assert adapter.max_retries.total == 5

    def test_create_session_custom_status_forcelist(self):
        """Test HTTP session with custom status forcelist."""
        custom_status = [500, 502, 503]
        session = HTTPSessionFactory.create_session(status_forcelist=custom_status)

        assert session is not None
        adapter = session.adapters["http://"]
        assert adapter.max_retries.status_forcelist == custom_status

    def test_create_session_custom_user_agent(self):
        """Test custom user agent string."""
        custom_ua = "CustomBot/1.0"
        session = HTTPSessionFactory.create_session(user_agent=custom_ua)

        assert session.headers["User-Agent"] == custom_ua

    def test_create_session_custom_allowed_methods(self):
        """Test custom allowed methods for retries."""
        custom_methods = ["GET", "POST"]
        session = HTTPSessionFactory.create_session(allowed_methods=custom_methods)

        assert session is not None
        adapter = session.adapters["http://"]
        # allowed_methods is stored as a list in the Retry object
        assert set(adapter.max_retries.allowed_methods) == set(custom_methods)

    def test_create_session_backoff_factor(self):
        """Test custom backoff factor."""
        session = HTTPSessionFactory.create_session(backoff_factor=1.0)

        assert session is not None
        adapter = session.adapters["http://"]
        assert adapter.max_retries.backoff_factor == 1.0

    def test_session_has_both_http_and_https_adapters(self):
        """Test that session has adapters for both HTTP and HTTPS."""
        session = HTTPSessionFactory.create_session()

        assert "http://" in session.adapters
        assert "https://" in session.adapters


class TestRateLimiter:
    """Test cases for RateLimiter."""

    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(calls_per_second=2.0)

        assert limiter.delay == 0.5  # 1.0 / 2.0

    def test_rate_limiter_default_rate(self):
        """Test rate limiter with default rate."""
        limiter = RateLimiter()

        assert limiter.delay == 1.0  # 1.0 / 1.0

    def test_rate_limiter_wait_enforces_delay(self):
        """Test that rate limiter enforces delay between calls."""
        limiter = RateLimiter(calls_per_second=2.0)  # 0.5s delay

        start = time.time()
        limiter.wait()
        limiter.wait()
        duration = time.time() - start

        # Should wait at least 0.5s (with small tolerance for timing variations)
        assert duration >= 0.45

    def test_rate_limiter_no_wait_on_first_call(self):
        """Test that first call to rate limiter doesn't wait."""
        limiter = RateLimiter(calls_per_second=1.0)

        start = time.time()
        limiter.wait()
        duration = time.time() - start

        # First call should be immediate (with small tolerance)
        assert duration < 0.1

    def test_rate_limiter_multiple_calls(self):
        """Test rate limiter with multiple sequential calls."""
        limiter = RateLimiter(calls_per_second=4.0)  # 0.25s delay

        start = time.time()
        for _ in range(3):
            limiter.wait()
        duration = time.time() - start

        # Should wait at least 0.5s total (2 delays of 0.25s each, first call immediate)
        assert duration >= 0.45

    def test_rate_limiter_high_rate(self):
        """Test rate limiter with high rate (short delays)."""
        limiter = RateLimiter(calls_per_second=10.0)  # 0.1s delay

        start = time.time()
        limiter.wait()
        limiter.wait()
        duration = time.time() - start

        # Should wait at least 0.1s
        assert duration >= 0.09


@pytest.mark.integration
class TestHTTPSessionIntegration:
    """Integration tests for HTTP session functionality."""

    def test_session_can_make_request(self):
        """Test that created session can make actual HTTP request."""
        session = HTTPSessionFactory.create_session()

        # Use a reliable test endpoint
        response = session.get("https://httpbin.org/user-agent", timeout=10)

        assert response.status_code == 200
        assert HTTPSessionFactory.DEFAULT_USER_AGENT in response.text

    def test_session_retry_on_500_error(self):
        """Test that session retries on 500 errors."""
        session = HTTPSessionFactory.create_session(
            max_retries=3, status_forcelist=[500, 502, 503]
        )

        # httpbin.org provides a /status/500 endpoint that returns 500
        # The session should retry and eventually fail
        with pytest.raises(requests.exceptions.RetryError):
            session.get("https://httpbin.org/status/500", timeout=10)
