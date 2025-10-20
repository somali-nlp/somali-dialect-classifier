from .wikipedia_somali_processor import WikipediaSomaliProcessor
from .bbc_somali_processor import BBCSomaliProcessor
from .text_cleaners import (
    WikiMarkupCleaner,
    WhitespaceCleaner,
    HTMLCleaner,
    TextCleaningPipeline,
    create_wikipedia_cleaner,
    create_html_cleaner,
)
from .record_utils import (
    generate_text_hash,
    generate_record_id,
    count_tokens,
    build_silver_record,
)
from .silver_writer import SilverDatasetWriter

# Backwards compatibility alias
SomaliWikipediaProcessor = WikipediaSomaliProcessor

__all__ = [
    # Processors
    "WikipediaSomaliProcessor",
    "BBCSomaliProcessor",
    "SomaliWikipediaProcessor",  # Legacy
    # Text cleaning
    "WikiMarkupCleaner",
    "WhitespaceCleaner",
    "HTMLCleaner",
    "TextCleaningPipeline",
    "create_wikipedia_cleaner",
    "create_html_cleaner",
    # Record utilities
    "generate_text_hash",
    "generate_record_id",
    "count_tokens",
    "build_silver_record",
    # Dataset writing
    "SilverDatasetWriter",
]


