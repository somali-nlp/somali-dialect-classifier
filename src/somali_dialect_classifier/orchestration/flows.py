"""
Prefect workflows for orchestrating data collection pipelines.

Provides coordinated execution of all four data sources with:
- Parallel execution where possible
- Error handling and retry logic
- Progress tracking and notifications
- Quality monitoring
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import timedelta

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


@task(retries=2, retry_delay_seconds=300)
def run_wikipedia_task(force: bool = False) -> Dict[str, Any]:
    """
    Task to run Wikipedia data collection pipeline.

    Args:
        force: Force reprocessing of existing data

    Returns:
        Dictionary with pipeline results and metrics
    """
    from ..preprocessing.wikipedia_somali_processor import WikipediaSomaliProcessor

    logger.info("Starting Wikipedia pipeline...")
    processor = WikipediaSomaliProcessor(force=force)

    try:
        silver_path = processor.process()

        # Get statistics from ledger
        stats = processor.ledger.get_statistics("wikipedia")

        return {
            "source": "Wikipedia-Somali",
            "status": "success",
            "silver_path": str(silver_path),
            "statistics": stats,
        }
    except Exception as e:
        logger.error(f"Wikipedia pipeline failed: {e}")
        return {
            "source": "Wikipedia-Somali",
            "status": "failed",
            "error": str(e),
        }


@task(retries=2, retry_delay_seconds=300)
def run_bbc_task(max_articles: Optional[int] = None, force: bool = False) -> Dict[str, Any]:
    """
    Task to run BBC Somali data collection pipeline.

    Args:
        max_articles: Maximum articles to scrape (None = unlimited)
        force: Force reprocessing of existing data

    Returns:
        Dictionary with pipeline results and metrics
    """
    from ..preprocessing.bbc_somali_processor import BBCSomaliProcessor

    logger.info("Starting BBC pipeline...")
    processor = BBCSomaliProcessor(max_articles=max_articles, force=force)

    try:
        silver_path = processor.process()

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


@task(retries=2, retry_delay_seconds=300)
def run_huggingface_task(
    dataset_name: str = "allenai/c4",
    dataset_config: str = "so",
    max_records: Optional[int] = None,
    force: bool = False
) -> Dict[str, Any]:
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
    from ..preprocessing.huggingface_somali_processor import HuggingFaceSomaliProcessor

    logger.info(f"Starting HuggingFace pipeline: {dataset_name}...")
    processor = HuggingFaceSomaliProcessor(
        dataset_name=dataset_name,
        dataset_config=dataset_config,
        max_records=max_records,
        force=force,
    )

    try:
        silver_path = processor.process()

        # Get statistics
        dataset_slug = dataset_name.split('/')[-1]
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


@task(retries=2, retry_delay_seconds=300)
def run_sprakbanken_task(corpus_id: str = "all", force: bool = False) -> Dict[str, Any]:
    """
    Task to run Språkbanken corpora collection pipeline.

    Args:
        corpus_id: Specific corpus ID or "all" for all 23 corpora
        force: Force reprocessing of existing data

    Returns:
        Dictionary with pipeline results and metrics
    """
    from ..preprocessing.sprakbanken_somali_processor import SprakbankenSomaliProcessor

    logger.info(f"Starting Språkbanken pipeline: {corpus_id}...")
    processor = SprakbankenSomaliProcessor(corpus_id=corpus_id, force=force)

    try:
        silver_path = processor.process()

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


@flow(
    name="Wikipedia Data Collection",
    description="Collect and process Wikipedia Somali articles",
)
def run_wikipedia_pipeline(force: bool = False) -> Dict[str, Any]:
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
def run_bbc_pipeline(max_articles: Optional[int] = None, force: bool = False) -> Dict[str, Any]:
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
    force: bool = False
) -> Dict[str, Any]:
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
def run_sprakbanken_pipeline(corpus_id: str = "all", force: bool = False) -> Dict[str, Any]:
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
    name="Complete Data Collection Pipeline",
    description="Run all data collection pipelines in parallel",
    task_runner=ConcurrentTaskRunner() if PREFECT_AVAILABLE else None,
)
def run_all_pipelines(
    force: bool = False,
    max_bbc_articles: Optional[int] = None,
    max_hf_records: Optional[int] = None,
    run_wikipedia: bool = True,
    run_bbc: bool = True,
    run_huggingface: bool = True,
    run_sprakbanken: bool = True,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Flow to orchestrate all data collection pipelines in parallel.

    This is the main orchestration flow that coordinates execution of
    all four data sources with parallel execution where possible.

    Args:
        force: Force reprocessing of existing data
        max_bbc_articles: Maximum BBC articles to scrape
        max_hf_records: Maximum HuggingFace records to process
        run_wikipedia: Enable Wikipedia pipeline
        run_bbc: Enable BBC pipeline
        run_huggingface: Enable HuggingFace pipeline
        run_sprakbanken: Enable Språkbanken pipeline

    Returns:
        Dictionary with results from all pipelines
    """
    logger.info("=" * 80)
    logger.info("STARTING COMPLETE DATA COLLECTION PIPELINE")
    logger.info("=" * 80)

    # Submit all tasks in parallel (Prefect handles concurrency)
    results = []

    if run_wikipedia:
        results.append(run_wikipedia_task.submit(force=force))

    if run_bbc:
        results.append(run_bbc_task.submit(max_articles=max_bbc_articles, force=force))

    if run_huggingface:
        results.append(run_huggingface_task.submit(
            dataset_name="allenai/c4",
            dataset_config="so",
            max_records=max_hf_records,
            force=force,
        ))

    if run_sprakbanken:
        results.append(run_sprakbanken_task.submit(corpus_id="all", force=force))

    # Wait for all results
    completed_results = [result.result() for result in results]

    # Aggregate results
    successful = [r for r in completed_results if r["status"] == "success"]
    failed = [r for r in completed_results if r["status"] == "failed"]

    logger.info("=" * 80)
    logger.info("PIPELINE EXECUTION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Successful: {len(successful)}/{len(completed_results)}")
    logger.info(f"Failed: {len(failed)}/{len(completed_results)}")

    if failed:
        logger.warning("Failed pipelines:")
        for result in failed:
            logger.warning(f"  - {result['source']}: {result.get('error', 'Unknown error')}")

    return {
        "successful": successful,
        "failed": failed,
        "total": len(completed_results),
    }


# CLI entry point for orchestration
def main():
    """CLI entry point for running orchestration flows."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Orchestrate Somali dialect classifier data pipelines"
    )
    parser.add_argument(
        "--pipeline",
        choices=["all", "wikipedia", "bbc", "huggingface", "sprakbanken"],
        default="all",
        help="Pipeline to run (default: all)",
    )
    parser.add_argument("--force", action="store_true", help="Force reprocessing")
    parser.add_argument("--max-bbc-articles", type=int, help="Max BBC articles")
    parser.add_argument("--max-hf-records", type=int, help="Max HuggingFace records")

    args = parser.parse_args()

    if not PREFECT_AVAILABLE:
        logger.warning(
            "Prefect not installed. Running pipelines sequentially. "
            "Install with: pip install prefect"
        )

    if args.pipeline == "all":
        result = run_all_pipelines(
            force=args.force,
            max_bbc_articles=args.max_bbc_articles,
            max_hf_records=args.max_hf_records,
        )
    elif args.pipeline == "wikipedia":
        result = run_wikipedia_pipeline(force=args.force)
    elif args.pipeline == "bbc":
        result = run_bbc_pipeline(max_articles=args.max_bbc_articles, force=args.force)
    elif args.pipeline == "huggingface":
        result = run_huggingface_pipeline(max_records=args.max_hf_records, force=args.force)
    elif args.pipeline == "sprakbanken":
        result = run_sprakbanken_pipeline(force=args.force)

    # Print summary
    if isinstance(result, dict) and "successful" in result:
        print(f"\n{'='*80}")
        print(f"EXECUTION SUMMARY")
        print(f"{'='*80}")
        print(f"Total pipelines: {result['total']}")
        print(f"Successful: {len(result['successful'])}")
        print(f"Failed: {len(result['failed'])}")

        if result['successful']:
            print(f"\n✅ Successful pipelines:")
            for r in result['successful']:
                print(f"  - {r['source']}")

        if result['failed']:
            print(f"\n❌ Failed pipelines:")
            for r in result['failed']:
                print(f"  - {r['source']}: {r.get('error', 'Unknown')}")
    else:
        print(f"\n{'='*80}")
        print(f"Pipeline completed: {result.get('source', 'Unknown')}")
        print(f"Status: {result.get('status', 'Unknown')}")
        if result.get('status') == 'success':
            print(f"Output: {result.get('silver_path', 'Unknown')}")
        else:
            print(f"Error: {result.get('error', 'Unknown')}")


if __name__ == "__main__":
    main()
