"""
Configuration management for Somali Dialect Classifier.

Uses pydantic-settings for declarative configuration with environment variable support.

Usage:
    # Load from environment variables or defaults
    from somali_dialect_classifier.config import get_config
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

Configuration file:
    Create a .env file in the project root or set SDC_CONFIG_FILE env var:

    # .env
    SDC_DATA__RAW_DIR=/custom/path/raw
    SDC_SCRAPING__BBC__MAX_ARTICLES=500
    SDC_LOGGING__LEVEL=DEBUG
"""

from pathlib import Path
from typing import Optional

try:
    from pydantic import Field
    from pydantic_settings import BaseSettings, SettingsConfigDict

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    # Fallback to simple dataclass if pydantic not installed
    from dataclasses import dataclass, field


# Pydantic-based configuration (preferred)
if PYDANTIC_AVAILABLE:

    class DataConfig(BaseSettings):
        """Data paths configuration."""

        model_config = SettingsConfigDict(
            env_prefix="SDC_DATA__", env_file=".env", env_file_encoding="utf-8", extra="ignore"
        )

        raw_dir: Path = Field(
            default=Path("data/raw"), description="Directory for raw scraped data"
        )
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
        min_delay: float = Field(
            default=1.0, description="Minimum delay between requests (seconds)"
        )
        max_delay: float = Field(
            default=3.0, description="Maximum delay between requests (seconds)"
        )
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
        dataset_config: str = Field(
            default="so", description="Dataset configuration (language code)"
        )
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
        apify_api_token: Optional[str] = Field(
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
            # Normalize source name to lowercase for case-insensitive lookup
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
            # Normalize source name to lowercase for case-insensitive lookup
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

        level: str = Field(
            default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)"
        )
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


# Fallback dataclass-based configuration (if pydantic not available)
else:

    @dataclass
    class DataConfig:
        """Data paths configuration."""

        raw_dir: Path = Path("data/raw")
        silver_dir: Path = Path("data/processed/silver")
        staging_dir: Path = Path("data/staging")
        processed_dir: Path = Path("data/processed")

    @dataclass
    class BBCScrapingConfig:
        """BBC scraping configuration."""

        max_articles: Optional[int] = None
        min_delay: float = 1.0
        max_delay: float = 3.0
        timeout: int = 30
        user_agent: str = "Mozilla/5.0 (compatible; SomaliNLPBot/1.0)"

        # RSS feed configuration
        rss_feeds: list = field(
            default_factory=lambda: [
                "https://www.bbc.com/somali/index.xml",
                "https://feeds.bbci.co.uk/somali/rss.xml",
            ]
        )
        max_items_per_feed: Optional[int] = 100
        check_frequency_hours: int = 24

        # Rate limiting configuration
        delay_range: tuple = (1, 3)
        max_requests_per_hour: Optional[int] = 100
        backoff_multiplier: float = 2.0
        max_backoff: float = 300.0
        jitter: bool = True

    @dataclass
    class WikipediaScrapingConfig:
        """Wikipedia scraping configuration."""

        batch_size: int = 100
        max_articles: Optional[int] = None
        timeout: int = 30

    @dataclass
    class HuggingFaceScrapingConfig:
        """HuggingFace datasets configuration."""

        streaming_batch_size: int = 5000
        max_records: Optional[int] = None
        min_length_threshold: int = 100
        langid_confidence_threshold: float = 0.3
        resume_enabled: bool = True

        # Dataset revision pinning
        default_dataset: str = "mc4"
        dataset_config: str = "so"
        revision: Optional[str] = None

    @dataclass
    class SprakbankenScrapingConfig:
        """Språkbanken corpora configuration."""

        batch_size: int = 5000
        max_corpora: Optional[int] = None
        timeout: int = 30
        xml_parse_timeout: int = 300
        min_length_threshold: int = 20
        langid_confidence_threshold: float = 0.3

    @dataclass
    class DedupSettings:
        """
        Deduplication configuration (fallback).

        Fallback implementation when Pydantic is unavailable.
        """

        hash_fields: list[str] = field(default_factory=lambda: ["text", "url"])
        enable_minhash: bool = True
        similarity_threshold: float = 0.85
        cache_size: int = 100_000
        num_shards: int = 10

    @dataclass
    class ScrapingConfig:
        """Scraping configuration."""

        bbc: BBCScrapingConfig = field(default_factory=BBCScrapingConfig)
        wikipedia: WikipediaScrapingConfig = field(default_factory=WikipediaScrapingConfig)
        huggingface: HuggingFaceScrapingConfig = field(default_factory=HuggingFaceScrapingConfig)
        sprakbanken: SprakbankenScrapingConfig = field(default_factory=SprakbankenScrapingConfig)

    @dataclass
    class OrchestrationConfig:
        """
        Orchestration and scheduling configuration.

        Fallback implementation when Pydantic is unavailable.
        """

        initial_collection_days: int = 6
        default_cadence_days: int = 7
        cadence_days: dict[str, int] = field(
            default_factory=lambda: {
                "wikipedia": 7,
                "bbc": 7,
                "huggingface": 30,
                "sprakbanken": 90,
                "tiktok": 7,
            }
        )
        quota_limits: dict[str, int] = field(
            default_factory=lambda: {"bbc": 350, "huggingface": 20000, "sprakbanken": 10}
        )

        def get_cadence(self, source: str) -> int:
            """Get refresh cadence for a specific source."""
            source_normalized = source.lower().strip()
            return self.cadence_days.get(source_normalized, self.default_cadence_days)

        def get_quota(self, source: str) -> Optional[int]:
            """Get daily quota limit for a specific source."""
            source_normalized = source.lower().strip()
            return self.quota_limits.get(source_normalized)

    @dataclass
    class HTTPConfig:
        """HTTP request configuration (fallback)."""

        request_timeout: int = 30
        connect_timeout: int = 10

    @dataclass
    class DiskConfig:
        """Disk space management configuration (fallback)."""

        min_free_space_gb: int = 5
        space_buffer_pct: float = 0.1

    @dataclass
    class LoggingConfig:
        """Logging configuration."""

        level: str = "INFO"
        log_dir: Path = Path("logs")
        format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @dataclass
    class Config:
        """Main configuration."""

        data: DataConfig = field(default_factory=DataConfig)
        scraping: ScrapingConfig = field(default_factory=ScrapingConfig)
        logging: LoggingConfig = field(default_factory=LoggingConfig)
        orchestration: OrchestrationConfig = field(default_factory=OrchestrationConfig)
        dedup: DedupSettings = field(default_factory=DedupSettings)
        http: HTTPConfig = field(default_factory=HTTPConfig)
        disk: DiskConfig = field(default_factory=DiskConfig)


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
