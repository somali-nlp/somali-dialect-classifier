"""
Source-specific processor implementations.

Imports all processors to trigger registration with ProcessorRegistry.
Each processor uses @register_processor decorator to auto-register itself.
"""

# Import all processors to trigger registration
from .bbc_somali_processor import BBCSomaliProcessor
from .huggingface_somali_processor import HuggingFaceSomaliProcessor
from .sprakbanken_somali_processor import SprakbankenSomaliProcessor
from .tiktok_somali_processor import TikTokSomaliProcessor
from .wikipedia_somali_processor import WikipediaSomaliProcessor

__all__ = [
    "WikipediaSomaliProcessor",
    "BBCSomaliProcessor",
    "HuggingFaceSomaliProcessor",
    "SprakbankenSomaliProcessor",
    "TikTokSomaliProcessor",
]
