"""
Security utilities for input sanitization and secret masking.

Provides defense against:
- SQL injection
- Path traversal attacks
- Secret exposure in logs
"""

import re
from typing import Optional


# Allowed source names (whitelist for path traversal protection)
ALLOWED_SOURCES = {
    'wikipedia',
    'bbc',
    'bbc-somali',
    'sprakbanken',
    'tiktok',
    'huggingface',
    'wikipedia-somali'
}


def sanitize_source_name(source: str) -> str:
    """
    Sanitize source name to prevent path traversal attacks.

    Implements defense-in-depth:
    1. Remove path separators (/, \)
    2. Remove parent directory references (..)
    3. Whitelist validation against known sources

    Args:
        source: User-provided source name

    Returns:
        Sanitized source name

    Raises:
        ValueError: If source is invalid or not in whitelist

    Examples:
        >>> sanitize_source_name("wikipedia")
        'wikipedia'
        >>> sanitize_source_name("../etc/passwd")
        ValueError: Invalid source
        >>> sanitize_source_name("bbc/../../etc")
        ValueError: Invalid source
    """
    if not source:
        raise ValueError("Source name cannot be empty")

    # Remove path separators and parent directory references
    sanitized = re.sub(r'[/\\]', '', source)
    sanitized = sanitized.replace('..', '')

    # Normalize to lowercase for comparison
    sanitized_lower = sanitized.lower()

    # Whitelist validation - only allow known sources
    if sanitized_lower not in ALLOWED_SOURCES:
        raise ValueError(
            f"Invalid source: {source}. "
            f"Allowed sources: {', '.join(sorted(ALLOWED_SOURCES))}"
        )

    return sanitized_lower


def mask_secret(secret: Optional[str], visible_chars: int = 4, min_length: int = 8) -> str:
    """
    Mask secret showing only last N characters.

    Prevents secret exposure in logs, CLI output, and error messages.

    Args:
        secret: Secret string to mask (API key, token, password)
        visible_chars: Number of characters to show at end (default: 4)
        min_length: Minimum length before showing any characters (default: 8)

    Returns:
        Masked string in format "***XXXX"

    Examples:
        >>> mask_secret("sk_live_abc123def456")
        '***f456'
        >>> mask_secret("short")
        '***'
        >>> mask_secret(None)
        '***'
        >>> mask_secret("")
        '***'
    """
    if not secret:
        return "***"

    # For very short secrets, mask completely for security
    if len(secret) < min_length:
        return "***"

    # Show only last N characters
    return f"***{secret[-visible_chars:]}"


def validate_sql_parameter(param: str, param_name: str = "parameter") -> str:
    """
    Validate SQL parameter (defensive check).

    While parameterized queries prevent SQL injection, this provides
    an additional validation layer for defense-in-depth.

    Args:
        param: Parameter value
        param_name: Parameter name for error messages

    Returns:
        Validated parameter

    Raises:
        ValueError: If parameter contains SQL injection patterns

    Examples:
        >>> validate_sql_parameter("normal_value")
        'normal_value'
        >>> validate_sql_parameter("'; DROP TABLE--")
        ValueError: Invalid SQL parameter
    """
    if not param:
        return param

    # Check for common SQL injection patterns
    dangerous_patterns = [
        r"';",           # Statement terminator
        r"--",           # Comment marker
        r"/\*",          # Block comment start
        r"\*/",          # Block comment end
        r"xp_",          # Extended stored procedures
        r"sp_",          # System stored procedures
        r"EXEC\s",       # Execute command
        r"EXECUTE\s",    # Execute command
        r"DROP\s",       # Drop table/database
        r"DELETE\s",     # Delete without WHERE (dangerous)
        r"INSERT\s",     # Injection attempt
        r"UPDATE\s",     # Update without WHERE (dangerous)
        r"UNION\s",      # Union-based injection
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, param, re.IGNORECASE):
            raise ValueError(
                f"Invalid SQL parameter '{param_name}': "
                f"contains potentially dangerous pattern"
            )

    return param


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent directory traversal.

    Args:
        filename: User-provided filename

    Returns:
        Sanitized filename (basename only, no path components)

    Examples:
        >>> sanitize_filename("document.txt")
        'document.txt'
        >>> sanitize_filename("../../etc/passwd")
        'passwd'
        >>> sanitize_filename("../../../root/.ssh/id_rsa")
        'id_rsa'
    """
    import os

    # Extract basename to remove any path components
    basename = os.path.basename(filename)

    # Remove any remaining path separators
    sanitized = re.sub(r'[/\\]', '', basename)

    # Remove parent directory references
    sanitized = sanitized.replace('..', '')

    # Remove null bytes (path traversal in some systems)
    sanitized = sanitized.replace('\0', '')

    if not sanitized:
        raise ValueError("Invalid filename: results in empty string after sanitization")

    return sanitized


def is_safe_url(url: str) -> bool:
    """
    Validate URL is safe for use in system.

    Prevents SSRF attacks by blocking internal/private URLs.

    Args:
        url: URL to validate

    Returns:
        True if URL is safe, False otherwise

    Examples:
        >>> is_safe_url("https://example.com/page")
        True
        >>> is_safe_url("http://localhost:8080")
        False
        >>> is_safe_url("file:///etc/passwd")
        False
    """
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)

        # Only allow http/https schemes
        if parsed.scheme not in ('http', 'https'):
            return False

        # Block localhost/loopback
        hostname = parsed.hostname
        if not hostname:
            return False

        # Block localhost variations
        localhost_patterns = [
            'localhost',
            '127.0.0.1',
            '0.0.0.0',
            '::1',
        ]

        if hostname.lower() in localhost_patterns:
            return False

        # Block private IP ranges (basic check)
        if hostname.startswith('10.'):
            return False
        if hostname.startswith('192.168.'):
            return False
        if hostname.startswith('172.'):
            # Check if in 172.16.0.0 - 172.31.255.255 range
            parts = hostname.split('.')
            if len(parts) == 4:
                try:
                    second_octet = int(parts[1])
                    if 16 <= second_octet <= 31:
                        return False
                except ValueError:
                    pass

        return True

    except Exception:
        return False
