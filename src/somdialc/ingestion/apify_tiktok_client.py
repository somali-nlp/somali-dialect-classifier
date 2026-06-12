"""
Apify TikTok Comments Scraper Client.

This module provides a client for interacting with the Apify TikTok Comments Scraper.
It handles authentication, actor execution, and data retrieval.

Apify Actor: https://apify.com/clockworks/tiktok-comments-scraper
"""

import logging
import time
from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import HTTPError
from urllib3.util.retry import Retry


class BudgetExceededError(Exception):
    """
    Raised before any Apify POST when the projected comment count would
    exceed the configured max_budget_usd cap.

    Attributes:
        projected_comments: Estimated raw comment count for the run.
        projected_cost_usd: Estimated cost in USD.
        budget_usd: Configured hard cap.
    """

    def __init__(self, projected_comments: int, projected_cost_usd: float, budget_usd: float):
        self.projected_comments = projected_comments
        self.projected_cost_usd = projected_cost_usd
        self.budget_usd = budget_usd
        super().__init__(
            f"Projected cost ${projected_cost_usd:.2f} ({projected_comments:,} raw comments) "
            f"exceeds budget cap ${budget_usd:.2f}. "
            f"Increase SDC_SCRAPING__TIKTOK__MAX_BUDGET_USD or reduce the URL list / "
            f"max_comments_per_video to proceed."
        )


class ApifyTikTokClient:
    """
    Client for Apify TikTok Comments Scraper.

    Handles:
    - Authentication with Apify API
    - Actor run management
    - Data retrieval and pagination
    - Error handling and retries
    - Hard per-run budget enforcement (BudgetExceededError before any POST)
    """

    # Apify API endpoints
    BASE_URL = "https://api.apify.com/v2"
    ACTOR_ID = "clockworks~tiktok-comments-scraper"  # Apify uses ~ not / in API calls

    # Cost model: Apify bills ~$1 per 1,000 raw comments.
    # The constant is the number of raw comments that cost $1.00.
    _COMMENTS_PER_USD = 1000.0

    def __init__(
        self,
        api_token: str,
        user_id: Optional[str] = None,
        timeout: int = 300,
        logger: Optional[logging.Logger] = None,
        max_budget_usd: Optional[float] = None,
    ):
        """
        Initialize Apify TikTok client.

        Args:
            api_token: Apify API token
            user_id: Apify user ID (optional, for reference)
            timeout: Request timeout in seconds
            logger: Logger instance (optional)
            max_budget_usd: Hard per-run spend cap in USD.  At $1/1,000 raw
                comments, max_budget_usd=20 caps the run at ~20,000 raw comments.
                Raises BudgetExceededError before any POST if the projected
                comment count would exceed this limit.  None = no cap.
        """
        self.api_token = api_token
        self.user_id = user_id
        self.timeout = timeout
        self.logger = logger or logging.getLogger(__name__)
        self.max_budget_usd = max_budget_usd

        # Create HTTP session with retry logic
        self.session = self._create_session()

    # CQ-6: bounded backoff constants for the actor-start POST retry loop.
    # Max 4 attempts (1 original + 3 retries), doubling from 2 s up to 16 s.
    _POST_RETRY_ATTEMPTS = 4
    _POST_RETRY_BASE_DELAY = 2.0
    _POST_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})

    def _check_budget(self, video_urls: list[str], max_comments: Optional[int]) -> None:
        """
        Pre-flight budget guard — raises BudgetExceededError before any POST.

        The projection uses the per-video comment cap (max_comments) when set,
        otherwise falls back to a conservative 500 comments/video estimate.
        This method composes with the CQ-6 retry guard: because it fires before
        the first POST attempt, no Apify run is ever created if the budget is
        exceeded, so retry loops never double-spend.

        Args:
            video_urls: Video URL list for the planned run.
            max_comments: Per-video comment cap passed to Apify (None = uncapped).

        Raises:
            BudgetExceededError: If the projected cost exceeds max_budget_usd.
        """
        if self.max_budget_usd is None:
            return  # No cap configured — pass through.

        # Conservative fallback when no per-video cap is set.
        effective_per_video = max_comments if max_comments else 500
        projected_comments = len(video_urls) * effective_per_video
        projected_cost = projected_comments / self._COMMENTS_PER_USD

        if projected_cost > self.max_budget_usd:
            raise BudgetExceededError(
                projected_comments=projected_comments,
                projected_cost_usd=projected_cost,
                budget_usd=self.max_budget_usd,
            )

        self.logger.info(
            "Budget pre-flight OK: projected %.2f USD (%d comments) <= cap %.2f USD",
            projected_cost,
            projected_comments,
            self.max_budget_usd,
        )

    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry logic for idempotent methods."""
        session = requests.Session()
        # GET/HEAD/OPTIONS retries are handled by urllib3 automatically.
        # POST (actor start) is intentionally excluded here; it is retried
        # explicitly in start_actor_run() with an idempotency guard.
        retries = Retry(
            total=5,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset({"GET", "HEAD", "OPTIONS"}),
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _get_headers(self) -> dict[str, str]:
        """Get API request headers with authentication."""
        return {"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"}

    def start_actor_run(
        self,
        video_urls: list[str],
        max_comments: Optional[int] = None,
        proxy_config: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Start an actor run to scrape TikTok comments.

        Args:
            video_urls: List of TikTok video URLs to scrape
            max_comments: Maximum number of comments to scrape per video (None = all)
            proxy_config: Apify proxy configuration (optional)

        Returns:
            Run ID for tracking the execution

        Raises:
            requests.HTTPError: If API request fails
        """
        # Build input configuration
        # Note: Clockworks actor expects "postURLs" not "videoUrls"
        actor_input = {
            "postURLs": video_urls,
            "commentsPerPost": max_comments
            if max_comments
            else 100000,  # Large number for "unlimited"
            "proxy": proxy_config or {"useApifyProxy": True, "apifyProxyGroups": ["RESIDENTIAL"]},
        }

        self.logger.info(f"Starting actor run for {len(video_urls)} videos...")
        self.logger.debug("Starting actor run with %d video URLs", len(video_urls))

        # Budget guard: raises BudgetExceededError before any network call.
        # Composes with CQ-6 retry loop — if this raises, no run_id is created
        # so retries cannot double-spend.
        self._check_budget(video_urls, max_comments)

        # CQ-6: Retry the actor-start POST on 429/5xx with bounded exponential
        # backoff.  Each attempt creates a NEW Apify run with a NEW run_id, so
        # we guard against re-billing by checking whether a run was already
        # created before retrying: if the POST response body contains a run_id
        # despite a non-2xx status (Apify occasionally returns 5xx after the run
        # is queued), we return that run_id immediately without a second POST.
        url = f"{self.BASE_URL}/acts/{self.ACTOR_ID}/runs"
        last_exc: Optional[Exception] = None
        delay = self._POST_RETRY_BASE_DELAY
        for attempt in range(1, self._POST_RETRY_ATTEMPTS + 1):
            try:
                response = self.session.post(
                    url, headers=self._get_headers(), json=actor_input, timeout=self.timeout
                )
                # Idempotency guard: extract run_id from body even on error status.
                try:
                    body = response.json()
                    if body.get("data", {}).get("id"):
                        run_id = body["data"]["id"]
                        self.logger.info(f"Actor run started: {run_id} (attempt {attempt})")
                        self.logger.info(
                            f"Monitor at: https://console.apify.com/actors/runs/{run_id}"
                        )
                        return run_id
                except Exception:
                    pass
                response.raise_for_status()
                # Fallthrough: raise_for_status did not raise (2xx without body run_id)
                run_id = response.json()["data"]["id"]
                break
            except HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else 0
                if (
                    status not in self._POST_RETRYABLE_STATUS
                    or attempt == self._POST_RETRY_ATTEMPTS
                ):
                    raise
                self.logger.warning(
                    f"Actor start POST returned {status} (attempt {attempt}/"
                    f"{self._POST_RETRY_ATTEMPTS}); retrying in {delay:.1f}s"
                )
                last_exc = exc
                time.sleep(delay)
                delay = min(delay * 2, 60.0)
        else:
            raise last_exc  # type: ignore[misc]

        self.logger.info(f"Actor run started: {run_id}")
        self.logger.info(f"Monitor at: https://console.apify.com/actors/runs/{run_id}")

        return run_id

    def wait_for_run_completion(
        self, run_id: str, poll_interval: int = 10, max_wait_time: int = 3600
    ) -> dict[str, Any]:
        """
        Wait for actor run to complete.

        Args:
            run_id: Actor run ID
            poll_interval: Seconds between status checks
            max_wait_time: Maximum seconds to wait (default: 1 hour)

        Returns:
            Run status data

        Raises:
            TimeoutError: If run doesn't complete within max_wait_time
            RuntimeError: If run fails
        """
        start_time = time.time()
        self.logger.info(f"Waiting for run {run_id} to complete...")

        while True:
            # Check run status
            url = f"{self.BASE_URL}/actor-runs/{run_id}"
            response = self.session.get(url, headers=self._get_headers(), timeout=self.timeout)
            response.raise_for_status()

            run_data = response.json()["data"]
            status = run_data["status"]

            self.logger.debug(f"Run status: {status}")

            # Check completion states
            if status == "SUCCEEDED":
                elapsed = time.time() - start_time
                self.logger.info(f"Run completed successfully in {elapsed:.1f}s")
                return run_data

            elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                error_msg = (
                    f"Run {status.lower()}: {run_data.get('statusMessage', 'Unknown error')}"
                )
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)

            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > max_wait_time:
                raise TimeoutError(f"Run {run_id} did not complete within {max_wait_time}s")

            # Wait before next poll
            time.sleep(poll_interval)

    def get_dataset_items(
        self, dataset_id: str, offset: int = 0, limit: int = 1000
    ) -> list[dict[str, Any]]:
        """
        Get items from dataset.

        Args:
            dataset_id: Dataset ID
            offset: Number of items to skip
            limit: Maximum number of items to return

        Returns:
            List of dataset items
        """
        url = f"{self.BASE_URL}/datasets/{dataset_id}/items"
        params = {"offset": offset, "limit": limit, "format": "json"}

        response = self.session.get(
            url, headers=self._get_headers(), params=params, timeout=self.timeout
        )
        response.raise_for_status()

        return response.json()

    def iter_dataset_items(
        self, dataset_id: str, batch_size: int = 1000
    ) -> Iterator[dict[str, Any]]:
        """
        Iterate over all items in dataset with automatic pagination.

        Args:
            dataset_id: Dataset ID
            batch_size: Number of items per batch

        Yields:
            Individual dataset items
        """
        offset = 0
        total_items = 0

        self.logger.info(f"Fetching dataset items from {dataset_id}...")

        while True:
            items = self.get_dataset_items(dataset_id, offset=offset, limit=batch_size)

            if not items:
                break

            for item in items:
                yield item
                total_items += 1

            self.logger.debug(f"Fetched {total_items} items so far...")

            # Check if we got fewer items than requested (end of dataset)
            if len(items) < batch_size:
                break

            offset += batch_size

        self.logger.info(f"Total items fetched: {total_items}")

    def scrape_comments(
        self,
        video_urls: list[str],
        max_comments_per_video: Optional[int] = None,
        wait_for_completion: bool = True,
        poll_interval: int = 10,
    ) -> dict[str, Any]:
        """
        High-level method to scrape TikTok comments.

        Args:
            video_urls: List of TikTok video URLs
            max_comments_per_video: Max comments per video (None = all)
            wait_for_completion: Whether to wait for run to complete
            poll_interval: Seconds between status checks

        Returns:
            Dictionary with run_id, status, and dataset_id
        """
        # Start actor run
        run_id = self.start_actor_run(video_urls, max_comments_per_video)

        result = {
            "run_id": run_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "RUNNING",
        }

        if wait_for_completion:
            # Wait for completion
            run_data = self.wait_for_run_completion(run_id, poll_interval=poll_interval)

            result.update(
                {
                    "status": run_data["status"],
                    "dataset_id": run_data["defaultDatasetId"],
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "stats": {
                        "items_count": run_data.get("stats", {}).get("itemsCount", 0),
                        "requests_count": run_data.get("stats", {}).get("requestsCount", 0),
                        "compute_units": run_data.get("stats", {}).get("computeUnits", 0),
                    },
                }
            )

        return result

    def get_account_info(self) -> dict[str, Any]:
        """
        Get Apify account information.

        Returns:
            Account info including credits and usage
        """
        url = f"{self.BASE_URL}/users/me"
        response = self.session.get(url, headers=self._get_headers(), timeout=self.timeout)
        response.raise_for_status()

        return response.json()["data"]

    def estimate_cost(self, num_videos: int, avg_comments_per_video: int = 500) -> dict[str, float]:
        """
        Estimate cost for scraping operation.

        Args:
            num_videos: Number of videos to scrape
            avg_comments_per_video: Estimated average comments per video

        Returns:
            Dictionary with cost estimates

        Note:
            This is a rough estimate. Actual costs depend on:
            - Proxy usage
            - Runtime duration
            - API rate limits
            - Comment pagination depth
        """
        # Rough estimates (adjust based on actual usage)
        compute_units_per_video = 0.01  # ~0.01 CU per video
        compute_units_per_1000_comments = 0.1  # ~0.1 CU per 1000 comments

        total_comments = num_videos * avg_comments_per_video
        compute_units = (
            num_videos * compute_units_per_video
            + (total_comments / 1000) * compute_units_per_1000_comments
        )

        # $1 = 1 compute unit (approximate)
        estimated_cost_usd = compute_units

        return {
            "num_videos": num_videos,
            "estimated_comments": total_comments,
            "estimated_compute_units": round(compute_units, 4),
            "estimated_cost_usd": round(estimated_cost_usd, 2),
        }
