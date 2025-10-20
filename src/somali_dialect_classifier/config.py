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
            env_prefix='SDC_DATA__',
            env_file='.env',
            env_file_encoding='utf-8',
            extra='ignore'
        )

        raw_dir: Path = Field(
            default=Path('data/raw'),
            description='Directory for raw scraped data'
        )
        silver_dir: Path = Field(
            default=Path('data/processed/silver'),
            description='Directory for cleaned silver data (Parquet format)'
        )
        staging_dir: Path = Field(
            default=Path('data/staging'),
            description='Directory for intermediate staging files'
        )
        processed_dir: Path = Field(
            default=Path('data/processed'),
            description='Directory for processed text files'
        )


    class BBCScrapingConfig(BaseSettings):
        """BBC scraping configuration."""
        model_config = SettingsConfigDict(
            env_prefix='SDC_SCRAPING__BBC__',
            env_file='.env',
            env_file_encoding='utf-8',
            extra='ignore'
        )

        max_articles: Optional[int] = Field(
            default=None,
            description='Maximum articles to scrape (None = unlimited)'
        )
        min_delay: float = Field(
            default=1.0,
            description='Minimum delay between requests (seconds)'
        )
        max_delay: float = Field(
            default=3.0,
            description='Maximum delay between requests (seconds)'
        )
        timeout: int = Field(
            default=30,
            description='Request timeout (seconds)'
        )
        user_agent: str = Field(
            default='Mozilla/5.0 (compatible; SomaliNLPBot/1.0)',
            description='User agent string for requests'
        )


    class WikipediaScrapingConfig(BaseSettings):
        """Wikipedia scraping configuration."""
        model_config = SettingsConfigDict(
            env_prefix='SDC_SCRAPING__WIKIPEDIA__',
            env_file='.env',
            env_file_encoding='utf-8',
            extra='ignore'
        )

        batch_size: int = Field(
            default=100,
            description='Number of articles to fetch per batch'
        )
        max_articles: Optional[int] = Field(
            default=None,
            description='Maximum articles to fetch (None = unlimited)'
        )
        timeout: int = Field(
            default=30,
            description='Request timeout (seconds)'
        )


    class ScrapingConfig(BaseSettings):
        """Scraping configuration."""
        model_config = SettingsConfigDict(
            env_prefix='SDC_SCRAPING__',
            env_file='.env',
            env_file_encoding='utf-8',
            extra='ignore'
        )

        bbc: BBCScrapingConfig = Field(default_factory=BBCScrapingConfig)
        wikipedia: WikipediaScrapingConfig = Field(default_factory=WikipediaScrapingConfig)


    class LoggingConfig(BaseSettings):
        """Logging configuration."""
        model_config = SettingsConfigDict(
            env_prefix='SDC_LOGGING__',
            env_file='.env',
            env_file_encoding='utf-8',
            extra='ignore'
        )

        level: str = Field(
            default='INFO',
            description='Logging level (DEBUG, INFO, WARNING, ERROR)'
        )
        log_dir: Path = Field(
            default=Path('logs'),
            description='Directory for log files'
        )
        format: str = Field(
            default='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            description='Log message format'
        )


    class Config(BaseSettings):
        """Main configuration."""
        model_config = SettingsConfigDict(
            env_prefix='SDC_',
            env_file='.env',
            env_file_encoding='utf-8',
            extra='ignore'
        )

        data: DataConfig = Field(default_factory=DataConfig)
        scraping: ScrapingConfig = Field(default_factory=ScrapingConfig)
        logging: LoggingConfig = Field(default_factory=LoggingConfig)


# Fallback dataclass-based configuration (if pydantic not available)
else:
    @dataclass
    class DataConfig:
        """Data paths configuration."""
        raw_dir: Path = Path('data/raw')
        silver_dir: Path = Path('data/processed/silver')
        staging_dir: Path = Path('data/staging')
        processed_dir: Path = Path('data/processed')


    @dataclass
    class BBCScrapingConfig:
        """BBC scraping configuration."""
        max_articles: Optional[int] = None
        min_delay: float = 1.0
        max_delay: float = 3.0
        timeout: int = 30
        user_agent: str = 'Mozilla/5.0 (compatible; SomaliNLPBot/1.0)'


    @dataclass
    class WikipediaScrapingConfig:
        """Wikipedia scraping configuration."""
        batch_size: int = 100
        max_articles: Optional[int] = None
        timeout: int = 30


    @dataclass
    class ScrapingConfig:
        """Scraping configuration."""
        bbc: BBCScrapingConfig = field(default_factory=BBCScrapingConfig)
        wikipedia: WikipediaScrapingConfig = field(default_factory=WikipediaScrapingConfig)


    @dataclass
    class LoggingConfig:
        """Logging configuration."""
        level: str = 'INFO'
        log_dir: Path = Path('logs')
        format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


    @dataclass
    class Config:
        """Main configuration."""
        data: DataConfig = field(default_factory=DataConfig)
        scraping: ScrapingConfig = field(default_factory=ScrapingConfig)
        logging: LoggingConfig = field(default_factory=LoggingConfig)


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
