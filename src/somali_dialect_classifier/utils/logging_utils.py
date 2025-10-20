"""
Structured logging utilities for production observability.

Provides:
- JSON structured logging for production
- Automatic context injection (run_id, source, phase)
- Thread-safe context variables
- Human-readable console output for development
- Log rotation and compression
"""

import json
import logging
import logging.handlers
import socket
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union
import traceback
from contextlib import contextmanager
import uuid


# Thread-local storage for context
_context = threading.local()


class StructuredFormatter(logging.Formatter):
    """
    JSON structured log formatter with automatic context injection.
    """

    def __init__(
        self,
        include_context: bool = True,
        include_hostname: bool = False,
        include_traceback: bool = True
    ):
        """
        Initialize structured formatter.

        Args:
            include_context: Include thread-local context variables
            include_hostname: Include machine hostname
            include_traceback: Include full traceback for errors
        """
        super().__init__()
        self.include_context = include_context
        self.include_hostname = include_hostname
        self.include_traceback = include_traceback
        self.hostname = socket.gethostname() if include_hostname else None

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base log entry
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add hostname if configured
        if self.hostname:
            log_entry["hostname"] = self.hostname

        # Add context variables
        if self.include_context:
            context = get_context()
            if context:
                log_entry.update(context)

        # Add extra fields from record
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)

        # Add exception info if present
        if record.exc_info and self.include_traceback:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }

        # Add source location for DEBUG level
        if record.levelno <= logging.DEBUG:
            log_entry["location"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName
            }

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class ColoredFormatter(logging.Formatter):
    """
    Colored console formatter for development.
    """

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }

    def __init__(self, format_str: Optional[str] = None, use_colors: bool = True):
        """
        Initialize colored formatter.

        Args:
            format_str: Log format string
            use_colors: Enable color output
        """
        if format_str is None:
            format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        super().__init__(format_str)
        self.use_colors = use_colors and sys.stderr.isatty()

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        if self.use_colors:
            levelname = record.levelname
            record.levelname = (
                f"{self.COLORS.get(levelname, '')}"
                f"{levelname}"
                f"{self.COLORS['RESET']}"
            )

        # Add context to message
        context = get_context()
        if context:
            context_str = " ".join(f"[{k}={v}]" for k, v in context.items())
            record.msg = f"{context_str} {record.msg}" if context_str else record.msg

        formatted = super().format(record)

        # Reset levelname for other handlers
        record.levelname = levelname if self.use_colors else record.levelname

        return formatted


class StructuredLogger:
    """
    High-level structured logger with context management.
    """

    def __init__(
        self,
        name: str,
        level: Union[str, int] = "INFO",
        log_file: Optional[Path] = None,
        console: bool = True,
        json_format: bool = True,
        rotation_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize structured logger.

        Args:
            name: Logger name
            level: Log level
            log_file: Path to log file (None = no file logging)
            console: Enable console output
            json_format: Use JSON format (False = human-readable)
            rotation_config: Log rotation settings
        """
        self.logger = logging.getLogger(name)

        # Set level
        if isinstance(level, str):
            level = getattr(logging, level.upper())
        self.logger.setLevel(level)

        # Clear existing handlers
        self.logger.handlers.clear()

        # Add file handler with rotation
        if log_file:
            self._add_file_handler(log_file, json_format, rotation_config)

        # Add console handler
        if console:
            self._add_console_handler(json_format)

    def _add_file_handler(
        self,
        log_file: Path,
        json_format: bool,
        rotation_config: Optional[Dict[str, Any]] = None
    ):
        """Add rotating file handler."""
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Default rotation config
        if rotation_config is None:
            rotation_config = {
                "max_bytes": 104857600,  # 100 MB
                "backup_count": 10,
                "encoding": "utf-8"
            }

        # Create rotating file handler
        handler = logging.handlers.RotatingFileHandler(
            filename=str(log_file),
            maxBytes=rotation_config.get("max_bytes", 104857600),
            backupCount=rotation_config.get("backup_count", 10),
            encoding=rotation_config.get("encoding", "utf-8")
        )

        # Set formatter
        if json_format:
            handler.setFormatter(StructuredFormatter(
                include_context=True,
                include_hostname=True
            ))
        else:
            handler.setFormatter(logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            ))

        self.logger.addHandler(handler)

    def _add_console_handler(self, json_format: bool):
        """Add console handler."""
        handler = logging.StreamHandler(sys.stderr)

        if json_format:
            handler.setFormatter(StructuredFormatter(
                include_context=True,
                include_hostname=False
            ))
        else:
            handler.setFormatter(ColoredFormatter())

        self.logger.addHandler(handler)

    def get_logger(self) -> logging.Logger:
        """Get underlying logger instance."""
        return self.logger


# Context management functions

def set_context(**kwargs):
    """
    Set thread-local context variables.

    Args:
        **kwargs: Context variables to set

    Example:
        set_context(run_id="20250119_103045", source="BBC-Somali", phase="fetch")
    """
    if not hasattr(_context, 'data'):
        _context.data = {}
    _context.data.update(kwargs)


def get_context() -> Dict[str, Any]:
    """Get current thread-local context."""
    return getattr(_context, 'data', {})


def clear_context():
    """Clear thread-local context."""
    if hasattr(_context, 'data'):
        _context.data.clear()


@contextmanager
def log_context(**kwargs):
    """
    Context manager for temporary context variables.

    Example:
        with log_context(phase="processing", batch_id=1):
            logger.info("Processing batch")  # Includes context
    """
    old_context = get_context().copy()
    set_context(**kwargs)
    try:
        yield
    finally:
        clear_context()
        if old_context:
            set_context(**old_context)


# Run ID generation

def generate_run_id(source: Optional[str] = None) -> str:
    """
    Generate unique run ID.

    Args:
        source: Optional source identifier

    Returns:
        Run ID in format: YYYYMMDD_HHMMSS_[source]_[uuid4]

    Example:
        20250119_103045_bbc_a1b2c3d4
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]

    if source:
        return f"{timestamp}_{source.lower()}_{unique_id}"
    return f"{timestamp}_{unique_id}"


# Logging helpers for specific events

class LogEvent:
    """Predefined log event types for consistency."""

    # Discovery events
    DISCOVERY_START = "discovery_start"
    DISCOVERY_COMPLETE = "discovery_complete"
    URL_DISCOVERED = "url_discovered"

    # Fetch events
    FETCH_START = "fetch_start"
    FETCH_SUCCESS = "fetch_success"
    FETCH_FAILED = "fetch_failed"
    FETCH_SKIPPED = "fetch_skipped"

    # Processing events
    PROCESS_START = "process_start"
    PROCESS_SUCCESS = "process_success"
    PROCESS_FAILED = "process_failed"

    # Deduplication events
    DUPLICATE_FOUND = "duplicate_found"
    NEAR_DUPLICATE_FOUND = "near_duplicate_found"

    # RSS events
    RSS_FETCH = "rss_fetch"
    RSS_THROTTLED = "rss_throttled"

    # Quality events
    FILTER_APPLIED = "filter_applied"
    QUALITY_CHECK_FAILED = "quality_check_failed"


def log_event(
    logger: logging.Logger,
    event: str,
    level: int = logging.INFO,
    **kwargs
):
    """
    Log structured event.

    Args:
        logger: Logger instance
        event: Event type (use LogEvent constants)
        level: Log level
        **kwargs: Event-specific data

    Example:
        log_event(
            logger,
            LogEvent.FETCH_SUCCESS,
            url="https://...",
            http_status=200,
            duration_ms=234,
            bytes=5432
        )
    """
    # Create extra fields
    extra_fields = {"event": event}
    extra_fields.update(kwargs)

    # Create log record with extra fields
    record = logger.makeRecord(
        logger.name,
        level,
        "",  # pathname
        0,   # lineno
        f"Event: {event}",  # msg
        (),  # args
        None  # exc_info
    )
    record.extra_fields = extra_fields

    logger.handle(record)


# Performance timing utilities

class Timer:
    """Simple timer for measuring durations."""

    def __init__(self):
        """Initialize timer."""
        self.start_time = None
        self.elapsed_ms = None

    def __enter__(self):
        """Start timer."""
        self.start_time = datetime.now(timezone.utc)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timer and calculate elapsed time."""
        if self.start_time:
            elapsed = datetime.now(timezone.utc) - self.start_time
            self.elapsed_ms = int(elapsed.total_seconds() * 1000)

    def get_elapsed_ms(self) -> int:
        """Get elapsed time in milliseconds."""
        return self.elapsed_ms or 0


# Configuration loader for logging

def setup_logging(config_path: Optional[Path] = None, environment: str = "development"):
    """
    Setup logging from configuration file.

    Args:
        config_path: Path to configuration YAML
        environment: Environment name (development, production)

    Returns:
        StructuredLogger instance
    """
    # Load configuration
    if config_path and config_path.exists():
        import yaml
        with open(config_path) as f:
            config = yaml.safe_load(f)
    else:
        # Default configuration
        config = {
            "logging": {
                "level": "INFO",
                "format": "json" if environment == "production" else "text",
                "file": {
                    "enabled": True,
                    "path": f"logs/{environment}.log"
                },
                "console": {
                    "enabled": True,
                    "colored": environment != "production"
                }
            }
        }

    log_config = config.get("logging", {})

    # Create logger
    logger = StructuredLogger(
        name="somali_dialect_classifier",
        level=log_config.get("level", "INFO"),
        log_file=Path(log_config["file"]["path"]) if log_config.get("file", {}).get("enabled") else None,
        console=log_config.get("console", {}).get("enabled", True),
        json_format=log_config.get("format") == "json"
    )

    return logger


# Example usage
if __name__ == "__main__":
    # Setup logger
    logger = StructuredLogger(
        name="test",
        level="DEBUG",
        log_file=Path("test.log"),
        json_format=True
    ).get_logger()

    # Set context
    run_id = generate_run_id("bbc")
    set_context(run_id=run_id, source="BBC-Somali")

    # Log with context
    logger.info("Starting data ingestion")

    # Log event with timing
    with Timer() as timer:
        # Simulate work
        import time
        time.sleep(0.1)

    log_event(
        logger,
        LogEvent.FETCH_SUCCESS,
        url="https://www.bbc.com/somali/article",
        http_status=200,
        duration_ms=timer.get_elapsed_ms(),
        bytes=5432
    )

    # Log with temporary context
    with log_context(phase="processing", batch_id=1):
        logger.info("Processing batch")

    # Log error with traceback
    try:
        raise ValueError("Test error")
    except Exception:
        logger.error("An error occurred", exc_info=True)