"""
Prefect workflows for orchestrating data collection pipelines.

Provides coordinated execution of all four data sources with:
- Parallel execution where possible
- Error handling and retry logic
- Progress tracking and notifications
- Quality monitoring
"""

import logging
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Optional

try:
    from prefect import flow, task
    from prefect.task_runners import ConcurrentTaskRunner

    PREFECT_AVAILABLE = True
except ImportError:
    PREFECT_AVAILABLE = False

    # Provide fallback decorators
    def flow(fn=None, **kwargs):
        if fn is None:
            return lambda f: f
        return fn

    def task(fn=None, **kwargs):
        if fn is None:
            return lambda f: f
        return fn


logger = logging.getLogger(__name__)


def _get_ledger():
    """Get ledger instance for orchestrator operations."""
    from ..ingestion.crawl_ledger import CrawlLedger

    # Use CrawlLedger factory which respects SDC_LEDGER_BACKEND env var
    # Automatically selects PostgreSQL or SQLite based on configuration
    return CrawlLedger()


def should_run_source(source: str) -> tuple[bool, str]:
    """
    Determine if source should be processed based on refresh cadence.

    FIXED: Now uses pipeline_runs table for accurate scheduling.

    Implements Phase 4 smart orchestrator logic per
    analysis-dedup-orchestration-strategy-20251109.md

    Args:
        source: Data source name ('bbc', 'wikipedia', 'tiktok', etc.)

    Returns:
        Tuple of (should_run: bool, reason: str)
    """
    from ..infra.config import get_config

    config = get_config()
    ledger = _get_ledger()

    # Always run if in initial collection phase
    if is_initial_collection_phase():
        return True, "initial_collection"

    # Get last successful run time from pipeline_runs table
    last_run = ledger.get_last_successful_run(source)

    if last_run is None:
        logger.info(f"{source}: Never run before, scheduling run")
        return True, "never_run"

    # Check refresh cadence
    cadence_days = config.orchestration.get_cadence(source)
    time_since_last = (datetime.now(timezone.utc) - last_run).total_seconds() / 86400

    if time_since_last >= cadence_days:
        logger.info(
            f"{source}: Last run {time_since_last:.1f} days ago, "
            f"cadence {cadence_days} days - scheduling run"
        )
        return True, f"refresh_due (last_run: {time_since_last:.1f} days ago)"
    else:
        days_until_refresh = cadence_days - time_since_last
        logger.info(
            f"{source}: Last run {time_since_last:.1f} days ago, "
            f"cadence {cadence_days} days - skipping"
        )
        return False, f"refresh_not_due (next in {days_until_refresh:.1f} days)"


def is_initial_collection_phase() -> bool:
    """
    Check if we're in the initial collection campaign.

    Uses the 'campaign_init_001' status in the ledger.
    """
    ledger = _get_ledger()
    status = ledger.get_campaign_status("campaign_init_001")
    
    # If campaign doesn't exist, start it
    if status is None:
        from ..infra.config import get_config
        config = get_config()
        ledger.start_campaign(
            "campaign_init_001", 
            "Initial Data Ingestion",
            {"duration_days": config.orchestration.initial_collection_days}
        )
        return True
        
    return status == "ACTIVE"


def _setup_orchestrator_logging() -> None:
    """
    Set up logging for orchestration flows.

    Creates rotating file handler for orchestrator.log with 10MB max file size
    to capture all pipeline execution logs in a unified location.
    """
    # Console logs - maintain real-time monitoring
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,  # Reset existing handlers
    )

    # File logs (rotating) under logs/
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Create handler for orchestrator log file
    # Use larger maxBytes (10MB) for orchestrator since it logs multiple pipelines
    fh = RotatingFileHandler(
        logs_dir / "orchestrator.log",
        maxBytes=10_000_000,  # 10MB (larger for orchestrator)
        backupCount=5,  # Keep more history for orchestrator
    )
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

    # Add handler to root logger to capture all downstream logs
    root_logger = logging.getLogger()

    # Remove any existing file handlers to prevent duplication
    root_logger.handlers = [
        h for h in root_logger.handlers if not isinstance(h, RotatingFileHandler)
    ]

    # Add our file handler
    root_logger.addHandler(fh)

    logger.info("Orchestrator logging initialized: logs/orchestrator.log")


@task(retries=2, retry_delay_seconds=10)
def run_wikipedia_task(force: bool = False, run_seed: Optional[str] = None) -> dict[str, Any]:
    """
    Task to run Wikipedia data collection pipeline.

    Args:
        force: Force reprocessing of existing data

    Returns:
        Dictionary with pipeline results and metrics
    """
    import subprocess
    import uuid

    from ..infra.config import get_config
    from ..ingestion.crawl_ledger import CrawlLedger
    from ..ingestion.processors.wikipedia_somali_processor import WikipediaSomaliProcessor

    logger.info("Starting Wikipedia pipeline...")

    # Check for concurrent runs before starting expensive work
    ledger = CrawlLedger()
    if ledger.is_source_locked("wikipedia"):
        logger.warning("Wikipedia pipeline already running, skipping")
        return {
            "source": "Wikipedia-Somali",
            "status": "skipped",
            "reason": "concurrent_run_active",
        }

    # Acquire lock before pipeline starts
    try:
        ledger.acquire_source_lock("wikipedia", timeout=30)
    except RuntimeError as e:
        logger.error(f"Failed to acquire lock: {e}")
        return {
            "source": "Wikipedia-Somali",
            "status": "failed",
            "reason": "lock_timeout",
            "error": str(e),
        }

    # Generate run ID and get git commit
    run_id = f"wikipedia_{uuid.uuid4().hex[:12]}"
    try:
        git_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:
        git_commit = None

    # Get config for pipeline run tracking
    config = get_config()
    quota_config = {"quota": config.orchestration.get_quota("wikipedia")}

    # Register pipeline run
    ledger.register_pipeline_run(
        run_id=run_id,
        source="wikipedia",
        pipeline_type="web",
        config=quota_config,
        git_commit=git_commit,
    )

    try:
        # Run pipeline with lock held
        ledger.update_pipeline_run(run_id=run_id, status="RUNNING")

        processor = WikipediaSomaliProcessor(force=force, run_seed=run_seed)
        silver_path = processor.run()

        # Get statistics from ledger
        stats = processor.ledger.get_statistics("wikipedia")
        records_processed = stats.get("by_state", {}).get("processed", 0)

        # Mark pipeline run as completed
        ledger.update_pipeline_run(
            run_id=run_id,
            status="COMPLETED",
            records_processed=records_processed,
            end_time=datetime.now(timezone.utc),
        )

        return {
            "source": "Wikipedia-Somali",
            "status": "success",
            "silver_path": str(silver_path),
            "statistics": stats,
        }
    except Exception as e:
        logger.error(f"Wikipedia pipeline failed: {e}")

        # Mark pipeline run as failed
        ledger.update_pipeline_run(
            run_id=run_id,
            status="FAILED",
            errors=str(e),
            end_time=datetime.now(timezone.utc),
        )

        return {
            "source": "Wikipedia-Somali",
            "status": "failed",
            "error": str(e),
        }
    finally:
        # ALWAYS release lock, even if pipeline fails
        ledger.release_source_lock("wikipedia")
        logger.info("Wikipedia pipeline completed and lock released")


@task(retries=2, retry_delay_seconds=10)
def run_bbc_task(
    max_articles: Optional[int] = None, force: bool = False, run_seed: Optional[str] = None
) -> dict[str, Any]:
    """
    Task to run BBC Somali data collection pipeline.

    Args:
        max_articles: Maximum articles to scrape (None = unlimited)
        force: Force reprocessing of existing data

    Returns:
        Dictionary with pipeline results and metrics
    """
    from ..ingestion.processors.bbc_somali_processor import BBCSomaliProcessor
    from ..ingestion.crawl_ledger import CrawlLedger

    logger.info("Starting BBC pipeline...")

    # Check for concurrent runs before starting expensive work
    ledger = CrawlLedger()
    if ledger.is_source_locked("bbc"):
        logger.warning("BBC pipeline already running, skipping")
        return {"source": "BBC-Somali", "status": "skipped", "reason": "concurrent_run_active"}

    # Acquire lock before pipeline starts
    try:
        ledger.acquire_source_lock("bbc", timeout=30)
    except RuntimeError as e:
        logger.error(f"Failed to acquire lock: {e}")
        return {
            "source": "BBC-Somali",
            "status": "failed",
            "reason": "lock_timeout",
            "error": str(e),
        }

    try:
        # Run pipeline with lock held
        processor = BBCSomaliProcessor(max_articles=max_articles, force=force, run_seed=run_seed)
        silver_path = processor.run()

        # Get statistics from ledger
        stats = processor.ledger.get_statistics("bbc")

        return {
            "source": "BBC-Somali",
            "status": "success",
            "silver_path": str(silver_path),
            "statistics": stats,
        }
    except Exception as e:
        logger.error(f"BBC pipeline failed: {e}")
        return {
            "source": "BBC-Somali",
            "status": "failed",
            "error": str(e),
        }
    finally:
        # ALWAYS release lock, even if pipeline fails
        ledger.release_source_lock("bbc")
        logger.info("BBC pipeline completed and lock released")


@task(retries=2, retry_delay_seconds=10)
def run_huggingface_task(
    dataset_name: str = "allenai/c4",
    dataset_config: str = "so",
    max_records: Optional[int] = None,
    force: bool = False,
    run_seed: Optional[str] = None,
) -> dict[str, Any]:
    """
    Task to run HuggingFace datasets collection pipeline.

    Args:
        dataset_name: HuggingFace dataset name
        dataset_config: Dataset configuration (language code)
        max_records: Maximum records to process (None = unlimited)
        force: Force reprocessing of existing data

    Returns:
        Dictionary with pipeline results and metrics
    """
    from ..ingestion.crawl_ledger import CrawlLedger
    from ..ingestion.processors.huggingface_somali_processor import HuggingFaceSomaliProcessor

    logger.info(f"Starting HuggingFace pipeline: {dataset_name}...")

    # Check for concurrent runs before starting expensive work
    ledger = CrawlLedger()
    if ledger.is_source_locked("huggingface"):
        logger.warning("HuggingFace pipeline already running, skipping")
        return {
            "source": "HuggingFace-Somali",
            "status": "skipped",
            "reason": "concurrent_run_active",
        }

    # Acquire lock before pipeline starts
    try:
        ledger.acquire_source_lock("huggingface", timeout=30)
    except RuntimeError as e:
        logger.error(f"Failed to acquire lock: {e}")
        return {
            "source": "HuggingFace-Somali",
            "status": "failed",
            "reason": "lock_timeout",
            "error": str(e),
        }

    try:
        # Run pipeline with lock held
        processor = HuggingFaceSomaliProcessor(
            dataset_name=dataset_name,
            dataset_config=dataset_config,
            url_field="url",  # Required for ledger deduplication
            max_records=max_records,
            force=force,
            run_seed=run_seed,
        )
        silver_path = processor.run()

        # Get statistics
        dataset_slug = dataset_name.split("/")[-1]
        source = f"HuggingFace-Somali_{dataset_slug}"

        return {
            "source": source,
            "status": "success",
            "silver_path": str(silver_path),
            "dataset_name": dataset_name,
            "dataset_config": dataset_config,
        }
    except Exception as e:
        logger.error(f"HuggingFace pipeline failed: {e}")
        return {
            "source": f"HuggingFace-{dataset_name}",
            "status": "failed",
            "error": str(e),
        }
    finally:
        # ALWAYS release lock, even if pipeline fails
        ledger.release_source_lock("huggingface")
        logger.info("HuggingFace pipeline completed and lock released")


@task(retries=2, retry_delay_seconds=10)
def run_sprakbanken_task(
    corpus_id: str = "all", force: bool = False, run_seed: Optional[str] = None
) -> dict[str, Any]:
    """
    Task to run Språkbanken corpora collection pipeline.

    Args:
        corpus_id: Specific corpus ID or "all" for all 23 corpora
        force: Force reprocessing of existing data

    Returns:
        Dictionary with pipeline results and metrics
    """
    from ..ingestion.crawl_ledger import CrawlLedger
    from ..ingestion.processors.sprakbanken_somali_processor import SprakbankenSomaliProcessor

    logger.info(f"Starting Språkbanken pipeline: {corpus_id}...")

    # Check for concurrent runs before starting expensive work
    ledger = CrawlLedger()
    if ledger.is_source_locked("sprakbanken"):
        logger.warning("Språkbanken pipeline already running, skipping")
        return {
            "source": "Sprakbanken-Somali",
            "status": "skipped",
            "reason": "concurrent_run_active",
        }

    # Acquire lock before pipeline starts
    try:
        ledger.acquire_source_lock("sprakbanken", timeout=30)
    except RuntimeError as e:
        logger.error(f"Failed to acquire lock: {e}")
        return {
            "source": "Sprakbanken-Somali",
            "status": "failed",
            "reason": "lock_timeout",
            "error": str(e),
        }

    try:
        # Run pipeline with lock held
        processor = SprakbankenSomaliProcessor(corpus_id=corpus_id, force=force, run_seed=run_seed)
        silver_path = processor.run()

        # Get statistics
        source = f"Sprakbanken-Somali-{corpus_id}"

        return {
            "source": source,
            "status": "success",
            "silver_path": str(silver_path),
            "corpus_id": corpus_id,
        }
    except Exception as e:
        logger.error(f"Språkbanken pipeline failed: {e}")
        return {
            "source": f"Sprakbanken-Somali-{corpus_id}",
            "status": "failed",
            "error": str(e),
        }
    finally:
        # ALWAYS release lock, even if pipeline fails
        ledger.release_source_lock("sprakbanken")
        logger.info("Språkbanken pipeline completed and lock released")


@task(retries=2, retry_delay_seconds=10)
def run_tiktok_task(
    video_urls: list[str],
    apify_api_token: str,
    apify_user_id: Optional[str] = None,
    force: bool = False,
    run_seed: Optional[str] = None,
) -> dict[str, Any]:
    """
    Task to run TikTok comments collection pipeline.

    Args:
        video_urls: List of TikTok video URLs to scrape
        apify_api_token: Apify API token for authentication
        apify_user_id: Apify user ID (optional, for reference)
        force: Force reprocessing of existing data

    Returns:
        Dictionary with pipeline results and metrics
    """
    from ..ingestion.crawl_ledger import CrawlLedger
    from ..ingestion.processors.tiktok_somali_processor import TikTokSomaliProcessor

    logger.info(f"Starting TikTok pipeline for {len(video_urls)} videos...")

    # Check for concurrent runs before starting expensive work
    ledger = CrawlLedger()
    if ledger.is_source_locked("tiktok"):
        logger.warning("TikTok pipeline already running, skipping")
        return {"source": "TikTok-Somali", "status": "skipped", "reason": "concurrent_run_active"}

    # Acquire lock before pipeline starts
    try:
        ledger.acquire_source_lock("tiktok", timeout=30)
    except RuntimeError as e:
        logger.error(f"Failed to acquire lock: {e}")
        return {
            "source": "TikTok-Somali",
            "status": "failed",
            "reason": "lock_timeout",
            "error": str(e),
        }

    try:
        # Run pipeline with lock held
        processor = TikTokSomaliProcessor(
            apify_api_token=apify_api_token,
            apify_user_id=apify_user_id,
            video_urls=video_urls,
            force=force,
            run_seed=run_seed,
        )
        silver_path = processor.run()

        # Get statistics
        source = "TikTok-Somali"

        return {
            "source": source,
            "status": "success",
            "silver_path": str(silver_path),
            "num_videos": len(video_urls),
        }
    except Exception as e:
        logger.error(f"TikTok pipeline failed: {e}")
        return {
            "source": "TikTok-Somali",
            "status": "failed",
            "error": str(e),
        }
    finally:
        # ALWAYS release lock, even if pipeline fails
        ledger.release_source_lock("tiktok")
        logger.info("TikTok pipeline completed and lock released")


@flow(
    name="Wikipedia Data Collection",
    description="Collect and process Wikipedia Somali articles",
)
def run_wikipedia_pipeline(force: bool = False) -> dict[str, Any]:
    """
    Flow to orchestrate Wikipedia data collection.

    Args:
        force: Force reprocessing of existing data

    Returns:
        Pipeline execution results
    """
    return run_wikipedia_task(force=force)


@flow(
    name="BBC Somali Data Collection",
    description="Collect and process BBC Somali news articles",
)
def run_bbc_pipeline(max_articles: Optional[int] = None, force: bool = False) -> dict[str, Any]:
    """
    Flow to orchestrate BBC Somali data collection.

    Args:
        max_articles: Maximum articles to scrape
        force: Force reprocessing of existing data

    Returns:
        Pipeline execution results
    """
    return run_bbc_task(max_articles=max_articles, force=force)


@flow(
    name="HuggingFace Dataset Collection",
    description="Collect and process HuggingFace datasets",
)
def run_huggingface_pipeline(
    dataset_name: str = "allenai/c4",
    dataset_config: str = "so",
    max_records: Optional[int] = None,
    force: bool = False,
) -> dict[str, Any]:
    """
    Flow to orchestrate HuggingFace dataset collection.

    Args:
        dataset_name: HuggingFace dataset name
        dataset_config: Dataset configuration
        max_records: Maximum records to process
        force: Force reprocessing of existing data

    Returns:
        Pipeline execution results
    """
    return run_huggingface_task(
        dataset_name=dataset_name,
        dataset_config=dataset_config,
        max_records=max_records,
        force=force,
    )


@flow(
    name="Språkbanken Corpora Collection",
    description="Collect and process Språkbanken Somali corpora",
)
def run_sprakbanken_pipeline(corpus_id: str = "all", force: bool = False) -> dict[str, Any]:
    """
    Flow to orchestrate Språkbanken corpora collection.

    Args:
        corpus_id: Specific corpus ID or "all"
        force: Force reprocessing of existing data

    Returns:
        Pipeline execution results
    """
    return run_sprakbanken_task(corpus_id=corpus_id, force=force)


@flow(
    name="TikTok Comments Collection",
    description="Collect and process TikTok Somali comments via Apify",
)
def run_tiktok_pipeline(
    video_urls: list[str],
    apify_api_token: str,
    apify_user_id: Optional[str] = None,
    force: bool = False,
) -> dict[str, Any]:
    """
    Flow to orchestrate TikTok comments collection.

    Args:
        video_urls: List of TikTok video URLs to scrape
        apify_api_token: Apify API token
        apify_user_id: Apify user ID (optional)
        force: Force reprocessing of existing data

    Returns:
        Pipeline execution results
    """
    return run_tiktok_task(
        video_urls=video_urls,
        apify_api_token=apify_api_token,
        apify_user_id=apify_user_id,
        force=force,
    )


@flow(
    name="Complete Data Collection Pipeline",
    description="Run all data collection pipelines in parallel",
    task_runner=ConcurrentTaskRunner() if PREFECT_AVAILABLE else None,
)
def run_all_pipelines(
    force: bool = False,
    max_bbc_articles: Optional[int] = None,
    max_hf_records: Optional[int] = None,
    sprakbanken_corpus: str = "all",
    run_wikipedia: bool = True,
    run_bbc: bool = True,
    run_huggingface: bool = True,
    run_sprakbanken: bool = True,
    run_tiktok: bool = True,
    tiktok_video_urls: Optional[list[str]] = None,
    tiktok_api_token: Optional[str] = None,
    tiktok_user_id: Optional[str] = None,
    auto_deploy: bool = False,
) -> dict[str, list[dict[str, Any]]]:
    """
    Flow to orchestrate all data collection pipelines in parallel.

    This is the main orchestration flow that coordinates execution of
    all five data sources with parallel execution where possible.

    Args:
        force: Force reprocessing of existing data
        max_bbc_articles: Maximum BBC articles to scrape
        max_hf_records: Maximum HuggingFace records to process
        sprakbanken_corpus: Specific Språkbanken corpus ID or "all"
        run_wikipedia: Enable Wikipedia pipeline
        run_bbc: Enable BBC pipeline
        run_huggingface: Enable HuggingFace pipeline
        run_sprakbanken: Enable Språkbanken pipeline
        run_tiktok: Enable TikTok pipeline
        tiktok_video_urls: List of TikTok video URLs to scrape
        tiktok_api_token: Apify API token for TikTok scraping
        tiktok_user_id: Apify user ID (optional)
        auto_deploy: Automatically deploy dashboard after pipeline completes

    Returns:
        Dictionary with results from all pipelines
    """
    import uuid
    from datetime import datetime, timezone

    from ..infra.manifest_writer import ManifestWriter

    # Generate unique run_id for this orchestration run
    run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    run_start_time = datetime.now(timezone.utc)

    logger.info("=" * 80)
    logger.info("STARTING COMPLETE DATA COLLECTION PIPELINE")
    logger.info(f"Run ID: {run_id}")
    logger.info("=" * 80)

    # Initialize manifest writer and sources dict
    manifest_writer = ManifestWriter()
    manifest_sources = {}

    # Check initial collection phase status
    in_initial_phase = is_initial_collection_phase()
    if in_initial_phase:
        logger.info("📅 Initial collection phase: All sources will run")
    else:
        logger.info("🔄 Refresh phase: Sources run per cadence schedule")

    # Execute tasks either in parallel (with Prefect) or sequentially (without Prefect)
    results = []
    skipped_sources = []

    if PREFECT_AVAILABLE:
        # Submit all tasks in parallel (Prefect handles concurrency)
        if run_wikipedia:
            should_run, reason = should_run_source("wikipedia")
            if should_run:
                logger.info(f"✅ Running Wikipedia: {reason}")
                results.append(run_wikipedia_task.submit(force=force, run_seed=run_id))
            else:
                logger.info(f"⏭️  Skipping Wikipedia: {reason}")
                skipped_sources.append(("Wikipedia-Somali", reason))

        if run_bbc:
            should_run, reason = should_run_source("bbc")
            if should_run:
                logger.info(f"✅ Running BBC: {reason}")
                results.append(
                    run_bbc_task.submit(
                        max_articles=max_bbc_articles, force=force, run_seed=run_id
                    )
                )
            else:
                logger.info(f"⏭️  Skipping BBC: {reason}")
                skipped_sources.append(("BBC-Somali", reason))

        if run_huggingface:
            should_run, reason = should_run_source("huggingface")
            if should_run:
                logger.info(f"✅ Running HuggingFace: {reason}")
                results.append(
                    run_huggingface_task.submit(
                        dataset_name="allenai/c4",
                        dataset_config="so",
                        max_records=max_hf_records,
                        force=force,
                        run_seed=run_id,
                    )
                )
            else:
                logger.info(f"⏭️  Skipping HuggingFace: {reason}")
                skipped_sources.append(("HuggingFace-Somali", reason))

        if run_sprakbanken:
            should_run, reason = should_run_source("sprakbanken")
            if should_run:
                logger.info(f"✅ Running Språkbanken: {reason}")
                results.append(
                    run_sprakbanken_task.submit(
                        corpus_id=sprakbanken_corpus, force=force, run_seed=run_id
                    )
                )
            else:
                logger.info(f"⏭️  Skipping Språkbanken: {reason}")
                skipped_sources.append(("Sprakbanken-Somali", reason))

        if run_tiktok and tiktok_video_urls and tiktok_api_token:
            should_run, reason = should_run_source("tiktok")
            if should_run:
                logger.info(f"✅ Running TikTok: {reason}")
                results.append(
                    run_tiktok_task.submit(
                        video_urls=tiktok_video_urls,
                        apify_api_token=tiktok_api_token,
                        apify_user_id=tiktok_user_id,
                        force=force,
                        run_seed=run_id,
                    )
                )
            else:
                logger.info(f"⏭️  Skipping TikTok: {reason}")
                skipped_sources.append(("TikTok-Somali", reason))
        elif run_tiktok and tiktok_video_urls:
            logger.warning("TikTok pipeline skipped: API token not provided")
        elif run_tiktok:
            logger.warning("TikTok pipeline skipped: video URLs not provided")

        # Wait for all results
        completed_results = [result.result() for result in results]
    else:
        # Run tasks sequentially without Prefect
        completed_results = []

        if run_wikipedia:
            should_run, reason = should_run_source("wikipedia")
            if should_run:
                logger.info(f"✅ Running Wikipedia: {reason}")
                completed_results.append(run_wikipedia_task(force=force, run_seed=run_id))
            else:
                logger.info(f"⏭️  Skipping Wikipedia: {reason}")
                skipped_sources.append(("Wikipedia-Somali", reason))

        if run_bbc:
            should_run, reason = should_run_source("bbc")
            if should_run:
                logger.info(f"✅ Running BBC: {reason}")
                completed_results.append(
                    run_bbc_task(max_articles=max_bbc_articles, force=force, run_seed=run_id)
                )
            else:
                logger.info(f"⏭️  Skipping BBC: {reason}")
                skipped_sources.append(("BBC-Somali", reason))

        if run_huggingface:
            should_run, reason = should_run_source("huggingface")
            if should_run:
                logger.info(f"✅ Running HuggingFace: {reason}")
                completed_results.append(
                    run_huggingface_task(
                        dataset_name="allenai/c4",
                        dataset_config="so",
                        max_records=max_hf_records,
                        force=force,
                        run_seed=run_id,
                    )
                )
            else:
                logger.info(f"⏭️  Skipping HuggingFace: {reason}")
                skipped_sources.append(("HuggingFace-Somali", reason))

        if run_sprakbanken:
            should_run, reason = should_run_source("sprakbanken")
            if should_run:
                logger.info(f"✅ Running Språkbanken: {reason}")
                completed_results.append(
                    run_sprakbanken_task(
                        corpus_id=sprakbanken_corpus, force=force, run_seed=run_id
                    )
                )
            else:
                logger.info(f"⏭️  Skipping Språkbanken: {reason}")
                skipped_sources.append(("Sprakbanken-Somali", reason))

        if run_tiktok and tiktok_video_urls and tiktok_api_token:
            should_run, reason = should_run_source("tiktok")
            if should_run:
                logger.info(f"✅ Running TikTok: {reason}")
                completed_results.append(
                    run_tiktok_task(
                        video_urls=tiktok_video_urls,
                        apify_api_token=tiktok_api_token,
                        apify_user_id=tiktok_user_id,
                        force=force,
                        run_seed=run_id,
                    )
                )
            else:
                logger.info(f"⏭️  Skipping TikTok: {reason}")
                skipped_sources.append(("TikTok-Somali", reason))
        elif run_tiktok and tiktok_video_urls:
            logger.warning("TikTok pipeline skipped: API token not provided")
        elif run_tiktok:
            logger.warning("TikTok pipeline skipped: video URLs not provided")

    # Aggregate results
    successful = [r for r in completed_results if r["status"] == "success"]
    failed = [r for r in completed_results if r["status"] == "failed"]

    # Collect manifest data from all completed results
    for result in completed_results:
        source_name = result.get("source", "unknown").lower()
        # Normalize source names for manifest
        if "wikipedia" in source_name:
            source_key = "wikipedia"
        elif "bbc" in source_name:
            source_key = "bbc"
        elif "huggingface" in source_name:
            source_key = "huggingface"
        elif "sprakbanken" in source_name:
            source_key = "sprakbanken"
        elif "tiktok" in source_name:
            source_key = "tiktok"
        else:
            source_key = source_name

        # Build manifest source entry
        manifest_sources[source_key] = {
            "status": result.get("status", "unknown"),
            "records_ingested": result.get("statistics", {}).get("processed", 0),
            "records_skipped": result.get("statistics", {}).get("skipped", 0),
            "partitions": [datetime.now(timezone.utc).strftime("%Y-%m-%d")],
            "quota_hit": result.get("quota_hit", False),
            "processing_time_seconds": result.get("processing_time", 0.0),
        }

        # Add quota info if quota was hit
        if result.get("quota_hit"):
            manifest_sources[source_key]["quota_limit"] = result.get("quota_limit")
            manifest_sources[source_key]["items_remaining"] = result.get("items_remaining", 0)

    # Generate and write manifest
    try:
        manifest = manifest_writer.create_manifest(
            run_id=run_id, sources=manifest_sources, timestamp=run_start_time
        )
        manifest_path = manifest_writer.write_manifest(manifest)
        logger.info(f"📝 Ingestion manifest written: {manifest_path}")
    except Exception as e:
        logger.error(f"Failed to write manifest: {e}")
        manifest_path = None

    logger.info("=" * 80)
    logger.info("PIPELINE EXECUTION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Successful: {len(successful)}/{len(completed_results)}")
    logger.info(f"Failed: {len(failed)}/{len(completed_results)}")
    logger.info(f"Skipped: {len(skipped_sources)}")

    if skipped_sources:
        logger.info("Skipped pipelines (cadence-based):")
        for source, reason in skipped_sources:
            logger.info(f"  - {source}: {reason}")

    if failed:
        logger.warning("Failed pipelines:")
        for result in failed:
            logger.warning(f"  - {result['source']}: {result.get('error', 'Unknown error')}")

    # Auto-deploy dashboard if requested and pipelines succeeded
    if auto_deploy and successful:
        logger.info("")
        logger.info("=" * 80)
        logger.info("AUTO-DEPLOY ENABLED: Deploying dashboard metrics...")
        logger.info("=" * 80)
        try:
            from ..deployment import DashboardDeployer, create_default_config

            config = create_default_config()
            # Set batch mode based on success count
            config.batch_mode = True
            config.min_sources_for_deploy = len(successful)

            deployer = DashboardDeployer(config)
            deploy_success = deployer.deploy(dry_run=False)

            if deploy_success:
                logger.info("Dashboard deployment successful!")
            else:
                logger.warning("Dashboard deployment was skipped or failed")
        except ImportError:
            logger.error(
                "Dashboard deployment module not available. Ensure deployment package is installed."
            )
        except Exception as e:
            logger.error(f"Dashboard deployment failed: {e}")
            logger.warning("Pipeline completed successfully but dashboard was not deployed")

    return {
        "successful": successful,
        "failed": failed,
        "total": len(completed_results),
        "run_id": run_id,
        "manifest_path": str(manifest_path) if manifest_path else None,
    }


# CLI entry point for orchestration
def main():
    """CLI entry point for running orchestration flows."""
    import argparse

    # Set up logging for orchestrator
    _setup_orchestrator_logging()

    parser = argparse.ArgumentParser(
        description="Orchestrate Somali dialect classifier data pipelines"
    )
    parser.add_argument(
        "--pipeline",
        choices=["all", "wikipedia", "bbc", "huggingface", "sprakbanken", "tiktok"],
        default="all",
        help="Pipeline to run (default: all)",
    )
    parser.add_argument("--force", action="store_true", help="Force reprocessing")
    parser.add_argument("--max-bbc-articles", type=int, help="Max BBC articles")
    parser.add_argument("--max-hf-records", type=int, help="Max HuggingFace records")
    parser.add_argument(
        "--auto-deploy",
        action="store_true",
        help="Automatically deploy dashboard after pipeline completes",
    )
    parser.add_argument(
        "--skip-sources",
        nargs="+",
        choices=["wikipedia", "bbc", "huggingface", "sprakbanken", "tiktok"],
        help="Sources to skip when running 'all' pipelines",
    )
    parser.add_argument(
        "--sprakbanken-corpus",
        type=str,
        default="all",
        help="Specific Språkbanken corpus ID to download (default: all)",
    )
    parser.add_argument(
        "--tiktok-video-urls",
        type=Path,
        help="Path to TikTok video URLs file (default: data/tiktok_urls.txt)",
    )
    parser.add_argument(
        "--tiktok-api-token",
        type=str,
        help="Apify API token for TikTok scraping (overrides env var)",
    )

    args = parser.parse_args()

    if not PREFECT_AVAILABLE:
        logger.warning(
            "Prefect not installed. Running pipelines sequentially. "
            "Install with: pip install prefect"
        )

    if args.pipeline == "all":
        # Determine which pipelines to run based on --skip-sources
        skip_sources = args.skip_sources or []

        # Handle TikTok parameters
        tiktok_video_urls = None
        tiktok_api_token = None
        tiktok_user_id = None
        should_run_tiktok = "tiktok" not in skip_sources

        if should_run_tiktok:
            # Load configuration for TikTok
            from ..infra.config import get_config

            config = get_config()

            # Get API token (CLI arg > env var). Gracefully skip if config lacks TikTok section.
            try:
                tiktok_api_token = args.tiktok_api_token or config.scraping.tiktok.apify_api_token
                tiktok_user_id = getattr(config.scraping.tiktok, "apify_user_id", None)
            except AttributeError:
                logger.warning("TikTok config not found; skipping TikTok pipeline.")
                should_run_tiktok = False

            # Determine video URLs source (CLI arg > default file location)
            default_tiktok_urls_path = Path("data/tiktok_urls.txt")
            urls_file_path = args.tiktok_video_urls or default_tiktok_urls_path

            # Load video URLs from file (default or custom path)
            if urls_file_path.exists():
                from ..cli.download_tiktoksom import load_video_urls

                try:
                    tiktok_video_urls = load_video_urls(urls_file_path)
                    source_info = "custom path" if args.tiktok_video_urls else "default location"
                    logger.info(
                        f"TikTok: Loaded {len(tiktok_video_urls)} video URLs from {source_info}: {urls_file_path}"
                    )
                except (FileNotFoundError, ValueError) as e:
                    logger.error(f"TikTok: Failed to load video URLs from {urls_file_path}: {e}")
                    logger.warning("TikTok pipeline will be skipped")
                    should_run_tiktok = False
            else:
                if args.tiktok_video_urls:
                    # User specified a path but file doesn't exist - this is an error
                    logger.error(f"TikTok: Video URLs file not found: {urls_file_path}")
                    logger.warning("TikTok pipeline will be skipped")
                else:
                    # Default file doesn't exist - this is expected/normal, just skip
                    logger.info(
                        f"TikTok: Skipping (default URLs file not found: {default_tiktok_urls_path})"
                    )
                    logger.info(
                        f"TikTok: To enable, create {default_tiktok_urls_path} or use --tiktok-video-urls"
                    )
                should_run_tiktok = False

            # Validate API token requirement
            if should_run_tiktok and not tiktok_api_token:
                logger.warning("TikTok: API token not provided, pipeline will be skipped")
                logger.info(
                    "TikTok: Set SDC_SCRAPING__TIKTOK__APIFY_API_TOKEN or use --tiktok-api-token"
                )
                should_run_tiktok = False

        result = run_all_pipelines(
            force=args.force,
            max_bbc_articles=args.max_bbc_articles,
            max_hf_records=args.max_hf_records,
            sprakbanken_corpus=args.sprakbanken_corpus,
            run_wikipedia="wikipedia" not in skip_sources,
            run_bbc="bbc" not in skip_sources,
            run_huggingface="huggingface" not in skip_sources,
            run_sprakbanken="sprakbanken" not in skip_sources,
            run_tiktok=should_run_tiktok,
            tiktok_video_urls=tiktok_video_urls,
            tiktok_api_token=tiktok_api_token,
            tiktok_user_id=tiktok_user_id,
            auto_deploy=args.auto_deploy,
        )
    elif args.pipeline == "wikipedia":
        result = run_wikipedia_pipeline(force=args.force)
    elif args.pipeline == "bbc":
        result = run_bbc_pipeline(max_articles=args.max_bbc_articles, force=args.force)
    elif args.pipeline == "huggingface":
        result = run_huggingface_pipeline(max_records=args.max_hf_records, force=args.force)
    elif args.pipeline == "sprakbanken":
        result = run_sprakbanken_pipeline(corpus_id=args.sprakbanken_corpus, force=args.force)
    elif args.pipeline == "tiktok":
        # Load configuration for TikTok
        from ..infra.config import get_config

        config = get_config()

        # Get API token (CLI arg > env var)
        api_token = args.tiktok_api_token or config.scraping.tiktok.apify_api_token

        if not api_token:
            logger.error("Apify API token not provided!")
            logger.error("Please set SDC_SCRAPING__TIKTOK__APIFY_API_TOKEN environment variable")
            logger.error("or provide --tiktok-api-token argument")
            sys.exit(1)

        if not args.tiktok_video_urls:
            logger.error("TikTok video URLs file not provided!")
            logger.error("Please provide --tiktok-video-urls argument")
            sys.exit(1)

        # Load video URLs from file
        from ..cli.download_tiktoksom import load_video_urls

        try:
            video_urls = load_video_urls(args.tiktok_video_urls)
        except (FileNotFoundError, ValueError) as e:
            logger.error(f"Failed to load video URLs: {e}")
            sys.exit(1)

        result = run_tiktok_pipeline(
            video_urls=video_urls,
            apify_api_token=api_token,
            apify_user_id=config.scraping.tiktok.apify_user_id,
            force=args.force,
        )

    # Print summary
    if isinstance(result, dict) and "successful" in result:
        print(f"\n{'=' * 80}")
        print("EXECUTION SUMMARY")
        print(f"{'=' * 80}")
        print(f"Total pipelines: {result['total']}")
        print(f"Successful: {len(result['successful'])}")
        print(f"Failed: {len(result['failed'])}")

        if result["successful"]:
            print("\n✅ Successful pipelines:")
            for r in result["successful"]:
                print(f"  - {r['source']}")

        if result["failed"]:
            print("\n❌ Failed pipelines:")
            for r in result["failed"]:
                print(f"  - {r['source']}: {r.get('error', 'Unknown')}")
            print(f"\n{'=' * 80}")
            print("PIPELINE EXECUTION FAILED")
            print(f"{'=' * 80}")
            sys.exit(1)
    else:
        print(f"\n{'=' * 80}")
        print(f"Pipeline completed: {result.get('source', 'Unknown')}")
        print(f"Status: {result.get('status', 'Unknown')}")
        if result.get("status") == "success":
            print(f"Output: {result.get('silver_path', 'Unknown')}")
        else:
            print(f"Error: {result.get('error', 'Unknown')}")
            print(f"\n{'=' * 80}")
            print("PIPELINE EXECUTION FAILED")
            print(f"{'=' * 80}")
            sys.exit(1)


if __name__ == "__main__":
    main()
