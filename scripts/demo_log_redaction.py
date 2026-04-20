#!/usr/bin/env python3
"""
Demonstration script for log redaction functionality.

Shows before/after examples of secret exposure prevention in logs.
"""

import json
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from somali_dialect_classifier.infra.logging_utils import (
    StructuredFormatter,
    set_context,
    clear_context,
    log_event,
    LogEvent,
)
from somali_dialect_classifier.infra.security import redact_secrets


def demo_basic_redaction():
    """Demonstrate basic secret redaction."""
    print("=" * 80)
    print("DEMO 1: Basic Secret Redaction")
    print("=" * 80)

    # Example data with secrets
    data = {
        "username": "admin",
        "password": "SuperSecret123456",
        "api_key": "sk_live_abc123def456ghi789",
        "apify_api_token": "apify_api_abcdefgh12345678",
        "huggingface_token": "hf_aBcDeFgHiJkLmNoPqRsTuVwXyZ123456",
        "database_host": "db.example.com",
        "max_workers": 10,
    }

    print("\nBEFORE REDACTION:")
    print(json.dumps(data, indent=2))

    redacted = redact_secrets(data)

    print("\nAFTER REDACTION:")
    print(json.dumps(redacted, indent=2))
    print()


def demo_nested_redaction():
    """Demonstrate nested secret redaction."""
    print("=" * 80)
    print("DEMO 2: Nested Dictionary Redaction")
    print("=" * 80)

    data = {
        "service": "data-ingestion",
        "config": {
            "scrapers": {
                "bbc": {
                    "base_url": "https://bbc.com/somali",
                    "max_articles": 350,
                },
                "tiktok": {
                    "apify_api_token": "apify_api_secret_key_12345678",
                    "max_comments": 1000,
                },
            },
            "database": {
                "host": "localhost",
                "port": 5432,
                "password": "DatabasePassword123456",
            },
        },
    }

    print("\nBEFORE REDACTION:")
    print(json.dumps(data, indent=2))

    redacted = redact_secrets(data)

    print("\nAFTER REDACTION:")
    print(json.dumps(redacted, indent=2))
    print()


def demo_logging_with_context():
    """Demonstrate log redaction with context variables."""
    print("=" * 80)
    print("DEMO 3: Logging with Context Redaction")
    print("=" * 80)

    # Setup logger
    logger = logging.getLogger("demo_redaction")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = StructuredFormatter(include_context=True, include_hostname=False)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Set context with secrets
    clear_context()
    set_context(
        run_id="20251230_120000_demo_abc123",
        source="TikTok-Somali",
        apify_api_token="apify_api_ThisIsASecret123456",
        phase="fetch",
    )

    print("\nLOG OUTPUT WITH REDACTED CONTEXT:")
    logger.info("Starting TikTok scraper")

    clear_context()
    print()


def demo_log_event_redaction():
    """Demonstrate log event redaction."""
    print("=" * 80)
    print("DEMO 4: Log Event Redaction")
    print("=" * 80)

    # Setup logger
    logger = logging.getLogger("demo_event")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = StructuredFormatter(include_context=False, include_hostname=False)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    print("\nLOG EVENT WITH API CREDENTIALS (REDACTED):")
    log_event(
        logger,
        LogEvent.FETCH_SUCCESS,
        url="https://api.apify.com/v2/actor-tasks/...",
        api_key="apify_api_secret_key_12345678",
        http_status=200,
        duration_ms=1234,
        bytes_downloaded=5678,
    )
    print()


def demo_performance():
    """Demonstrate redaction performance."""
    print("=" * 80)
    print("DEMO 5: Redaction Performance")
    print("=" * 80)

    import time

    # Create large dataset
    data = {
        f"user_{i}": {
            "username": f"user{i}",
            "email": f"user{i}@example.com",
            "api_key": f"sk_live_user{i}_secret_key_{i:06d}",
            "settings": {
                "notifications": True,
                "password": f"password_for_user_{i}_123456",
            },
        }
        for i in range(1000)
    }

    print(f"\nRedacting {len(data)} user records...")

    start = time.time()
    redacted = redact_secrets(data)
    elapsed_ms = (time.time() - start) * 1000

    print(f"Redaction completed in {elapsed_ms:.2f}ms")
    print(f"Performance: {len(data) / (elapsed_ms / 1000):.0f} records/second")

    # Verify redaction
    sample_key = "user_500"
    print(f"\nSample redaction (user_500):")
    print(f"  Original password: password_for_user_500_123456")
    print(f"  Redacted password: {redacted[sample_key]['settings']['password']}")
    print(f"  Original api_key: sk_live_user500_secret_key_000500")
    print(f"  Redacted api_key: {redacted[sample_key]['api_key']}")
    print()


def demo_real_world_scenario():
    """Demonstrate real-world logging scenario."""
    print("=" * 80)
    print("DEMO 6: Real-World Pipeline Scenario")
    print("=" * 80)

    # Setup logger
    logger = logging.getLogger("pipeline")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = StructuredFormatter(include_context=True, include_hostname=False)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    print("\nSimulating data pipeline with API credentials in context:\n")

    # Scenario 1: TikTok scraping
    clear_context()
    set_context(
        run_id="20251230_140000_tiktok_xyz789",
        source="TikTok-Somali",
        apify_api_token="apify_api_ProductionToken123456",
        phase="discovery",
    )

    logger.info("Discovered 25 TikTok videos for scraping")
    log_event(
        logger,
        LogEvent.FETCH_SUCCESS,
        url="https://www.tiktok.com/@somali_content/video/...",
        comments_count=145,
        duration_ms=890,
    )

    # Scenario 2: HuggingFace download
    clear_context()
    set_context(
        run_id="20251230_140100_hf_abc456",
        source="HuggingFace-Somali",
        huggingface_token="hf_aBcDeFgHiJkLmNoPqRsTuVwXyZ123456",
        phase="download",
    )

    logger.info("Downloading MC4 dataset from HuggingFace")
    log_event(
        logger,
        LogEvent.FETCH_SUCCESS,
        url="https://huggingface.co/datasets/mc4",
        records_downloaded=10000,
        duration_ms=5432,
    )

    clear_context()
    print()


def main():
    """Run all demonstrations."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "SECRET REDACTION DEMONSTRATION" + " " * 28 + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    demo_basic_redaction()
    demo_nested_redaction()
    demo_logging_with_context()
    demo_log_event_redaction()
    demo_performance()
    demo_real_world_scenario()

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("""
The log redaction system provides:

1. Automatic detection of 20+ sensitive key patterns (password, token, api_key, etc.)
2. Case-insensitive and partial key matching
3. Recursive redaction for nested data structures
4. Preservation of data structure and types
5. Safe masking showing only last 4 characters (or *** for short values)
6. High performance (<1ms for typical log entries, <100ms for 1000 records)
7. Integration with both JSON and colored formatters
8. Zero-configuration - works automatically in all logging contexts

Secrets are never exposed in:
- Log files (JSON or text format)
- Console output
- Log context variables
- Log event extra fields
- Exception tracebacks (when they contain context)

This prevents API tokens (Apify, HuggingFace) and other secrets from
appearing in logs, even when developers accidentally log sensitive data.
""")


if __name__ == "__main__":
    main()
