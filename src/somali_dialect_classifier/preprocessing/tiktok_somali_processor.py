"""
TikTok Somali Comments Processor.

Scrapes Somali comments from TikTok using Apify's TikTok Comments Scraper.
Follows the BasePipeline pattern for consistency with other data sources.

This processor is designed to integrate with the existing pipeline architecture
while handling the unique aspects of TikTok comment data (social media, informal text).
"""

import json
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Import our Apify client
from .apify_tiktok_client import ApifyTikTokClient
from .base_pipeline import BasePipeline, RawRecord
from .text_cleaners import TextCleaningPipeline


class TikTokSomaliProcessor(BasePipeline):
    """
    Processor for scraping and processing TikTok Somali comments via Apify.

    Inherits shared orchestration from BasePipeline and implements
    TikTok-specific scraping logic using Apify's actor.

    Note:
        TikTok comments represent informal, colloquial Somali text
        from social media - ideal for dialect classification training data.

    Quota Policy:
        TikTok scraping does NOT use automatic daily quotas. Instead, it uses
        manual cost-gating because each comment incurs a direct Apify API cost
        (~$1 per 1,000 comments). Users must manually schedule TikTok runs and
        specify video URLs to control costs. This differs from other sources
        (BBC, HuggingFace, Språkbanken) which use automated daily quotas for
        rate limiting and resource management.
    """

    def __init__(
        self,
        apify_api_token: str,
        apify_user_id: Optional[str] = None,
        video_urls: Optional[list[str]] = None,
        force: bool = False,
    ):
        """
        Initialize TikTok Somali processor.

        Args:
            apify_api_token: Apify API token
            apify_user_id: Apify user ID (optional, for reference)
            video_urls: List of TikTok video URLs to scrape (optional)
            force: Force reprocessing even if output exists

        Note:
            ALL comments from Apify are preserved. No limits, no fuzzy deduplication.
            You pay for every comment Apify scrapes, so we keep them all.
        """
        # Initialize Apify client
        self.apify_api_token = apify_api_token
        self.apify_user_id = apify_user_id
        self.apify_client = None  # Will be initialized in download()

        # TikTok-specific configuration
        self.video_urls = video_urls or []

        # Initialize deduplication and ledger BEFORE BasePipeline
        from somali_dialect_classifier.preprocessing.crawl_ledger import get_ledger
        from somali_dialect_classifier.preprocessing.dedup import DedupConfig, DedupEngine

        # IMPORTANT: Only remove EXACT duplicates, not similar comments
        # User pays for every comment Apify scrapes, so we keep ALL of them
        dedup_config = DedupConfig(
            hash_fields=["text", "url"],
            enable_minhash=False,  # Disabled: was removing similar (not identical) comments
            similarity_threshold=1.0,  # Only remove 100% identical duplicates
        )
        self.dedup = DedupEngine(dedup_config)
        self.ledger = get_ledger()
        self.metrics = None  # Will be initialized in download()

        # Initialize BasePipeline (generates run_id and logger)
        super().__init__(source="tiktok", log_frequency=50, force=force)

        # File paths (TikTok-specific naming)
        self.video_urls_file = self.raw_dir / f"tiktok-somali_{self.run_id}_raw_video-urls.json"
        self.apify_metadata_file = (
            self.raw_dir / f"tiktok-somali_{self.run_id}_raw_apify-metadata.json"
        )
        self.staging_file = self.staging_dir / f"tiktok-somali_{self.run_id}_staging_comments.jsonl"
        self.processed_file = (
            self.processed_dir / f"tiktok-somali_{self.run_id}_processed_cleaned.txt"
        )

    def _register_filters(self) -> None:
        """
        Register TikTok-specific filters.

        Strategy: NO FILTERING! User pays for every comment, so we keep them ALL.

        Even emoji-only or very short comments are kept since:
        - User paid $1 per 1,000 comments to Apify
        - Filtering wastes money
        - User can filter later during training if needed
        - Better to have all data than lose comments we paid for
        """
        # NO FILTERS - Keep 100% of comments!
        pass

    def _create_cleaner(self) -> TextCleaningPipeline:
        """Create text cleaner for TikTok comments."""
        from somali_dialect_classifier.preprocessing.text_cleaners import (
            TextCleaningPipeline,
            WhitespaceCleaner,
        )

        # MINIMAL cleaning - preserve EVERYTHING including emojis!
        # User paid for these comments, so we keep them as-is.
        # Only normalize whitespace to prevent formatting issues.
        return TextCleaningPipeline(
            [
                WhitespaceCleaner(),  # Just normalize whitespace
                # NO emoji removal
                # NO special character removal
                # NO length filtering
            ]
        )

    def _get_source_type(self) -> str:
        """Return source type for silver records."""
        return "social"

    def _get_license(self) -> str:
        """Return license information for silver records."""
        return "TikTok Terms of Service"

    def _get_language(self) -> str:
        """Return language code for silver records."""
        return "so"

    def _get_source_metadata(self) -> dict[str, Any]:
        """Return TikTok-specific metadata for silver records."""
        return {
            "platform": "tiktok",
            "scraper": "apify",
            "apify_user_id": self.apify_user_id,
            "num_videos": len(self.video_urls),
            "note": "ALL comments preserved - no limits applied",
        }

    def _get_domain(self) -> str:
        """Return content domain for silver records."""
        return "social_media"

    def _get_register(self) -> str:
        """
        Return linguistic register for silver records.

        Returns:
            Register string ("formal", "informal", "colloquial")

        Note:
            TikTok comments are social media content, inherently colloquial
        """
        return "colloquial"

    def download(self) -> Path:
        """
        Download TikTok comments using Apify actor.

        Returns:
            Path to video URLs file

        Raises:
            ValueError: If no video URLs provided
        """
        from somali_dialect_classifier.utils.logging_utils import set_context
        from somali_dialect_classifier.utils.metrics import MetricsCollector, PipelineType

        self.raw_dir.mkdir(parents=True, exist_ok=True)

        # Set context
        set_context(run_id=self.run_id, source="tiktok", phase="discovery")

        # Initialize metrics collector
        # Using STREAM_PROCESSING as TikTok Apify acts like an API stream
        self.metrics = MetricsCollector(
            self.run_id, "tiktok", pipeline_type=PipelineType.STREAM_PROCESSING
        )

        # Initialize Apify client
        self.apify_client = ApifyTikTokClient(
            api_token=self.apify_api_token, user_id=self.apify_user_id, logger=self.logger
        )

        # Check for existing video URLs file
        if self.video_urls_file.exists() and not self.force:
            self.logger.info(f"Video URLs file already exists: {self.video_urls_file}")
            with open(self.video_urls_file, encoding="utf-8") as f:
                data = json.load(f)
                self.video_urls = data["video_urls"]
            return self.video_urls_file

        # Validate video URLs
        if not self.video_urls:
            raise ValueError(
                "No video URLs provided. Please provide a list of TikTok video URLs to scrape."
            )

        self.logger.info("=" * 60)
        self.logger.info("PHASE 1: TikTok Video URL Discovery")
        self.logger.info("=" * 60)
        self.logger.info(f"Videos to scrape: {len(self.video_urls)}")

        # Save video URLs
        with open(self.video_urls_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "video_urls": self.video_urls,
                    "discovered_at": self.date_accessed,
                    "run_id": self.run_id,
                    "note": "ALL comments will be preserved - no limits",
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        self.logger.info(f"Saved {len(self.video_urls)} video URLs -> {self.video_urls_file}")

        # Mark URLs as discovered in ledger
        for url in self.video_urls:
            self.ledger.discover_url(url, "tiktok", metadata={"discovered_at": self.date_accessed})
            self.metrics.increment("urls_discovered")

        # Export metrics
        metrics_path = Path("data/metrics") / f"{self.run_id}_discovery.json"
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        self.metrics.export_json(metrics_path)

        return self.video_urls_file

    def extract(self) -> Path:
        """
        Scrape TikTok comments using Apify actor.

        Returns:
            Path to scraped comments file
        """
        from somali_dialect_classifier.utils.logging_utils import set_context

        if not self.video_urls_file.exists():
            raise FileNotFoundError(f"Video URLs not found: {self.video_urls_file}")

        self.staging_dir.mkdir(parents=True, exist_ok=True)

        if self.staging_file.exists() and not self.force:
            self.logger.info(f"Staging file already exists: {self.staging_file}")
            self.logger.info("Use force=True to re-scrape")
            return self.staging_file

        if self.staging_file.exists() and self.force:
            self.logger.info(f"Force re-scraping: removing existing file {self.staging_file}")
            self.staging_file.unlink()

        # Load video URLs
        with open(self.video_urls_file, encoding="utf-8") as f:
            data = json.load(f)
            self.video_urls = data["video_urls"]

        # Set context for extraction phase
        set_context(run_id=self.run_id, source="tiktok", phase="extraction")

        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("PHASE 2: TikTok Comment Extraction via Apify")
        self.logger.info("=" * 60)

        # Get account info and estimate cost
        try:
            account_info = self.apify_client.get_account_info()
            self.logger.info(f"Apify account: {account_info.get('username', 'N/A')}")
            self.logger.info(
                f"Available credits: ${account_info.get('plan', {}).get('availableCredits', 'N/A')}"
            )

            # Estimate cost (assuming average 500 comments per video)
            cost_estimate = self.apify_client.estimate_cost(
                num_videos=len(self.video_urls), avg_comments_per_video=500
            )
            self.logger.info(
                f"Estimated cost: ${cost_estimate['estimated_cost_usd']} "
                f"({cost_estimate['estimated_compute_units']} CU)"
            )
        except Exception as e:
            self.logger.warning(f"Could not fetch account info: {e}")

        # Start Apify actor run
        self.logger.info(f"Starting Apify actor for {len(self.video_urls)} videos...")
        self.logger.info("ALL comments will be scraped - no limits applied")
        scrape_result = self.apify_client.scrape_comments(
            video_urls=self.video_urls,
            max_comments_per_video=None,  # No limit - scrape ALL comments
            wait_for_completion=True,
            poll_interval=15,
        )

        # Save Apify metadata
        with open(self.apify_metadata_file, "w", encoding="utf-8") as f:
            json.dump(scrape_result, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Apify run completed: {scrape_result['run_id']}")
        self.logger.info(f"Dataset ID: {scrape_result['dataset_id']}")
        self.logger.info(f"Items scraped: {scrape_result['stats']['items_count']}")
        self.logger.info(f"Compute units used: {scrape_result['stats']['compute_units']}")

        # Fetch dataset items and write to staging
        dataset_id = scrape_result["dataset_id"]

        # STEP 1: Save raw Apify JSON to local disk
        raw_apify_file = self.raw_dir / f"tiktok-somali_{self.run_id}_raw_apify-dataset.jsonl"
        apify_items_count = 0

        self.logger.info(f"Saving raw Apify data to: {raw_apify_file}")

        with open(raw_apify_file, "w", encoding="utf-8") as raw_out:
            for item in self.apify_client.iter_dataset_items(dataset_id, batch_size=1000):
                raw_out.write(json.dumps(item, ensure_ascii=False) + "\n")
                apify_items_count += 1

        self.logger.info(f"Raw Apify data saved: {apify_items_count} items")

        # STEP 2: Transform raw data to staging format (NO FILTERING!)
        comments_count = 0
        skipped_empty = 0

        self.logger.info(f"Transforming {apify_items_count} items to staging format...")

        with (
            open(raw_apify_file, encoding="utf-8") as raw_in,
            open(self.staging_file, "w", encoding="utf-8") as staging_out,
        ):
            for line in raw_in:
                item = json.loads(line)

                # Transform to our format
                comment_data = self._transform_apify_item(item)

                if comment_data:
                    # Calculate hash for tracking (but DON'T skip duplicates)
                    import hashlib

                    text_hash = hashlib.sha256(comment_data["text"].encode()).hexdigest()
                    comment_data["text_hash"] = text_hash
                    comment_data["minhash_signature"] = ""  # Not using fuzzy matching

                    # Write to staging (KEEP ALL COMMENTS)
                    staging_out.write(json.dumps(comment_data, ensure_ascii=False) + "\n")
                    comments_count += 1

                    # Mark as fetched in ledger
                    self.ledger.mark_fetched(
                        url=comment_data["url"],
                        http_status=200,
                        content_length=len(comment_data["text"]),
                        source=self.source,
                    )
                    self.metrics.increment("urls_fetched")
                    self.metrics.record_text_length(len(comment_data["text"]))
                else:
                    skipped_empty += 1

        self.logger.info("=" * 60)
        self.logger.info("Extraction complete:")
        self.logger.info(f"  Raw items from Apify: {apify_items_count}")
        self.logger.info(f"  Staging comments saved: {comments_count}")
        self.logger.info(f"  Skipped (empty text): {skipped_empty}")
        self.logger.info(f"  Preservation rate: {100 * comments_count / apify_items_count:.1f}%")
        self.logger.info("=" * 60)

        # Export metrics
        from somali_dialect_classifier.utils.metrics import QualityReporter

        metrics_path = Path("data/metrics") / f"{self.run_id}_extraction.json"
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        self.metrics.export_json(metrics_path)

        report_path = Path("data/reports") / f"{self.run_id}_extraction_quality_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        QualityReporter(self.metrics).generate_markdown_report(report_path)

        self.logger.info(f"Metrics exported: {metrics_path}")
        self.logger.info(f"Quality report: {report_path}")

        return self.staging_file

    def _transform_apify_item(self, item: dict[str, Any]) -> Optional[dict[str, Any]]:
        """
        Transform Apify dataset item to our staging format.

        Args:
            item: Raw item from Apify dataset

        Returns:
            Transformed comment data or None if invalid
        """
        # Apify TikTok Comments Scraper returns items with structure:
        # {
        #   "text": "comment text",
        #   "createTime": 1761342789,
        #   "createTimeISO": "2025-10-24T21:53:09.000Z",
        #   "diggCount": 123,  # likes
        #   "replyCommentTotal": 5,
        #   "uniqueId": "username",  # username
        #   "uid": "7489303120642049032",  # user ID
        #   "cid": "7564909554666193671",  # comment ID
        #   "videoWebUrl": "https://tiktok.com/...",
        #   ...
        # }

        try:
            text = item.get("text", "").strip()
            if not text:
                return None

            # Filter out emoji-only/non-linguistic comments EARLY
            # This prevents paying to store/process comments with no linguistic content
            import re

            # Remove emojis, symbols, punctuation, whitespace
            text_without_symbols = re.sub(r"[^\w\s]", "", text, flags=re.UNICODE)
            text_alphanumeric_only = text_without_symbols.strip()

            # If nothing left after removing symbols, it's emoji-only
            if not text_alphanumeric_only:
                # Track emoji-only filter reason for metrics telemetry
                if hasattr(self, "metrics") and self.metrics:
                    self.metrics.record_filter_reason("emoji_only_comment")
                return None  # Skip emoji-only comments like "😂😂😂" or "🔥🔥"

            # Also skip if text is too short (less than 3 characters of actual text)
            if len(text_alphanumeric_only) < 3:
                # Track short-text filter reason for metrics telemetry
                if hasattr(self, "metrics") and self.metrics:
                    self.metrics.record_filter_reason("text_too_short_after_cleanup")
                return None  # Skip very short comments like "!!" or "??"

            # Build unique URL for comment (video URL + comment ID)
            # FIXED: Apify returns 'videoWebUrl' not 'videoUrl'
            video_url = item.get("videoWebUrl", "")
            comment_id = item.get("cid", item.get("id", ""))
            comment_url = f"{video_url}#comment-{comment_id}" if comment_id else video_url

            # Ensure all IDs are strings for schema compatibility
            # FIXED: Apify returns 'uid' at top level, not in 'user' object
            author_id = item.get("uid", "")
            author_id_str = str(author_id) if author_id else ""
            comment_id_str = str(comment_id) if comment_id else ""

            return {
                "url": comment_url,
                "video_url": video_url,
                "text": text,
                # FIXED: Apify returns 'uniqueId' at top level, not in 'user' object
                "author": item.get("uniqueId", "unknown"),
                "author_id": author_id_str,
                "created_at": item.get("createTime", ""),
                "likes": item.get("diggCount", 0),
                "replies": item.get("replyCommentTotal", 0),
                "comment_id": comment_id_str,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            }

        except (KeyError, TypeError, ValueError) as e:
            self.logger.warning(f"Failed to transform Apify item: {e}")
            return None

    def _extract_records(self) -> Iterator[RawRecord]:
        """
        Extract records from staging file (JSONL format).

        Yields RawRecord objects for each TikTok comment.
        BasePipeline.process() handles the rest.
        """
        with open(self.staging_file, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue

                comment = json.loads(line)

                # Use comment text as title (truncated)
                title = (
                    comment["text"][:100] + "..." if len(comment["text"]) > 100 else comment["text"]
                )

                # Convert all metadata values to strings for schema compatibility
                yield RawRecord(
                    title=title,
                    text=comment["text"],
                    url=comment["url"],
                    metadata={
                        "video_url": str(comment.get("video_url", "")),
                        "author": str(comment.get("author", "")),
                        "author_id": str(comment.get("author_id", "")),
                        "date_published": str(comment.get("created_at", "")),
                        "likes": str(comment.get("likes", 0)),
                        "replies": str(comment.get("replies", 0)),
                        "comment_id": str(comment.get("comment_id", "")),
                        "scraped_at": str(comment.get("scraped_at", "")),
                        "minhash_signature": str(comment.get("minhash_signature", "")),
                    },
                )
