"""
Configuration management for Somali Dialect Classifier.

Uses pydantic-settings for declarative configuration with environment variable support.

Usage:
    # Load from environment variables or defaults
    from somdialc.infra.config import get_config
    config = get_config()

    # Access settings
    print(config.data.raw_dir)
    print(config.scraping.bbc.max_articles)

Environment variables:
    SDC_DATA__RAW_DIR: Override raw data directory
    SDC_DATA__SILVER_DIR: Override silver data directory
    SDC_SCRAPING__BBC__MAX_ARTICLES: Override BBC max articles
    SDC_SCRAPING__WIKIPEDIA__BATCH_SIZE: Override Wikipedia batch size
    SDC_LOGGING__LEVEL: Override logging level
    SDC_RUN__PURPOSE: Override run purpose (production|validation|test)
    SDC_CAMPAIGN__ID: Override campaign ID
    SDC_CAMPAIGN__DURATION_DAYS: Override campaign duration in days

Configuration file:
    Create a .env file in the project root or set SDC_CONFIG_FILE env var:

    # .env
    SDC_DATA__RAW_DIR=/custom/path/raw
    SDC_SCRAPING__BBC__MAX_ARTICLES=500
    SDC_LOGGING__LEVEL=DEBUG

Requirements:
    pydantic>=2.5 and pydantic-settings>=2.1 are required core dependencies.
    Install with: pip install "somali-dialect-classifier[config]"
"""

from pathlib import Path
from typing import Literal, Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DataConfig(BaseSettings):
    """Data paths configuration."""

    model_config = SettingsConfigDict(
        env_prefix="SDC_DATA__", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    raw_dir: Path = Field(default=Path("data/raw"), description="Directory for raw scraped data")
    silver_dir: Path = Field(
        default=Path("data/processed/silver"),
        description="Directory for cleaned silver data (Parquet format)",
    )
    staging_dir: Path = Field(
        default=Path("data/staging"), description="Directory for intermediate staging files"
    )
    processed_dir: Path = Field(
        default=Path("data/processed"), description="Directory for processed text files"
    )
    metrics_dir: Path = Field(
        default=Path("data/metrics"), description="Directory for metrics and telemetry files"
    )
    reports_dir: Path = Field(
        default=Path("data/reports"), description="Directory for quality reports and summaries"
    )

    # Retention policy
    raw_retention_days: Optional[int] = Field(
        default=None, description="Number of days to retain raw files (None = keep forever)"
    )
    enable_auto_cleanup: bool = Field(
        default=False, description="Automatically cleanup old raw files after processing"
    )


class BBCScrapingConfig(BaseSettings):
    """BBC scraping configuration."""

    model_config = SettingsConfigDict(
        env_prefix="SDC_SCRAPING__BBC__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    max_articles: Optional[int] = Field(
        default=None, description="Maximum articles to scrape (None = unlimited)"
    )
    min_delay: float = Field(default=1.0, description="Minimum delay between requests (seconds)")
    max_delay: float = Field(default=3.0, description="Maximum delay between requests (seconds)")
    timeout: int = Field(default=30, description="Request timeout (seconds)")
    user_agent: str = Field(
        default="Mozilla/5.0 (compatible; SomaliNLPBot/1.0)",
        description="User agent string for requests",
    )

    # RSS feed configuration
    rss_feeds: list = Field(
        default_factory=lambda: [
            "https://www.bbc.com/somali/index.xml",
            "https://feeds.bbci.co.uk/somali/rss.xml",
        ],
        description="List of RSS feed URLs to scrape",
    )
    max_items_per_feed: Optional[int] = Field(
        default=100, description="Maximum items to extract per RSS feed (None = unlimited)"
    )
    check_frequency_hours: int = Field(
        default=24, description="Minimum hours between RSS feed checks"
    )

    # Rate limiting configuration
    delay_range: tuple = Field(
        default=(3, 6), description="Min and max delay between requests (seconds)"
    )
    max_requests_per_hour: Optional[int] = Field(
        default=60, description="Maximum requests per hour (None = unlimited)"
    )
    backoff_multiplier: float = Field(
        default=2.0, description="Exponential backoff multiplier on errors"
    )
    max_backoff: float = Field(
        default=300.0, description="Maximum backoff time in seconds (5 minutes)"
    )
    jitter: bool = Field(default=True, description="Add random jitter to delays")


class WikipediaScrapingConfig(BaseSettings):
    """Wikipedia scraping configuration."""

    model_config = SettingsConfigDict(
        env_prefix="SDC_SCRAPING__WIKIPEDIA__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    batch_size: int = Field(default=100, description="Number of articles to fetch per batch")
    max_articles: Optional[int] = Field(
        default=None, description="Maximum articles to fetch (None = unlimited)"
    )
    timeout: int = Field(default=30, description="Request timeout (seconds)")

    # Buffer management configuration
    buffer_chunk_size_mb: int = Field(
        default=1,
        description="XML buffer chunk size in MB",
        ge=1,
        le=10,
    )
    buffer_max_size_mb: int = Field(
        default=10,
        description="Max XML buffer size before truncation (MB)",
        ge=1,
        le=100,
    )
    buffer_truncate_size_mb: int = Field(
        default=1,
        description="Buffer size to keep after truncation (MB)",
        ge=1,
        le=10,
    )


class HuggingFaceScrapingConfig(BaseSettings):
    """HuggingFace datasets configuration."""

    model_config = SettingsConfigDict(
        env_prefix="SDC_SCRAPING__HUGGINGFACE__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    streaming_batch_size: int = Field(default=5000, description="Records per JSONL batch file")
    max_records: Optional[int] = Field(
        default=None, description="Maximum records to process (None = unlimited)"
    )
    min_length_threshold: int = Field(
        default=100, description="Minimum text length for quality filter (chars)"
    )
    langid_confidence_threshold: float = Field(
        default=0.3, description="Language detection confidence threshold (0-1)"
    )
    resume_enabled: bool = Field(
        default=True, description="Enable resume from last offset on failure"
    )

    # Dataset revision pinning
    default_dataset: str = Field(default="mc4", description="Default dataset to load")
    dataset_config: str = Field(default="so", description="Dataset configuration (language code)")
    revision: Optional[str] = Field(
        default=None,
        description="Git revision/commit hash to pin dataset version (None = latest)",
    )


class SprakbankenScrapingConfig(BaseSettings):
    """Språkbanken corpora configuration."""

    model_config = SettingsConfigDict(
        env_prefix="SDC_SCRAPING__SPRAKBANKEN__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    batch_size: int = Field(default=5000, description="Batch size for processing")
    max_corpora: Optional[int] = Field(
        default=None, description="Maximum number of corpora to process (None = all 23)"
    )
    timeout: int = Field(default=30, description="Request timeout (seconds)")
    xml_parse_timeout: int = Field(
        default=300, description="XML parsing timeout for large files (seconds)"
    )
    min_length_threshold: int = Field(
        default=20, description="Minimum text length for quality filter (tokens)"
    )
    langid_confidence_threshold: float = Field(
        default=0.3, description="Language detection confidence threshold (0-1)"
    )


class TikTokScrapingConfig(BaseSettings):
    """TikTok scraping configuration via Apify."""

    model_config = SettingsConfigDict(
        env_prefix="SDC_SCRAPING__TIKTOK__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Apify credentials
    apify_api_token: Optional[SecretStr] = Field(
        default=None, description="Apify API token (required for TikTok scraping)"
    )
    apify_user_id: Optional[str] = Field(
        default=None, description="Apify user ID (optional, for reference)"
    )

    # Scraping limits
    max_comments_per_video: Optional[int] = Field(
        default=None, description="Max comments per video (None = unlimited)"
    )
    max_total_comments: Optional[int] = Field(
        default=30000, description="Target total comments to collect"
    )

    # Hard per-run spend cap — enforced in ApifyTikTokClient before the POST.
    # At $1 / 1,000 raw comments this caps the maximum charge for a single run.
    # None = no cap (operator assumes full responsibility for costs).
    # A value of 50 means the client refuses to start if the projected raw
    # comment count across all videos exceeds 50,000 comments (~$50).
    max_budget_usd: Optional[float] = Field(
        default=20.0,
        description=(
            "Hard per-run Apify spend cap in USD. "
            "At $1/1,000 raw comments, max_budget_usd=20 caps the run at ~20,000 raw comments. "
            "Set to None to disable the cap (not recommended for production). "
            "env: SDC_SCRAPING__TIKTOK__MAX_BUDGET_USD"
        ),
    )

    # Quality filters (minimal for TikTok - user pays for all comments)
    min_text_length: int = Field(
        default=3, description="Minimum comment length for linguistic value (characters)"
    )

    # Apify actor settings
    poll_interval: int = Field(default=15, description="Seconds between actor status checks")
    max_wait_time: int = Field(
        default=3600, description="Maximum wait time for actor completion (seconds)"
    )
    batch_size: int = Field(default=1000, description="Items per batch when fetching dataset")


class RunConfig(BaseSettings):
    """
    Run-level provenance configuration.

    Stamps every pipeline run with an operator-declared intent so that
    test/validation rows can be distinguished from production rows in
    the ledger and in silver source_metadata.

    Environment Variables:
        SDC_RUN__PURPOSE: Run intent — 'production', 'validation', or 'test'
                          (default: 'production')

    Examples:
        >>> config = RunConfig()
        >>> config.purpose
        'production'
        >>> # Override via env: SDC_RUN__PURPOSE=validation
    """

    model_config = SettingsConfigDict(
        env_prefix="SDC_RUN__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    purpose: Literal["production", "validation", "test"] = Field(
        default="production",
        description=(
            "Operator-declared run intent. "
            "'production' — campaign data run; "
            "'validation' — pre-campaign dry-run; "
            "'test' — automated test suite invocation."
        ),
    )


class CampaignConfig(BaseSettings):
    """
    Campaign identity and duration configuration.

    Provides the campaign ID and planned duration that flow.py uses to
    initialise the campaigns table row and that silver source_metadata
    carries for downstream provenance.

    Environment Variables:
        SDC_CAMPAIGN__ID: Campaign identifier (default: 'campaign_init_001')
        SDC_CAMPAIGN__DURATION_DAYS: Planned campaign length in days (default: 6)

    Examples:
        >>> config = CampaignConfig()
        >>> config.id
        'campaign_init_001'
        >>> config.duration_days
        6
    """

    model_config = SettingsConfigDict(
        env_prefix="SDC_CAMPAIGN__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    id: str = Field(
        default="campaign_init_001",
        description="Unique campaign identifier used in the campaigns table and silver metadata.",
    )
    duration_days: int = Field(
        default=6,
        description="Planned campaign duration in days (informational; auto-completion not wired).",
        ge=1,
        le=365,
    )


class DatabaseConfig(BaseSettings):
    """
    Database configuration.

    Controls PostgreSQL connection and query behavior.

    Environment Variables:
        SDC_DATABASE__QUERY_TIMEOUT: PostgreSQL query timeout in seconds (default: 30)
        SDC_DATABASE__MIN_CONNECTIONS: Minimum connection pool size (default: 2)
        SDC_DATABASE__MAX_CONNECTIONS: Maximum connection pool size (default: 10)
    """

    model_config = SettingsConfigDict(
        env_prefix="SDC_DATABASE__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    query_timeout: int = Field(
        default=30,
        description="PostgreSQL query timeout in seconds",
        ge=1,
        le=300,
    )
    min_connections: int = Field(
        default=2,
        description="Minimum connection pool size",
        ge=1,
        le=10,
    )
    max_connections: int = Field(
        default=10,
        description="Maximum connection pool size",
        ge=1,
        le=100,
    )


class HTTPConfig(BaseSettings):
    """
    HTTP request configuration with timeout enforcement.

    Prevents silent hangs on network failures by enforcing timeouts on all HTTP requests.

    Environment Variables:
        SDC_HTTP__REQUEST_TIMEOUT: Total request timeout in seconds (default: 30)
        SDC_HTTP__CONNECT_TIMEOUT: Connection timeout in seconds (default: 10)

    Examples:
        >>> config = HTTPConfig()
        >>> config.request_timeout
        30
        >>> config.connect_timeout
        10
    """

    model_config = SettingsConfigDict(
        env_prefix="SDC_HTTP__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    request_timeout: int = Field(
        default=30,
        description="HTTP request timeout in seconds (total time for request)",
        ge=1,
        le=600,
    )
    connect_timeout: int = Field(
        default=10,
        description="Connection timeout in seconds (time to establish connection)",
        ge=1,
        le=60,
    )


class DiskConfig(BaseSettings):
    """
    Disk space management configuration.

    Prevents data loss from full disk scenarios by enforcing pre-flight
    space checks before large writes.

    Environment Variables:
        SDC_DISK__MIN_FREE_SPACE_GB: Minimum free space required (GB)
        SDC_DISK__SPACE_BUFFER_PCT: Safety buffer percentage (0.0-1.0)

    Examples:
        >>> config = DiskConfig()
        >>> config.min_free_space_gb
        5
        >>> config.space_buffer_pct
        0.1
    """

    model_config = SettingsConfigDict(
        env_prefix="SDC_DISK__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    min_free_space_gb: int = Field(
        default=5,
        description="Minimum free disk space to maintain after writes (GB)",
        ge=1,
        le=1000,
    )
    space_buffer_pct: float = Field(
        default=0.1,
        description="Safety buffer percentage for space calculations (0.1 = 10%)",
        ge=0.0,
        le=0.5,
    )


class DedupSettings(BaseSettings):
    """
    Deduplication configuration.

    Controls exact and near-duplicate detection across all data sources.
    Ensures consistent deduplication thresholds and cache sizes.

    Environment Variables:
        SDC_DEDUP__HASH_FIELDS: Fields to include in hash (default: ["text", "url"])
        SDC_DEDUP__ENABLE_MINHASH: Enable MinHash near-duplicate detection (default: True)
        SDC_DEDUP__SIMILARITY_THRESHOLD: Jaccard similarity threshold (default: 0.85)
        SDC_DEDUP__CACHE_SIZE: LRU cache size for hash storage (default: 100000)
        SDC_DEDUP__NUM_SHARDS: Number of LSH shards for performance (default: 10)

    Examples:
        >>> config = DedupSettings()
        >>> config.similarity_threshold
        0.85
        >>> config.cache_size
        100000
    """

    model_config = SettingsConfigDict(
        env_prefix="SDC_DEDUP__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    hash_fields: list[str] = Field(
        default_factory=lambda: ["text", "url"],
        description="Fields to include in content hash for exact deduplication",
    )
    enable_minhash: bool = Field(
        default=True, description="Enable MinHash-based near-duplicate detection"
    )
    similarity_threshold: float = Field(
        default=0.85,
        description="Jaccard similarity threshold for near-duplicates (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )
    cache_size: int = Field(
        default=100_000,
        description="Maximum number of hashes to store in LRU cache",
        ge=1000,
    )
    num_shards: int = Field(
        default=10,
        description="Number of LSH shards for performance optimization",
        ge=1,
        le=100,
    )


class OrchestrationConfig(BaseSettings):
    """
    Orchestration and scheduling configuration.

    Controls the initial collection phase duration and per-source
    refresh cadences for the 6-day ingestion pipeline.

    Environment Variables:
        SDC_ORCHESTRATION__INITIAL_COLLECTION_DAYS: Days for initial collection phase (1-30)
        SDC_ORCHESTRATION__DEFAULT_CADENCE_DAYS: Default refresh cadence (1-365)
        SDC_ORCHESTRATION__CADENCE_DAYS__<SOURCE>: Per-source cadence override
        SDC_ORCHESTRATION__QUOTA_LIMITS__<SOURCE>: Daily quota per source (records/day)

    Examples:
        >>> config = OrchestrationConfig()
        >>> config.initial_collection_days
        7
        >>> config.get_cadence("wikipedia")
        7
        >>> config.get_cadence("huggingface")
        30
        >>> config.get_quota("bbc")
        350
    """

    model_config = SettingsConfigDict(
        env_prefix="SDC_ORCHESTRATION__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Initial collection phase
    initial_collection_days: int = Field(
        default=7,
        description="Days to collect all sources daily before switching to cadence-based refresh",
        ge=1,
        le=30,
    )

    # Default fallback cadence
    default_cadence_days: int = Field(
        default=7,
        description="Default refresh cadence in days for sources not explicitly configured",
        ge=1,
        le=365,
    )

    # Per-source refresh cadences
    cadence_days: dict[str, int] = Field(
        default_factory=lambda: {
            "wikipedia": 7,  # Weekly - content changes moderately
            "bbc": 7,  # Weekly - news refresh
            "huggingface": 30,  # Monthly - large static dataset
            "sprakbanken": 90,  # Quarterly - academic corpus
            "tiktok": 7,  # Weekly - manual scheduling
        },
        description="Per-source refresh cadence in days",
    )

    # Per-source daily quotas
    quota_limits: dict[str, int] = Field(
        default_factory=lambda: {
            "bbc": 350,  # 350 articles/day - respects rate limits
            "huggingface": 20000,  # 20k records/day - large dataset throttling
            "sprakbanken": 10,  # 10 corpora/day - academic corpus pacing
            # wikipedia: No quota (file-based, efficient)
            # tiktok: Manual scheduling with cost gating (no automatic quota)
        },
        description="Daily quota limits per source (None = unlimited)",
    )

    def get_cadence(self, source: str) -> int:
        """
        Get refresh cadence for a specific source.

        Args:
            source: Data source name (e.g., 'wikipedia', 'bbc')

        Returns:
            Cadence in days for the source, or default_cadence_days if not configured

        Examples:
            >>> config = OrchestrationConfig()
            >>> config.get_cadence("wikipedia")
            7
            >>> config.get_cadence("unknown_source")
            7
        """
        source_normalized = source.lower().strip()
        return self.cadence_days.get(source_normalized, self.default_cadence_days)

    def get_quota(self, source: str) -> Optional[int]:
        """
        Get daily quota limit for a specific source.

        Args:
            source: Data source name (e.g., 'bbc', 'huggingface')

        Returns:
            Daily quota limit (records/day), or None if unlimited

        Examples:
            >>> config = OrchestrationConfig()
            >>> config.get_quota("bbc")
            350
            >>> config.get_quota("wikipedia")
            None
        """
        source_normalized = source.lower().strip()
        return self.quota_limits.get(source_normalized)


class ScrapingConfig(BaseSettings):
    """Scraping configuration."""

    model_config = SettingsConfigDict(
        env_prefix="SDC_SCRAPING__", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    bbc: BBCScrapingConfig = Field(default_factory=BBCScrapingConfig)
    wikipedia: WikipediaScrapingConfig = Field(default_factory=WikipediaScrapingConfig)
    huggingface: HuggingFaceScrapingConfig = Field(default_factory=HuggingFaceScrapingConfig)
    sprakbanken: SprakbankenScrapingConfig = Field(default_factory=SprakbankenScrapingConfig)
    tiktok: TikTokScrapingConfig = Field(default_factory=TikTokScrapingConfig)


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    model_config = SettingsConfigDict(
        env_prefix="SDC_LOGGING__", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    level: str = Field(default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)")
    log_dir: Path = Field(default=Path("logs"), description="Directory for log files")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format",
    )


class Config(BaseSettings):
    """Main configuration."""

    model_config = SettingsConfigDict(
        env_prefix="SDC_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    data: DataConfig = Field(default_factory=DataConfig)
    scraping: ScrapingConfig = Field(default_factory=ScrapingConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    orchestration: OrchestrationConfig = Field(default_factory=OrchestrationConfig)
    dedup: DedupSettings = Field(default_factory=DedupSettings)
    http: HTTPConfig = Field(default_factory=HTTPConfig)
    disk: DiskConfig = Field(default_factory=DiskConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    run: RunConfig = Field(default_factory=RunConfig)
    campaign: CampaignConfig = Field(default_factory=CampaignConfig)


# Singleton instance
_config: Optional[Config] = None


def get_config(reload: bool = False) -> Config:
    """
    Get the global configuration instance.

    Args:
        reload: If True, reload configuration from environment

    Returns:
        Config instance
    """
    global _config

    if _config is None or reload:
        _config = Config()

    return _config


def reset_config():
    """Reset configuration to defaults (useful for testing)."""
    global _config
    _config = None
