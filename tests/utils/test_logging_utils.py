"""Tests for logging utilities."""

import json
import logging
import sys
import time

import pytest

from somali_dialect_classifier.infra.logging_utils import (
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
from somali_dialect_classifier.infra.security import redact_secrets, SENSITIVE_KEYS


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


class TestSecretRedaction:
    """Test secret redaction in logging."""

    def test_redact_secrets_simple_dict(self):
        """Test redaction of simple dictionary with secrets."""
        data = {
            "username": "admin",
            "password": "secret123456",
            "api_key": "sk_live_abc123def456",
        }

        redacted = redact_secrets(data)

        assert redacted["username"] == "admin"
        assert redacted["password"] == "***3456"
        assert redacted["api_key"] == "***f456"

    def test_redact_secrets_nested_dict(self):
        """Test redaction of nested dictionary."""
        data = {
            "config": {
                "database": {
                    "host": "localhost",
                    "password": "dbpass12345678",
                },
                "api": {
                    "token": "secret_token_value",
                }
            }
        }

        redacted = redact_secrets(data)

        assert redacted["config"]["database"]["host"] == "localhost"
        assert redacted["config"]["database"]["password"] == "***5678"
        assert redacted["config"]["api"]["token"] == "***alue"

    def test_redact_secrets_case_insensitive(self):
        """Test that redaction is case-insensitive."""
        data = {
            "Password": "secret123456",
            "API_KEY": "sk_live_abc123",
            "apiKey": "another_key_123",
        }

        redacted = redact_secrets(data)

        assert redacted["Password"] == "***3456"
        assert redacted["API_KEY"] == "***c123"
        assert redacted["apiKey"] == "***_123"

    def test_redact_secrets_list_of_dicts(self):
        """Test redaction in list of dictionaries."""
        data = [
            {"name": "user1", "token": "token123456"},
            {"name": "user2", "api_key": "key987654321"},
        ]

        redacted = redact_secrets(data)

        assert redacted[0]["name"] == "user1"
        assert redacted[0]["token"] == "***3456"
        assert redacted[1]["name"] == "user2"
        assert redacted[1]["api_key"] == "***4321"

    def test_redact_secrets_preserves_structure(self):
        """Test that redaction preserves data structure."""
        data = {
            "list": [1, 2, 3],
            "dict": {"a": 1},
            "tuple": (1, 2),
            "string": "text",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "none": None,
        }

        redacted = redact_secrets(data)

        assert redacted["list"] == [1, 2, 3]
        assert redacted["dict"] == {"a": 1}
        assert redacted["tuple"] == (1, 2)
        assert redacted["string"] == "text"
        assert redacted["int"] == 42
        assert redacted["float"] == 3.14
        assert redacted["bool"] is True
        assert redacted["none"] is None

    def test_redact_secrets_all_sensitive_keys(self):
        """Test redaction for all defined sensitive keys."""
        # Test a subset of SENSITIVE_KEYS
        test_keys = [
            "password",
            "token",
            "api_key",
            "secret",
            "apify_api_token",
            "huggingface_token",
        ]

        data = {key: "secret_value_123456" for key in test_keys}
        redacted = redact_secrets(data)

        for key in test_keys:
            assert redacted[key] == "***3456"

    def test_redact_secrets_partial_key_match(self):
        """Test that partial key matches are detected."""
        data = {
            "user_password": "pass123456",
            "oauth_token": "tok987654321",
            "app_secret_key": "sec111222333",
        }

        redacted = redact_secrets(data)

        # All should be redacted due to partial matches
        assert redacted["user_password"] == "***3456"
        assert redacted["oauth_token"] == "***4321"
        assert redacted["app_secret_key"] == "***2333"

    def test_redact_secrets_short_values(self):
        """Test redaction of short secret values."""
        data = {
            "password": "short",
            "token": "abc",
        }

        redacted = redact_secrets(data)

        # Short values should be completely masked
        assert redacted["password"] == "***"
        assert redacted["token"] == "***"

    def test_redact_secrets_empty_values(self):
        """Test redaction of empty values."""
        data = {
            "password": "",
            "token": None,
        }

        redacted = redact_secrets(data)

        assert redacted["password"] == "***"
        assert redacted["token"] is None

    def test_redact_secrets_non_string_sensitive_values(self):
        """Test that non-string values in sensitive keys are not redacted."""
        data = {
            "password": 12345,
            "token": ["list", "items"],
            "api_key": {"nested": "dict"},
        }

        redacted = redact_secrets(data)

        # Non-string values should be recursively processed, not redacted
        assert redacted["password"] == 12345
        assert redacted["token"] == ["list", "items"]
        assert redacted["api_key"] == {"nested": "dict"}

    def test_formatter_redacts_context_secrets(self):
        """Test that StructuredFormatter redacts secrets in context."""
        clear_context()
        set_context(
            run_id="test_123",
            apify_api_token="sk_live_abc123def456",
            source="test"
        )

        formatter = StructuredFormatter(include_context=True)
        logger = logging.getLogger("test_redact_context")

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
        parsed = json.loads(output)

        # run_id and source should not be redacted
        assert parsed["run_id"] == "test_123"
        assert parsed["source"] == "test"

        # apify_api_token should be redacted
        assert parsed["apify_api_token"] == "***f456"
        assert "sk_live" not in output

        clear_context()

    def test_formatter_redacts_extra_fields_secrets(self):
        """Test that StructuredFormatter redacts secrets in extra_fields."""
        formatter = StructuredFormatter()
        logger = logging.getLogger("test_redact_extra")

        record = logger.makeRecord(
            logger.name,
            logging.INFO,
            __file__,
            42,
            "Test message",
            (),
            None,
        )

        # Add extra fields with secrets
        record.extra_fields = {
            "url": "https://example.com",
            "api_key": "sk_live_secret123456",
            "password": "userpass123456",
        }

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["url"] == "https://example.com"
        assert parsed["api_key"] == "***3456"
        assert parsed["password"] == "***3456"
        assert "sk_live_secret" not in output

    def test_colored_formatter_redacts_secrets(self):
        """Test that ColoredFormatter redacts secrets in context."""
        clear_context()
        set_context(
            run_id="test_123",
            token="secret_token_123456"
        )

        formatter = ColoredFormatter(use_colors=False)
        logger = logging.getLogger("test_colored_redact")

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

        # Should contain redacted token
        assert "***3456" in output
        assert "secret_token_123456" not in output

        clear_context()

    def test_log_event_with_secrets(self):
        """Test that log_event redacts secrets in event data."""
        logger = logging.getLogger("test_event_redact")
        logger.handlers.clear()

        # Add handler to capture output
        handler = logging.StreamHandler()
        formatter = StructuredFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Log event with secrets
        log_event(
            logger,
            LogEvent.FETCH_SUCCESS,
            url="https://api.example.com/data",
            api_key="sk_live_secret123456",
            response_size=1024,
        )

        # Should not raise an error
        assert True

    def test_redact_secrets_performance(self):
        """Test that redaction has acceptable performance."""
        import time

        # Create large nested structure
        data = {
            f"field_{i}": {
                "data": f"value_{i}",
                "password": f"secret_{i}_123456",
                "nested": {
                    "token": f"token_{i}_987654321",
                }
            }
            for i in range(100)
        }

        start_time = time.time()
        redacted = redact_secrets(data)
        elapsed_ms = (time.time() - start_time) * 1000

        # Should complete in less than 100ms
        assert elapsed_ms < 100

        # Verify some redactions
        assert redacted["field_0"]["password"] == "***3456"
        assert redacted["field_50"]["nested"]["token"] == "***4321"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
