"""
Adaptive rate limiting utilities for ethical web scraping.

Provides:
- Exponential backoff with jitter
- Adaptive rate limiting based on response times
- Token bucket algorithm for rate limiting
- Respect for HTTP 429 (Too Many Requests) and Retry-After headers
"""

import time
import random
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from collections import deque
import threading

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiter."""

    # Base delay settings
    min_delay: float = 1.0  # Minimum delay between requests (seconds)
    max_delay: float = 10.0  # Maximum delay between requests (seconds)

    # Exponential backoff settings
    backoff_multiplier: float = 2.0  # Multiplier for backoff
    max_backoff: float = 300.0  # Maximum backoff time (5 minutes)

    # Jitter settings
    jitter: bool = True  # Add random jitter to delays
    jitter_range: float = 0.2  # ±20% jitter

    # Adaptive settings
    adaptive: bool = True  # Enable adaptive rate limiting
    target_latency_ms: float = 1000.0  # Target server response time
    adaptation_rate: float = 0.1  # Rate of adaptation (0-1)

    # Token bucket settings (requests per time window)
    requests_per_hour: Optional[int] = None  # Maximum requests per hour
    requests_per_minute: Optional[int] = None  # Maximum requests per minute


class AdaptiveRateLimiter:
    """
    Adaptive rate limiter with exponential backoff and token bucket.

    Features:
    - Exponential backoff on errors
    - Adaptive delays based on server response times
    - Token bucket for enforcing request limits
    - Jitter to avoid thundering herd
    - Respect for HTTP Retry-After headers
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        """
        Initialize rate limiter.

        Args:
            config: Rate limit configuration
        """
        self.config = config or RateLimitConfig()

        # Current state
        self.current_delay = self.config.min_delay
        self.consecutive_errors = 0

        # Response time tracking for adaptive limiting
        self.recent_latencies = deque(maxlen=100)  # Last 100 requests

        # Token bucket for request limiting
        self.tokens = 0.0
        self.last_refill = time.time()
        self._lock = threading.Lock()

        # Calculate token refill rate
        self._calculate_refill_rate()

        # Last request time
        self.last_request_time = 0.0

    def _calculate_refill_rate(self):
        """Calculate token refill rate from config."""
        if self.config.requests_per_hour:
            # Tokens per second from hourly limit
            self.refill_rate = self.config.requests_per_hour / 3600.0
            self.max_tokens = self.config.requests_per_hour / 3600.0 * 60  # 1 minute worth
        elif self.config.requests_per_minute:
            # Tokens per second from minute limit
            self.refill_rate = self.config.requests_per_minute / 60.0
            self.max_tokens = self.config.requests_per_minute
        else:
            # No token bucket limiting
            self.refill_rate = None
            self.max_tokens = None

    def _refill_tokens(self):
        """Refill token bucket based on elapsed time."""
        if self.refill_rate is None:
            return

        now = time.time()
        elapsed = now - self.last_refill

        # Add tokens based on elapsed time
        self.tokens = min(
            self.max_tokens,
            self.tokens + (elapsed * self.refill_rate)
        )

        self.last_refill = now

    def _consume_token(self) -> bool:
        """
        Try to consume a token from bucket.

        Returns:
            True if token consumed, False if no tokens available
        """
        if self.refill_rate is None:
            return True  # No token limiting

        with self._lock:
            self._refill_tokens()

            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
            else:
                return False

    def _calculate_adaptive_delay(self) -> float:
        """
        Calculate adaptive delay based on recent response times.

        Returns:
            Recommended delay in seconds
        """
        if not self.config.adaptive or not self.recent_latencies:
            return self.current_delay

        # Calculate average recent latency
        avg_latency_ms = sum(self.recent_latencies) / len(self.recent_latencies)

        # If server is slow, increase delay
        if avg_latency_ms > self.config.target_latency_ms:
            # Server is struggling, slow down
            factor = 1.0 + (self.config.adaptation_rate * (avg_latency_ms / self.config.target_latency_ms - 1.0))
            new_delay = min(self.current_delay * factor, self.config.max_delay)
        else:
            # Server is responsive, can speed up slightly
            factor = 1.0 - (self.config.adaptation_rate * 0.5)  # Slower to decrease
            new_delay = max(self.current_delay * factor, self.config.min_delay)

        return new_delay

    def _add_jitter(self, delay: float) -> float:
        """
        Add random jitter to delay.

        Args:
            delay: Base delay in seconds

        Returns:
            Delay with jitter applied
        """
        if not self.config.jitter:
            return delay

        # Add ±jitter_range% random variation
        jitter_amount = delay * self.config.jitter_range
        return delay + random.uniform(-jitter_amount, jitter_amount)

    def wait(self):
        """
        Wait appropriate amount of time before next request.

        This method:
        1. Waits for token bucket availability
        2. Applies adaptive delay
        3. Adds jitter
        4. Ensures minimum time between requests
        """
        # Wait for token availability
        while not self._consume_token():
            time.sleep(0.1)  # Check every 100ms

        # Calculate adaptive delay
        if self.config.adaptive:
            self.current_delay = self._calculate_adaptive_delay()

        # Add jitter
        delay = self._add_jitter(self.current_delay)

        # Ensure minimum time has passed since last request
        now = time.time()
        elapsed_since_last = now - self.last_request_time

        if elapsed_since_last < delay:
            sleep_time = delay - elapsed_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def record_success(self, response_time_ms: float):
        """
        Record successful request with response time.

        Args:
            response_time_ms: Response time in milliseconds
        """
        # Reset error counter on success
        self.consecutive_errors = 0

        # Record latency for adaptive limiting
        self.recent_latencies.append(response_time_ms)

        logger.debug(
            f"Request successful (latency: {response_time_ms:.0f}ms, "
            f"current_delay: {self.current_delay:.2f}s)"
        )

    def record_error(self, http_status: Optional[int] = None, retry_after: Optional[int] = None):
        """
        Record failed request and apply exponential backoff.

        Args:
            http_status: HTTP status code (if applicable)
            retry_after: Value from Retry-After header (seconds)
        """
        self.consecutive_errors += 1

        # Apply exponential backoff
        backoff = min(
            self.config.min_delay * (self.config.backoff_multiplier ** self.consecutive_errors),
            self.config.max_backoff
        )

        # Respect Retry-After header if present
        if retry_after:
            backoff = max(backoff, retry_after)
            logger.info(f"Server requested retry after {retry_after}s")

        # Update current delay
        self.current_delay = backoff

        logger.warning(
            f"Request failed (status: {http_status}, errors: {self.consecutive_errors}, "
            f"backoff: {backoff:.2f}s)"
        )

    def handle_429(self, retry_after: Optional[str] = None):
        """
        Handle HTTP 429 (Too Many Requests) response.

        Args:
            retry_after: Retry-After header value (seconds or HTTP date)
        """
        # Parse Retry-After header
        retry_seconds = None

        if retry_after:
            try:
                # Try as integer (seconds)
                retry_seconds = int(retry_after)
            except ValueError:
                # Try as HTTP date
                try:
                    from email.utils import parsedate_to_datetime
                    retry_date = parsedate_to_datetime(retry_after)
                    retry_seconds = (retry_date - datetime.now()).total_seconds()
                except Exception as e:
                    logger.warning(f"Could not parse Retry-After header: {e}")

        # Default to exponential backoff if no valid Retry-After
        if not retry_seconds:
            retry_seconds = min(
                self.config.min_delay * (self.config.backoff_multiplier ** (self.consecutive_errors + 1)),
                self.config.max_backoff
            )

        logger.warning(f"HTTP 429: Too Many Requests. Backing off for {retry_seconds}s")

        # Record error and wait
        self.record_error(http_status=429, retry_after=int(retry_seconds))
        time.sleep(retry_seconds)

    def reset(self):
        """Reset rate limiter to initial state."""
        self.current_delay = self.config.min_delay
        self.consecutive_errors = 0
        self.recent_latencies.clear()
        logger.info("Rate limiter reset")

    def get_statistics(self) -> dict:
        """Get rate limiter statistics."""
        stats = {
            "current_delay": self.current_delay,
            "consecutive_errors": self.consecutive_errors,
            "tokens_available": self.tokens if self.refill_rate else None,
            "refill_rate": self.refill_rate
        }

        if self.recent_latencies:
            stats["avg_latency_ms"] = sum(self.recent_latencies) / len(self.recent_latencies)
            stats["min_latency_ms"] = min(self.recent_latencies)
            stats["max_latency_ms"] = max(self.recent_latencies)

        return stats


# Context manager for timing requests

class TimedRequest:
    """Context manager for timing requests and updating rate limiter."""

    def __init__(self, rate_limiter: AdaptiveRateLimiter):
        """
        Initialize timed request.

        Args:
            rate_limiter: AdaptiveRateLimiter instance to update
        """
        self.rate_limiter = rate_limiter
        self.start_time = None
        self.elapsed_ms = None

    def __enter__(self):
        """Start timing."""
        # Wait before making request
        self.rate_limiter.wait()
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and record result."""
        if self.start_time:
            self.elapsed_ms = (time.time() - self.start_time) * 1000

            if exc_type is None:
                # Success
                self.rate_limiter.record_success(self.elapsed_ms)
            else:
                # Error
                self.rate_limiter.record_error()

    def get_elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        return self.elapsed_ms or 0


# Example usage
if __name__ == "__main__":
    # Configure rate limiter for BBC scraping
    config = RateLimitConfig(
        min_delay=5.0,
        max_delay=10.0,
        backoff_multiplier=2.0,
        max_backoff=300.0,
        jitter=True,
        adaptive=True,
        requests_per_hour=60  # 60 requests per hour
    )

    rate_limiter = AdaptiveRateLimiter(config)

    # Simulate requests
    for i in range(10):
        with TimedRequest(rate_limiter) as timer:
            # Simulate request
            time.sleep(random.uniform(0.1, 0.5))

            # Simulate occasional errors
            if random.random() < 0.1:
                raise Exception("Simulated error")

        print(f"Request {i+1}: {timer.get_elapsed_ms():.0f}ms")
        print(f"Stats: {rate_limiter.get_statistics()}")
