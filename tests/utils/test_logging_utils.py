"""Tests for logging utilities."""

import json
import logging
import sys
import time

import pytest

from somali_dialect_classifier.utils.logging_utils import (
    ColoredFormatter,
    LogEvent,
    StructuredFormatter,
    StructuredLogger,
    Timer,
    clear_context,
    generate_run_id,
    get_context,
    log_context,
    log_event,
    set_context,
    setup_logging,
)


class TestStructuredFormatter:
    """Test cases for StructuredFormatter."""

    def test_formatter_creates_json_output(self):
        """Test that structured formatter creates valid JSON."""
        formatter = StructuredFormatter()
        logger = logging.getLogger("test_json")
        logger.setLevel(logging.INFO)

        # Create a log record
        record = logger.makeRecord(
            logger.name,
            logging.INFO,
            __file__,
            42,
            "Test message",
            (),
            None,
        )

        output = formatter.format(record)

        # Should be valid JSON
        parsed = json.loads(output)
        assert parsed["message"] == "Test message"
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test_json"
        assert "timestamp" in parsed

    def test_formatter_includes_context(self):
        """Test that formatter includes context variables."""
        formatter = StructuredFormatter(include_context=True)
        logger = logging.getLogger("test_context")

        # Set context
        set_context(run_id="test_run_123", source="test_source")

        record = logger.makeRecord(
            logger.name,
            logging.INFO,
            __file__,
            42,
            "Test with context",
            (),
            None,
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["run_id"] == "test_run_123"
        assert parsed["source"] == "test_source"

        # Clean up context
        clear_context()

    def test_formatter_includes_exception_info(self):
        """Test that formatter includes exception information."""
        formatter = StructuredFormatter(include_traceback=True)
        logger = logging.getLogger("test_exception")

        try:
            raise ValueError("Test error")
        except ValueError:
            record = logger.makeRecord(
                logger.name,
                logging.ERROR,
                __file__,
                42,
                "Error occurred",
                (),
                sys.exc_info(),
            )

            output = formatter.format(record)
            parsed = json.loads(output)

            assert "exception" in parsed
            assert parsed["exception"]["type"] == "ValueError"
            assert "Test error" in parsed["exception"]["message"]
            assert "traceback" in parsed["exception"]

    def test_formatter_includes_hostname(self):
        """Test that formatter can include hostname."""
        formatter = StructuredFormatter(include_hostname=True)
        logger = logging.getLogger("test_hostname")

        record = logger.makeRecord(
            logger.name,
            logging.INFO,
            __file__,
            42,
            "Test",
            (),
            None,
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        assert "hostname" in parsed
        assert isinstance(parsed["hostname"], str)
        assert len(parsed["hostname"]) > 0

    def test_formatter_includes_source_location_for_debug(self):
        """Test that DEBUG level includes source location."""
        formatter = StructuredFormatter()
        logger = logging.getLogger("test_location")

        record = logger.makeRecord(
            logger.name,
            logging.DEBUG,
            __file__,
            42,
            "Debug message",
            (),
            None,
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        assert "location" in parsed
        assert "file" in parsed["location"]
        assert "line" in parsed["location"]
        assert "function" in parsed["location"]

    def test_formatter_no_location_for_info(self):
        """Test that INFO level doesn't include source location."""
        formatter = StructuredFormatter()
        logger = logging.getLogger("test_no_location")

        record = logger.makeRecord(
            logger.name,
            logging.INFO,
            __file__,
            42,
            "Info message",
            (),
            None,
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        assert "location" not in parsed


class TestColoredFormatter:
    """Test cases for ColoredFormatter."""

    def test_formatter_creates_output(self):
        """Test that colored formatter creates output."""
        formatter = ColoredFormatter(use_colors=False)
        logger = logging.getLogger("test_colored")

        record = logger.makeRecord(
            logger.name,
            logging.INFO,
            __file__,
            42,
            "Test message",
            (),
            None,
        )

        output = formatter.format(record)
        assert "Test message" in output
        assert "INFO" in output

    def test_formatter_includes_context_in_message(self):
        """Test that colored formatter includes context in message."""
        formatter = ColoredFormatter(use_colors=False)
        logger = logging.getLogger("test_context_colored")

        set_context(run_id="test_123")

        record = logger.makeRecord(
            logger.name,
            logging.INFO,
            __file__,
            42,
            "Test",
            (),
            None,
        )

        output = formatter.format(record)
        assert "[run_id=test_123]" in output

        clear_context()


class TestStructuredLogger:
    """Test cases for StructuredLogger."""

    def test_logger_initialization(self, tmp_path):
        """Test structured logger initialization."""
        log_file = tmp_path / "test.log"
        logger = StructuredLogger(
            name="test_init",
            level="INFO",
            log_file=log_file,
            console=False,
            json_format=True,
        )

        assert logger.logger.name == "test_init"
        assert logger.logger.level == logging.INFO
        assert len(logger.logger.handlers) == 1

    def test_logger_creates_log_file(self, tmp_path):
        """Test that logger creates log file."""
        log_file = tmp_path / "test.log"
        logger = StructuredLogger(
            name="test_file",
            level="INFO",
            log_file=log_file,
            console=False,
        )

        logger.get_logger().info("Test message")

        # Force flush
        for handler in logger.logger.handlers:
            handler.flush()

        assert log_file.exists()

    def test_logger_respects_level(self, tmp_path):
        """Test that logger respects log level."""
        log_file = tmp_path / "test.log"
        logger = StructuredLogger(
            name="test_level",
            level="WARNING",
            log_file=log_file,
            console=False,
        )

        logger.get_logger().debug("Debug message")
        logger.get_logger().warning("Warning message")

        for handler in logger.logger.handlers:
            handler.flush()

        # Only warning should be logged
        if log_file.exists():
            content = log_file.read_text()
            assert "Warning message" in content
            assert "Debug message" not in content

    def test_logger_rotation_config(self, tmp_path):
        """Test log rotation configuration."""
        log_file = tmp_path / "test.log"
        rotation_config = {
            "max_bytes": 1024,
            "backup_count": 5,
            "encoding": "utf-8",
        }

        logger = StructuredLogger(
            name="test_rotation",
            level="INFO",
            log_file=log_file,
            console=False,
            rotation_config=rotation_config,
        )

        # Check that handler is RotatingFileHandler
        file_handlers = [h for h in logger.logger.handlers if hasattr(h, "maxBytes")]
        assert len(file_handlers) == 1
        assert file_handlers[0].maxBytes == 1024
        assert file_handlers[0].backupCount == 5


class TestContextManagement:
    """Test context management functions."""

    def test_set_and_get_context(self):
        """Test setting and getting context."""
        clear_context()
        set_context(run_id="test_123", source="test_source")

        context = get_context()
        assert context["run_id"] == "test_123"
        assert context["source"] == "test_source"

        clear_context()

    def test_clear_context(self):
        """Test clearing context."""
        set_context(run_id="test_123")
        assert len(get_context()) > 0

        clear_context()
        assert len(get_context()) == 0

    def test_log_context_manager(self):
        """Test log context manager."""
        clear_context()
        set_context(run_id="outer")

        with log_context(phase="processing", batch_id=1):
            context = get_context()
            assert context["run_id"] == "outer"
            assert context["phase"] == "processing"
            assert context["batch_id"] == 1

        # Context should be restored
        context = get_context()
        assert context["run_id"] == "outer"
        assert "phase" not in context
        assert "batch_id" not in context

        clear_context()

    def test_nested_log_context(self):
        """Test nested log context managers."""
        clear_context()

        with log_context(level=1):
            assert get_context()["level"] == 1

            with log_context(level=2, sub="a"):
                context = get_context()
                assert context["level"] == 2
                assert context["sub"] == "a"

            # Should restore to level 1
            assert get_context()["level"] == 1
            assert "sub" not in get_context()

        # Should be empty
        assert len(get_context()) == 0


class TestRunIDGeneration:
    """Test run ID generation."""

    def test_generate_run_id_without_source(self):
        """Test generating run ID without source."""
        run_id = generate_run_id()

        assert len(run_id) > 0
        assert "_" in run_id
        # Format: YYYYMMDD_HHMMSS_uuid
        parts = run_id.split("_")
        assert len(parts) == 3

    def test_generate_run_id_with_source(self):
        """Test generating run ID with source."""
        run_id = generate_run_id(source="BBC")

        assert "bbc" in run_id.lower()
        parts = run_id.split("_")
        assert len(parts) == 4
        assert parts[2] == "bbc"

    def test_generate_run_id_is_unique(self):
        """Test that generated run IDs are unique."""
        run_id1 = generate_run_id()
        time.sleep(0.01)  # Small delay
        run_id2 = generate_run_id()

        assert run_id1 != run_id2


class TestLogEvent:
    """Test log event functionality."""

    def test_log_event_creates_record(self):
        """Test that log_event creates a log record."""
        logger = logging.getLogger("test_event")
        logger.handlers.clear()

        # Add handler to capture output
        handler = logging.StreamHandler()
        formatter = StructuredFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Log an event
        log_event(
            logger,
            LogEvent.FETCH_SUCCESS,
            url="https://example.com",
            http_status=200,
            duration_ms=100,
        )

        # Should not raise an error
        assert True

    def test_log_event_constants_exist(self):
        """Test that log event constants are defined."""
        assert hasattr(LogEvent, "DISCOVERY_START")
        assert hasattr(LogEvent, "FETCH_SUCCESS")
        assert hasattr(LogEvent, "FETCH_FAILED")
        assert hasattr(LogEvent, "PROCESS_START")
        assert hasattr(LogEvent, "DUPLICATE_FOUND")
        assert hasattr(LogEvent, "RSS_FETCH")
        assert hasattr(LogEvent, "FILTER_APPLIED")


class TestTimer:
    """Test Timer class."""

    def test_timer_measures_elapsed_time(self):
        """Test that timer measures elapsed time."""
        with Timer() as timer:
            time.sleep(0.1)

        elapsed = timer.get_elapsed_ms()
        # Should be at least 100ms
        assert elapsed >= 90
        # Should be less than 200ms (with tolerance)
        assert elapsed < 200

    def test_timer_returns_zero_if_not_started(self):
        """Test that timer returns zero if not used."""
        timer = Timer()
        assert timer.get_elapsed_ms() == 0

    def test_timer_context_manager(self):
        """Test timer as context manager."""
        timer = Timer()
        with timer:
            time.sleep(0.05)

        assert timer.elapsed_ms > 0
        assert timer.elapsed_ms >= 45


class TestSetupLogging:
    """Test setup_logging function."""

    def test_setup_logging_default_config(self):
        """Test setup logging with default configuration."""
        logger = setup_logging(environment="development")

        assert logger is not None
        assert logger.logger.name == "somali_dialect_classifier"

    def test_setup_logging_production_environment(self):
        """Test setup logging in production environment."""
        logger = setup_logging(environment="production")

        assert logger is not None
        # Should use JSON format in production
        json_handlers = [
            h for h in logger.logger.handlers if isinstance(h.formatter, StructuredFormatter)
        ]
        assert len(json_handlers) > 0

    def test_setup_logging_with_config_file(self, tmp_path):
        """Test setup logging with configuration file."""
        config_file = tmp_path / "logging_config.yaml"
        config_file.write_text("""
logging:
  level: DEBUG
  format: json
  file:
    enabled: true
    path: logs/test.log
  console:
    enabled: true
    colored: false
""")

        logger = setup_logging(config_path=config_file)

        assert logger is not None
        assert logger.logger.level == logging.DEBUG


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
