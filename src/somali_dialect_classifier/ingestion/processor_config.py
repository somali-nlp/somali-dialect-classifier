"""
Processor configuration mapping for ProcessorRegistry.

Maps processor names to their configuration requirements, enabling
the registry to construct processors with correct parameters.
"""

from typing import Any, Optional


def get_processor_kwargs(
    processor_name: str,
    force: bool = False,
    run_seed: Optional[str] = None,
    **kwargs: Any
) -> dict[str, Any]:
    """
    Get constructor kwargs for a processor by name.

    Args:
        processor_name: Registered processor name
        force: Force reprocessing of existing data
        run_seed: Seed for run ID generation
        **kwargs: Processor-specific parameters

    Returns:
        Dictionary of constructor arguments

    Raises:
        ValueError: If processor name unknown
    """
    # Base kwargs common to all processors
    base_kwargs = {
        "force": force,
        "run_seed": run_seed,
    }

    # Processor-specific parameter mapping
    if processor_name == "wikipedia":
        # Wikipedia has no additional required parameters
        return base_kwargs

    elif processor_name == "bbc":
        # BBC supports max_articles parameter
        processor_kwargs = base_kwargs.copy()
        if "max_articles" in kwargs:
            processor_kwargs["max_articles"] = kwargs["max_articles"]
        return processor_kwargs

    elif processor_name == "huggingface":
        # HuggingFace requires dataset configuration
        processor_kwargs = base_kwargs.copy()
        processor_kwargs.update({
            "dataset_name": kwargs.get("dataset_name", "allenai/c4"),
            "dataset_config": kwargs.get("dataset_config", "so"),
            "url_field": kwargs.get("url_field", "url"),
            "max_records": kwargs.get("max_records"),
        })
        return processor_kwargs

    elif processor_name == "sprakbanken":
        # Språkbanken supports corpus_id parameter
        processor_kwargs = base_kwargs.copy()
        if "corpus_id" in kwargs:
            processor_kwargs["corpus_id"] = kwargs["corpus_id"]
        return processor_kwargs

    elif processor_name == "tiktok":
        # TikTok requires Apify credentials and video URLs
        processor_kwargs = base_kwargs.copy()
        processor_kwargs.update({
            "apify_api_token": kwargs.get("apify_api_token"),
            "apify_user_id": kwargs.get("apify_user_id"),
            "video_urls": kwargs.get("video_urls"),
        })
        return processor_kwargs

    else:
        raise ValueError(f"Unknown processor: {processor_name}")


def get_processor_source_name(processor_name: str, **kwargs: Any) -> str:
    """
    Get the display source name for a processor.

    Args:
        processor_name: Registered processor name
        **kwargs: Processor-specific parameters

    Returns:
        Human-readable source name
    """
    source_names = {
        "wikipedia": "Wikipedia-Somali",
        "bbc": "BBC-Somali",
        "sprakbanken": "Sprakbanken-Somali",
        "tiktok": "TikTok-Somali",
    }

    # HuggingFace source name depends on dataset
    if processor_name == "huggingface":
        dataset_name = kwargs.get("dataset_name", "allenai/c4")
        dataset_slug = dataset_name.split("/")[-1]
        return f"HuggingFace-Somali_{dataset_slug}"

    # Språkbanken source name depends on corpus
    if processor_name == "sprakbanken":
        corpus_id = kwargs.get("corpus_id", "all")
        return f"Sprakbanken-Somali-{corpus_id}"

    return source_names.get(processor_name, processor_name.capitalize())
