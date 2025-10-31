"""
Apify TikTok Comments Scraper Client.

This module provides a client for interacting with the Apify TikTok Comments Scraper.
It handles authentication, actor execution, and data retrieval.

Apify Actor: https://apify.com/clockworks/tiktok-comments-scraper
"""

import time
import logging
from typing import Dict, Any, List, Optional, Iterator
from datetime import datetime, timezone
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ApifyTikTokClient:
    """
    Client for Apify TikTok Comments Scraper.

    Handles:
    - Authentication with Apify API
    - Actor run management
    - Data retrieval and pagination
    - Error handling and retries
    """

    # Apify API endpoints
    BASE_URL = "https://api.apify.com/v2"
    ACTOR_ID = "clockworks~tiktok-comments-scraper"  # Apify uses ~ not / in API calls

    def __init__(
        self,
        api_token: str,
        user_id: Optional[str] = None,
        timeout: int = 300,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Apify TikTok client.

        Args:
            api_token: Apify API token
            user_id: Apify user ID (optional, for reference)
            timeout: Request timeout in seconds
            logger: Logger instance (optional)
        """
        self.api_token = api_token
        self.user_id = user_id
        self.timeout = timeout
        self.logger = logger or logging.getLogger(__name__)

        # Create HTTP session with retry logic
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry logic."""
        session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _get_headers(self) -> Dict[str, str]:
        """Get API request headers with authentication."""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

    def start_actor_run(
        self,
        video_urls: List[str],
        max_comments: Optional[int] = None,
        proxy_config: Optional[Dict[str, Any]] = None
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
            "commentsPerPost": max_comments if max_comments else 100000,  # Large number for "unlimited"
            "proxy": proxy_config or {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"]
            }
        }

        self.logger.info(f"Starting actor run for {len(video_urls)} videos...")
        self.logger.debug(f"Actor input: {actor_input}")

        # Start actor run
        url = f"{self.BASE_URL}/acts/{self.ACTOR_ID}/runs"
        response = self.session.post(
            url,
            headers=self._get_headers(),
            json=actor_input,
            timeout=self.timeout
        )
        response.raise_for_status()

        run_data = response.json()
        run_id = run_data["data"]["id"]

        self.logger.info(f"Actor run started: {run_id}")
        self.logger.info(f"Monitor at: https://console.apify.com/actors/runs/{run_id}")

        return run_id

    def wait_for_run_completion(
        self,
        run_id: str,
        poll_interval: int = 10,
        max_wait_time: int = 3600
    ) -> Dict[str, Any]:
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
            response = self.session.get(
                url,
                headers=self._get_headers(),
                timeout=self.timeout
            )
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
                error_msg = f"Run {status.lower()}: {run_data.get('statusMessage', 'Unknown error')}"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)

            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > max_wait_time:
                raise TimeoutError(
                    f"Run {run_id} did not complete within {max_wait_time}s"
                )

            # Wait before next poll
            time.sleep(poll_interval)

    def get_dataset_items(
        self,
        dataset_id: str,
        offset: int = 0,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
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
        params = {
            "offset": offset,
            "limit": limit,
            "format": "json"
        }

        response = self.session.get(
            url,
            headers=self._get_headers(),
            params=params,
            timeout=self.timeout
        )
        response.raise_for_status()

        return response.json()

    def iter_dataset_items(
        self,
        dataset_id: str,
        batch_size: int = 1000
    ) -> Iterator[Dict[str, Any]]:
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
        video_urls: List[str],
        max_comments_per_video: Optional[int] = None,
        wait_for_completion: bool = True,
        poll_interval: int = 10
    ) -> Dict[str, Any]:
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
            "status": "RUNNING"
        }

        if wait_for_completion:
            # Wait for completion
            run_data = self.wait_for_run_completion(run_id, poll_interval=poll_interval)

            result.update({
                "status": run_data["status"],
                "dataset_id": run_data["defaultDatasetId"],
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "stats": {
                    "items_count": run_data.get("stats", {}).get("itemsCount", 0),
                    "requests_count": run_data.get("stats", {}).get("requestsCount", 0),
                    "compute_units": run_data.get("stats", {}).get("computeUnits", 0)
                }
            })

        return result

    def get_account_info(self) -> Dict[str, Any]:
        """
        Get Apify account information.

        Returns:
            Account info including credits and usage
        """
        url = f"{self.BASE_URL}/users/me"
        response = self.session.get(
            url,
            headers=self._get_headers(),
            timeout=self.timeout
        )
        response.raise_for_status()

        return response.json()["data"]

    def estimate_cost(
        self,
        num_videos: int,
        avg_comments_per_video: int = 500
    ) -> Dict[str, float]:
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
            num_videos * compute_units_per_video +
            (total_comments / 1000) * compute_units_per_1000_comments
        )

        # $1 = 1 compute unit (approximate)
        estimated_cost_usd = compute_units

        return {
            "num_videos": num_videos,
            "estimated_comments": total_comments,
            "estimated_compute_units": round(compute_units, 4),
            "estimated_cost_usd": round(estimated_cost_usd, 2)
        }
