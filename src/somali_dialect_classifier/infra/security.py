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
    "wikipedia",
    "bbc",
    "bbc-somali",
    "sprakbanken",
    "sprakbanken-somali",  # Added to match actual processor source name
    "tiktok",
    "tiktok-somali",  # Added to match silver schema validation requirement
    "huggingface",
    "wikipedia-somali",
}


def sanitize_source_name(source: str) -> str:
    r"""
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
        >>> sanitize_source_name("HuggingFace-Somali_c4-so")
        'huggingface-somali_c4-so'
    """
    if not source:
        raise ValueError("Source name cannot be empty")

    # Remove path separators and parent directory references
    sanitized = re.sub(r"[/\\]", "", source)
    sanitized = sanitized.replace("..", "")

    # Normalize to lowercase for comparison
    sanitized_lower = sanitized.lower()

    # Check if exact match in whitelist
    if sanitized_lower in ALLOWED_SOURCES:
        return sanitized_lower

    # Special handling for HuggingFace sources with dataset suffixes
    # Format: huggingface-somali_<dataset>-<config> or huggingface_<dataset>
    if sanitized_lower.startswith("huggingface"):
        # Allow alphanumeric, hyphens, and underscores only
        if re.match(r"^huggingface[-_a-z0-9]+$", sanitized_lower):
            return sanitized_lower

    # If not in whitelist and not a valid HuggingFace source, reject
    raise ValueError(
        f"Invalid source: {source}. "
        f"Allowed sources: {', '.join(sorted(ALLOWED_SOURCES))} "
        f"(HuggingFace sources with dataset suffixes are also allowed)"
    )


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
        r"';",  # Statement terminator
        r"--",  # Comment marker
        r"/\*",  # Block comment start
        r"\*/",  # Block comment end
        r"xp_",  # Extended stored procedures
        r"sp_",  # System stored procedures
        r"EXEC\s",  # Execute command
        r"EXECUTE\s",  # Execute command
        r"DROP\s",  # Drop table/database
        r"DELETE\s",  # Delete without WHERE (dangerous)
        r"INSERT\s",  # Injection attempt
        r"UPDATE\s",  # Update without WHERE (dangerous)
        r"UNION\s",  # Union-based injection
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, param, re.IGNORECASE):
            raise ValueError(
                f"Invalid SQL parameter '{param_name}': contains potentially dangerous pattern"
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
    sanitized = re.sub(r"[/\\]", "", basename)

    # Remove parent directory references
    sanitized = sanitized.replace("..", "")

    # Remove null bytes (path traversal in some systems)
    sanitized = sanitized.replace("\0", "")

    if not sanitized:
        raise ValueError("Invalid filename: results in empty string after sanitization")

    return sanitized


def validate_file_path(file_path: str, base_dir: Optional[str] = None) -> bool:
    """
    Validate file path to prevent path traversal attacks.

    Prevents access to files outside base directory using:
    - Path normalization (resolve .., ., symlinks)
    - Base directory containment check
    - Null byte detection

    Args:
        file_path: User-provided file path
        base_dir: Base directory to restrict access to (optional)

    Returns:
        True if path is safe, False otherwise

    Examples:
        >>> validate_file_path("data/raw/file.txt", base_dir="data")
        True
        >>> validate_file_path("../../../etc/passwd", base_dir="data")
        False
        >>> validate_file_path("data/raw/../../etc/passwd", base_dir="data")
        False
    """
    from pathlib import Path

    try:
        # Remove null bytes (path traversal in some systems)
        if "\0" in file_path:
            return False

        # Resolve to absolute path (resolves .., ., symlinks)
        resolved_path = Path(file_path).resolve()

        # If base_dir provided, ensure path is within base_dir
        if base_dir:
            base_path = Path(base_dir).resolve()
            try:
                # relative_to() raises ValueError if path is not relative to base
                resolved_path.relative_to(base_path)
            except ValueError:
                # Path is outside base directory
                return False

        return True

    except Exception:
        return False


def is_safe_url(
    url: str, allowed_schemes: set[str] | None = None, allowed_domains: set[str] | None = None
) -> bool:
    """
    Validate URL is safe for use in system (SSRF protection).

    Prevents SSRF attacks by blocking:
    - Unsafe schemes (file://, ftp://, javascript:, data:)
    - Private IP ranges (RFC 1918)
    - Loopback addresses (127.0.0.0/8, ::1)
    - Link-local addresses (169.254.0.0/16)
    - Multicast addresses
    - Metadata endpoints (AWS, GCP, Azure)

    Args:
        url: URL to validate
        allowed_schemes: Set of allowed schemes (default: {"http", "https"})
        allowed_domains: Optional set of allowed domains (e.g., {"bbc.com", "bbc.co.uk"})

    Returns:
        True if URL is safe, False otherwise

    Examples:
        >>> is_safe_url("https://example.com/page")
        True
        >>> is_safe_url("http://localhost:8080")
        False
        >>> is_safe_url("file:///etc/passwd")
        False
        >>> is_safe_url("http://169.254.169.254/latest/meta-data/")
        False
        >>> is_safe_url("https://bbc.com/article", allowed_domains={"bbc.com"})
        True
        >>> is_safe_url("https://evil.com/article", allowed_domains={"bbc.com"})
        False
    """
    import ipaddress
    from urllib.parse import urlparse

    if allowed_schemes is None:
        allowed_schemes = {"http", "https"}

    try:
        parsed = urlparse(url)

        # Only allow http/https schemes (or custom whitelist)
        if parsed.scheme not in allowed_schemes:
            return False

        # Block data: URLs (common in XSS/SSRF)
        if parsed.scheme == "data":
            return False

        # Require hostname
        hostname = parsed.hostname
        if not hostname:
            return False

        # Domain whitelist check (if provided)
        if allowed_domains is not None:
            domain_match = False
            for allowed_domain in allowed_domains:
                # Support both exact match and subdomain match
                if hostname == allowed_domain or hostname.endswith(f".{allowed_domain}"):
                    domain_match = True
                    break

            if not domain_match:
                return False

        # Block localhost variations
        localhost_patterns = [
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "::1",
            "[::]",
            "[::1]",
        ]

        if hostname.lower() in localhost_patterns:
            return False

        # Try to parse as IP address for comprehensive checks
        try:
            ip = ipaddress.ip_address(hostname)

            # Block loopback addresses (127.0.0.0/8, ::1)
            if ip.is_loopback:
                return False

            # Block private IP ranges (RFC 1918)
            if ip.is_private:
                return False

            # Block link-local addresses (169.254.0.0/16, fe80::/10)
            if ip.is_link_local:
                return False

            # Block multicast addresses
            if ip.is_multicast:
                return False

            # Block reserved addresses
            if ip.is_reserved:
                return False

            # Block unspecified addresses (0.0.0.0, ::)
            if ip.is_unspecified:
                return False

        except ValueError:
            # Not a direct IP address, continue with domain checks
            pass

        # Block cloud metadata endpoints (DNS-based)
        metadata_endpoints = [
            "metadata.google.internal",  # GCP
            "169.254.169.254",  # AWS/Azure
            "metadata.azure.com",  # Azure
            "consul",  # Consul
            "kubernetes.default",  # Kubernetes
        ]

        if hostname.lower() in metadata_endpoints:
            return False

        return True

    except Exception:
        # Any parsing error = reject URL
        return False


def validate_url_for_source(url: str, source: str, allowed_domains: set[str]) -> tuple[bool, str]:
    """
    Validate URL for a specific data source with SSRF protection.

    Combines general SSRF protection with source-specific domain validation.

    Args:
        url: URL to validate
        source: Source name (for logging)
        allowed_domains: Set of allowed domains for this source

    Returns:
        Tuple of (is_valid, error_message)
        - (True, "") if valid
        - (False, error_msg) if invalid

    Examples:
        >>> validate_url_for_source("https://bbc.com/somali/article", "bbc", {"bbc.com", "bbc.co.uk"})
        (True, "")
        >>> validate_url_for_source("http://127.0.0.1/pwned", "bbc", {"bbc.com"})
        (False, "SSRF attempt detected: loopback address blocked")
        >>> validate_url_for_source("https://evil.com/article", "bbc", {"bbc.com"})
        (False, "Domain not allowed for source 'bbc': evil.com")
    """
    from urllib.parse import urlparse

    try:
        # Basic URL validation
        if not url or not isinstance(url, str):
            return False, "URL is empty or invalid type"

        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception as e:
            return False, f"Failed to parse URL: {e}"

        hostname = parsed.hostname
        if not hostname:
            return False, "URL missing hostname"

        # General SSRF protection
        if not is_safe_url(url, allowed_schemes={"http", "https"}):
            # Determine specific reason for rejection
            if parsed.scheme not in {"http", "https"}:
                return False, f"SSRF attempt detected: unsafe scheme '{parsed.scheme}'"

            import ipaddress

            try:
                ip = ipaddress.ip_address(hostname)
                if ip.is_loopback:
                    return False, "SSRF attempt detected: loopback address blocked"
                if ip.is_private:
                    return False, "SSRF attempt detected: private IP range blocked"
                if ip.is_link_local:
                    return False, "SSRF attempt detected: link-local address blocked"
            except ValueError:
                pass

            return False, "SSRF attempt detected: URL blocked by security policy"

        # Domain whitelist validation
        domain_match = False
        for allowed_domain in allowed_domains:
            if hostname == allowed_domain or hostname.endswith(f".{allowed_domain}"):
                domain_match = True
                break

        if not domain_match:
            return (
                False,
                f"Domain not allowed for source '{source}': {hostname} "
                f"(allowed: {', '.join(sorted(allowed_domains))})",
            )

        return True, ""

    except Exception as e:
        return False, f"URL validation error: {e}"


# Sensitive key patterns for log redaction
SENSITIVE_KEYS = {
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "api-key",
    "access_token",
    "refresh_token",
    "auth",
    "authorization",
    "apify_api_token",
    "apify_token",
    "huggingface_token",
    "hf_token",
    "private_key",
    "client_secret",
    "bearer",
    "credential",
    "credentials",
}


def redact_secrets(data: dict | list | tuple | str | int | float | bool | None) -> dict | list | tuple | str | int | float | bool | None:
    """
    Recursively redact sensitive values from data structures.

    Designed for use in logging systems to prevent secret exposure.
    Handles nested dictionaries, lists, tuples, and primitive types.

    Args:
        data: Data structure potentially containing secrets
              (dict, list, tuple, or primitive types)

    Returns:
        Data structure with secrets masked using mask_secret()
        Original structure and types preserved

    Examples:
        >>> redact_secrets({"username": "admin", "password": "secret123"})
        {'username': 'admin', 'password': '***t123'}

        >>> redact_secrets({"config": {"api_key": "sk_live_abc123"}})
        {'config': {'api_key': '***c123'}}

        >>> redact_secrets([{"token": "abc"}, {"data": "safe"}])
        [{'token': '***'}, {'data': 'safe'}]

        >>> redact_secrets("plain string")
        'plain string'
    """
    # Handle None
    if data is None:
        return None

    # Handle dictionaries
    if isinstance(data, dict):
        redacted = {}
        for key, value in data.items():
            # Check if key name indicates sensitive data (case-insensitive)
            key_lower = key.lower() if isinstance(key, str) else str(key).lower()

            # Check for exact match or partial match in key name
            is_sensitive = False
            for sensitive_key in SENSITIVE_KEYS:
                if sensitive_key in key_lower:
                    is_sensitive = True
                    break

            if is_sensitive and isinstance(value, str):
                # Redact the value using mask_secret
                redacted[key] = mask_secret(value)
            else:
                # Recursively process the value
                redacted[key] = redact_secrets(value)

        return redacted

    # Handle lists
    if isinstance(data, list):
        return [redact_secrets(item) for item in data]

    # Handle tuples (preserve tuple type)
    if isinstance(data, tuple):
        return tuple(redact_secrets(item) for item in data)

    # Handle primitive types (str, int, float, bool)
    # These are returned as-is unless they're dict values (handled above)
    return data
