"""
Disk space utilities for preventing data loss on write failures.

Provides pre-flight checks before writing large datasets to ensure
sufficient disk space is available.

Usage:
    from somali_dialect_classifier.infra.disk_utils import check_disk_space

    # Check if 1GB is available
    has_space, error_msg = check_disk_space(1024**3, Path("/data"))
    if not has_space:
        raise InsufficientDiskSpaceError(error_msg)
"""

import shutil
from pathlib import Path
from typing import Optional


class InsufficientDiskSpaceError(Exception):
    """Raised when insufficient disk space is available for operation."""

    def __init__(self, required: int, available: int, path: Path):
        """
        Initialize error with disk space details.

        Args:
            required: Required bytes
            available: Available bytes
            path: Path being checked
        """
        self.required = required
        self.available = available
        self.path = path

        required_gb = required / (1024**3)
        available_gb = available / (1024**3)

        super().__init__(
            f"Insufficient disk space: need {required_gb:.2f}GB, "
            f"have {available_gb:.2f}GB at {path}"
        )


def get_available_disk_space(path: Path) -> int:
    """
    Get available disk space at path in bytes.

    Args:
        path: Directory path to check (uses parent if file)

    Returns:
        Available disk space in bytes

    Raises:
        FileNotFoundError: If path does not exist

    Example:
        >>> space = get_available_disk_space(Path("/data"))
        >>> print(f"Available: {space / (1024**3):.2f}GB")
        Available: 125.34GB
    """
    # Use parent directory if path is a file or doesn't exist yet
    check_path = path if path.is_dir() else path.parent

    # Ensure parent exists
    if not check_path.exists():
        check_path.mkdir(parents=True, exist_ok=True)

    # Get disk usage statistics
    stat = shutil.disk_usage(check_path)
    return stat.free


def check_disk_space(
    required_bytes: int, path: Path, buffer_pct: float = 0.1, min_free_gb: Optional[float] = None
) -> tuple[bool, str]:
    """
    Check if sufficient disk space is available.

    Applies a safety buffer (default 10%) to prevent edge cases where
    the OS requires additional space.

    Args:
        required_bytes: Required space in bytes
        path: Path where data will be written
        buffer_pct: Safety buffer percentage (default: 0.1 = 10%)
        min_free_gb: Minimum free space to maintain after write (GB)

    Returns:
        Tuple of (has_space, error_message)
        - has_space: True if sufficient space available
        - error_message: Empty string if space available, error details otherwise

    Example:
        >>> has_space, error = check_disk_space(1024**3, Path("/data"))
        >>> if not has_space:
        ...     print(error)

        >>> # With 20% buffer and 5GB minimum free
        >>> has_space, error = check_disk_space(
        ...     1024**3, Path("/data"), buffer_pct=0.2, min_free_gb=5.0
        ... )
    """
    try:
        available = get_available_disk_space(path)
    except Exception as e:
        return False, f"Failed to check disk space at {path}: {e}"

    # Calculate required space with buffer
    buffered_required = int(required_bytes * (1 + buffer_pct))

    # Apply minimum free space constraint if specified
    if min_free_gb is not None:
        min_free_bytes = int(min_free_gb * (1024**3))
        total_required = buffered_required + min_free_bytes
    else:
        total_required = buffered_required

    if available < total_required:
        required_gb = total_required / (1024**3)
        available_gb = available / (1024**3)
        buffer_info = f" (includes {buffer_pct*100:.0f}% safety buffer)"
        if min_free_gb:
            buffer_info += f" + {min_free_gb:.1f}GB minimum free"

        return (
            False,
            f"Insufficient disk space: need {required_gb:.2f}GB{buffer_info}, "
            f"have {available_gb:.2f}GB at {path}",
        )

    return True, ""


def estimate_required_space(
    source: str, item_count: Optional[int] = None, dump_size: Optional[int] = None
) -> int:
    """
    Estimate required disk space based on data source and parameters.

    Uses conservative multipliers based on empirical data:
    - Wikipedia: 3x dump size (compressed -> extracted -> silver)
    - BBC: 50MB per 100 articles
    - HuggingFace: ~500 bytes per record (text + metadata)
    - Språkbanken: ~2KB per document
    - TikTok: ~200 bytes per comment

    Args:
        source: Data source name (e.g., "wikipedia", "bbc", "huggingface")
        item_count: Number of items to process (articles, records, etc.)
        dump_size: Size of dump file in bytes (for Wikipedia, Språkbanken)

    Returns:
        Estimated required space in bytes

    Example:
        >>> # Wikipedia dump (300MB compressed)
        >>> required = estimate_required_space("wikipedia", dump_size=300*1024**2)
        >>> print(f"Need: {required / (1024**2):.0f}MB")
        Need: 900MB

        >>> # BBC scraping (500 articles)
        >>> required = estimate_required_space("bbc", item_count=500)
        >>> print(f"Need: {required / (1024**2):.0f}MB")
        Need: 250MB
    """
    source_lower = source.lower()

    # Wikipedia: 3x dump size (compressed -> extracted -> silver)
    if "wikipedia" in source_lower or "wiki" in source_lower:
        if dump_size:
            return dump_size * 3
        # Default: assume 300MB dump
        return 900 * (1024**2)  # 900MB

    # BBC: 50MB per 100 articles
    elif "bbc" in source_lower:
        if item_count:
            return int((item_count / 100) * 50 * (1024**2))
        # Default: 100 articles
        return 50 * (1024**2)  # 50MB

    # HuggingFace: 500 bytes per record (conservative)
    elif "huggingface" in source_lower or "hf" in source_lower or "mc4" in source_lower:
        if item_count:
            return item_count * 500
        # Default: 10k records
        return 10_000 * 500  # 5MB

    # Språkbanken: 2KB per document
    elif "sprakbanken" in source_lower or "språkbanken" in source_lower:
        if dump_size:
            return dump_size * 2  # 2x for extraction + processing
        if item_count:
            return item_count * 2048
        # Default: 5k documents
        return 5_000 * 2048  # 10MB

    # TikTok: 200 bytes per comment
    elif "tiktok" in source_lower:
        if item_count:
            return item_count * 200
        # Default: 1k comments
        return 1_000 * 200  # 200KB

    # Unknown source: conservative 100MB default
    else:
        return 100 * (1024**2)


def format_bytes(bytes_val: int) -> str:
    """
    Format bytes as human-readable string.

    Args:
        bytes_val: Number of bytes

    Returns:
        Formatted string (e.g., "1.5GB", "250MB", "10KB")

    Example:
        >>> format_bytes(1536 * 1024**2)
        '1.50GB'
        >>> format_bytes(256 * 1024**2)
        '256MB'
    """
    if bytes_val >= 1024**3:
        return f"{bytes_val / (1024**3):.2f}GB"
    elif bytes_val >= 1024**2:
        return f"{bytes_val / (1024**2):.0f}MB"
    elif bytes_val >= 1024:
        return f"{bytes_val / 1024:.0f}KB"
    else:
        return f"{bytes_val}B"
