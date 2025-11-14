"""
Comprehensive security tests for P0 vulnerability fixes.

Tests for:
1. SQL injection prevention
2. XSS prevention
3. Path traversal prevention
4. Secrets masking
"""

import sqlite3
from pathlib import Path

import pytest


class TestSQLInjectionPrevention:
    """Test SQL injection vulnerabilities are fixed."""

    def test_get_statistics_sql_injection(self, tmp_path):
        """Test that get_statistics uses parameterized queries."""
        from somali_dialect_classifier.preprocessing.crawl_ledger import (
            CrawlState,
            SQLiteLedger,
        )

        # Create test database
        db_path = tmp_path / "test.db"
        ledger = SQLiteLedger(db_path)

        # Insert test data
        ledger.upsert_url(
            url="https://example.com/article1",
            source="test-source",
            state=CrawlState.PROCESSED,
            text_hash="hash123",
        )

        # Test malicious input (SQL injection attempt)
        malicious_source = "test' OR '1'='1"

        # This should NOT return data due to parameterized queries
        stats = ledger.get_statistics(source=malicious_source)

        # Should return 0 results (no source matches malicious string)
        assert stats["total_urls"] == 0, "SQL injection prevention failed: malicious query returned data"

        # Valid source should work
        valid_stats = ledger.get_statistics(source="test-source")
        assert valid_stats["total_urls"] == 1

        ledger.close()

    def test_get_statistics_drop_table_injection(self, tmp_path):
        """Test that DROP TABLE injection is prevented."""
        from somali_dialect_classifier.preprocessing.crawl_ledger import (
            CrawlState,
            SQLiteLedger,
        )

        db_path = tmp_path / "test.db"
        ledger = SQLiteLedger(db_path)

        # Insert test data
        ledger.upsert_url(
            url="https://example.com/article1",
            source="test-source",
            state=CrawlState.PROCESSED,
        )

        # Attempt DROP TABLE injection
        malicious_source = "'; DROP TABLE crawl_ledger; --"

        # This should not drop the table
        ledger.get_statistics(source=malicious_source)

        # Table should still exist
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM crawl_ledger")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 1, "DROP TABLE injection prevention failed: table was dropped"

        ledger.close()

    def test_get_statistics_union_injection(self, tmp_path):
        """Test that UNION-based injection is prevented."""
        from somali_dialect_classifier.preprocessing.crawl_ledger import SQLiteLedger

        db_path = tmp_path / "test.db"
        ledger = SQLiteLedger(db_path)

        # Attempt UNION injection to extract data
        malicious_source = "' UNION SELECT * FROM crawl_ledger WHERE '1'='1"

        # This should return 0 results
        stats = ledger.get_statistics(source=malicious_source)
        assert stats["total_urls"] == 0

        ledger.close()


class TestPathTraversalPrevention:
    """Test path traversal vulnerabilities are fixed."""

    def test_sanitize_source_name_basic(self):
        """Test basic path traversal prevention."""
        from somali_dialect_classifier.utils.security import sanitize_source_name

        # Valid sources should work
        assert sanitize_source_name("wikipedia") == "wikipedia"
        assert sanitize_source_name("bbc") == "bbc"
        assert sanitize_source_name("BBC-Somali") == "bbc-somali"

        # Invalid sources should raise ValueError
        with pytest.raises(ValueError, match="Invalid source"):
            sanitize_source_name("../etc/passwd")

        with pytest.raises(ValueError, match="Invalid source"):
            sanitize_source_name("../../root/.ssh/id_rsa")

        with pytest.raises(ValueError, match="Invalid source"):
            sanitize_source_name("..\\..\\windows\\system32")

    def test_sanitize_source_name_null_bytes(self):
        """Test null byte injection is prevented."""
        from somali_dialect_classifier.utils.security import sanitize_source_name

        with pytest.raises(ValueError, match="Invalid source"):
            sanitize_source_name("wikipedia\x00/etc/passwd")

    def test_sanitize_source_name_mixed_case(self):
        """Test case-insensitive validation."""
        from somali_dialect_classifier.utils.security import sanitize_source_name

        # Should normalize to lowercase
        assert sanitize_source_name("WIKIPEDIA") == "wikipedia"
        assert sanitize_source_name("Wikipedia") == "wikipedia"
        assert sanitize_source_name("BBC") == "bbc"

    def test_sanitize_source_name_unknown_source(self):
        """Test unknown sources are rejected."""
        from somali_dialect_classifier.utils.security import sanitize_source_name

        with pytest.raises(ValueError, match="Invalid source"):
            sanitize_source_name("unknown-source")

        with pytest.raises(ValueError, match="Invalid source"):
            sanitize_source_name("malicious")

    def test_base_pipeline_sanitizes_source(self):
        """Test that BasePipeline sanitizes source names."""
        from somali_dialect_classifier.preprocessing.base_pipeline import BasePipeline
        from somali_dialect_classifier.preprocessing.text_cleaners import (
            create_html_cleaner,
        )

        # Create a minimal concrete implementation for testing
        class TestPipeline(BasePipeline):
            def download(self):
                pass

            def extract(self):
                pass

            def _extract_records(self):
                return iter([])

            def _create_cleaner(self):
                return create_html_cleaner()

            def _get_source_type(self):
                return "test"

            def _get_license(self):
                return "MIT"

            def _get_language(self):
                return "so"

            def _get_source_metadata(self):
                return {}

            def _get_domain(self):
                return "test"

            def _get_register(self):
                return "formal"

        # Valid source should work
        pipeline = TestPipeline(source="wikipedia")
        assert pipeline.source == "wikipedia"

        # Path traversal attempt should raise ValueError
        with pytest.raises(ValueError, match="Invalid source name"):
            TestPipeline(source="../etc/passwd")

        with pytest.raises(ValueError, match="Invalid source name"):
            TestPipeline(source="../../sensitive")


class TestSecretsMasking:
    """Test secrets masking functionality."""

    def test_mask_secret_basic(self):
        """Test basic secret masking."""
        from somali_dialect_classifier.utils.security import mask_secret

        # Normal secret
        assert mask_secret("sk_live_abc123def456") == "***f456"

        # Short secret
        assert mask_secret("short") == "***"

        # None/empty
        assert mask_secret(None) == "***"
        assert mask_secret("") == "***"

    def test_mask_secret_custom_visible_chars(self):
        """Test custom visible character count."""
        from somali_dialect_classifier.utils.security import mask_secret

        assert mask_secret("abcdef123456", visible_chars=6) == "***123456"
        assert mask_secret("abcdef123456", visible_chars=2) == "***56"
        assert mask_secret("abcdef123456", visible_chars=8) == "***ef123456"

    def test_mask_secret_edge_cases(self):
        """Test edge cases."""
        from somali_dialect_classifier.utils.security import mask_secret

        # Short secret (below min_length default of 8)
        assert mask_secret("1234", visible_chars=4) == "***"
        assert mask_secret("12345", visible_chars=4) == "***"

        # Long enough to show characters (8+ characters)
        assert mask_secret("12345678", visible_chars=4) == "***5678"
        assert mask_secret("123456789", visible_chars=4) == "***6789"


class TestFilenameeSanitization:
    """Test filename sanitization."""

    def test_sanitize_filename_basic(self):
        """Test basic filename sanitization."""
        from somali_dialect_classifier.utils.security import sanitize_filename

        assert sanitize_filename("document.txt") == "document.txt"
        assert sanitize_filename("my_file.json") == "my_file.json"

    def test_sanitize_filename_path_traversal(self):
        """Test path traversal prevention."""
        from somali_dialect_classifier.utils.security import sanitize_filename

        # Should extract only the filename
        assert sanitize_filename("../../etc/passwd") == "passwd"
        assert sanitize_filename("../../../root/.ssh/id_rsa") == "id_rsa"
        # Note: On Unix, backslashes are part of filename, not separators
        # os.path.basename handles this correctly for the current platform
        result = sanitize_filename("..\\..\\windows\\system32\\config")
        # Accept either result depending on OS path handling
        assert result in ["config", "windowssystem32config"]

    def test_sanitize_filename_null_bytes(self):
        """Test null byte removal."""
        from somali_dialect_classifier.utils.security import sanitize_filename

        assert sanitize_filename("file\x00.txt") == "file.txt"
        assert sanitize_filename("test\x00") == "test"

    def test_sanitize_filename_empty_result(self):
        """Test invalid filenames."""
        from somali_dialect_classifier.utils.security import sanitize_filename

        with pytest.raises(ValueError, match="Invalid filename"):
            sanitize_filename("../../")

        with pytest.raises(ValueError, match="Invalid filename"):
            sanitize_filename("..")


class TestURLSanitization:
    """Test URL sanitization for SSRF prevention."""

    def test_is_safe_url_valid(self):
        """Test valid URLs are allowed."""
        from somali_dialect_classifier.utils.security import is_safe_url

        assert is_safe_url("https://example.com/page") is True
        assert is_safe_url("http://example.com/api") is True
        assert is_safe_url("https://subdomain.example.com/path?query=value") is True

    def test_is_safe_url_localhost(self):
        """Test localhost is blocked."""
        from somali_dialect_classifier.utils.security import is_safe_url

        assert is_safe_url("http://localhost:8080") is False
        assert is_safe_url("http://127.0.0.1") is False
        assert is_safe_url("http://0.0.0.0") is False
        assert is_safe_url("http://[::1]") is False

    def test_is_safe_url_file_protocol(self):
        """Test file:// protocol is blocked."""
        from somali_dialect_classifier.utils.security import is_safe_url

        assert is_safe_url("file:///etc/passwd") is False
        assert is_safe_url("file:///C:/Windows/System32") is False

    def test_is_safe_url_private_ips(self):
        """Test private IP ranges are blocked."""
        from somali_dialect_classifier.utils.security import is_safe_url

        # 10.0.0.0/8
        assert is_safe_url("http://10.0.0.1") is False
        assert is_safe_url("http://10.255.255.255") is False

        # 192.168.0.0/16
        assert is_safe_url("http://192.168.1.1") is False
        assert is_safe_url("http://192.168.255.255") is False

        # 172.16.0.0/12
        assert is_safe_url("http://172.16.0.1") is False
        assert is_safe_url("http://172.31.255.255") is False

        # Public IPs should be allowed
        assert is_safe_url("http://8.8.8.8") is True


class TestXSSPrevention:
    """Test XSS prevention in JavaScript utilities."""

    def test_dashboard_has_security_utilities(self):
        """Verify security.js exists with XSS prevention functions."""
        security_js = Path("dashboard/js/utils/security.js")
        assert security_js.exists(), "security.js utility file not found"

        content = security_js.read_text()
        assert "escapeHtml" in content, "escapeHtml function not found"
        assert "sanitizeUrl" in content, "sanitizeUrl function not found"
        assert "createSafeElement" in content, "createSafeElement function not found"


class TestSecurityIntegration:
    """Integration tests for security fixes."""

    def test_sql_injection_in_real_scenario(self, tmp_path):
        """Test SQL injection prevention in realistic usage."""
        from somali_dialect_classifier.preprocessing.crawl_ledger import (
            CrawlLedger,
            CrawlState,
        )

        ledger = CrawlLedger(db_path=tmp_path / "ledger.db")

        # Create test data
        ledger.backend.upsert_url(
            url="https://bbc.com/article1",
            source="bbc",
            state=CrawlState.PROCESSED,
            text_hash="hash1",
        )

        ledger.backend.upsert_url(
            url="https://wikipedia.org/page1",
            source="wikipedia",
            state=CrawlState.PROCESSED,
            text_hash="hash2",
        )

        # Attempt various SQL injection attacks
        injection_attempts = [
            "bbc' OR '1'='1",
            "'; DROP TABLE crawl_ledger; --",
            "' UNION SELECT * FROM crawl_ledger --",
            "bbc'; DELETE FROM crawl_ledger WHERE '1'='1",
        ]

        for attempt in injection_attempts:
            stats = ledger.backend.get_statistics(source=attempt)
            assert (
                stats["total_urls"] == 0
            ), f"SQL injection not prevented for: {attempt}"

        # Valid queries should still work
        bbc_stats = ledger.backend.get_statistics(source="bbc")
        assert bbc_stats["total_urls"] == 1

        wikipedia_stats = ledger.backend.get_statistics(source="wikipedia")
        assert wikipedia_stats["total_urls"] == 1

        ledger.close()

    def test_path_traversal_in_pipeline_init(self):
        """Test path traversal is prevented during pipeline initialization."""
        from somali_dialect_classifier.preprocessing.base_pipeline import BasePipeline

        class DummyPipeline(BasePipeline):
            def download(self):
                return None

            def extract(self):
                pass

            def _extract_records(self):
                return iter([])

            def _create_cleaner(self):
                from somali_dialect_classifier.preprocessing.text_cleaners import (
                    TextCleaningPipeline,
                )

                return TextCleaningPipeline()

            def _get_source_type(self):
                return "test"

            def _get_license(self):
                return "MIT"

            def _get_language(self):
                return "so"

            def _get_source_metadata(self):
                return {}

            def _get_domain(self):
                return "test"

            def _get_register(self):
                return "formal"

        # These should fail
        path_traversal_attempts = [
            "../etc/passwd",
            "../../root/.ssh/id_rsa",
            "..\\..\\windows\\system32",
            "wikipedia/../../../etc/hosts",
        ]

        for attempt in path_traversal_attempts:
            with pytest.raises(ValueError, match="Invalid source name"):
                DummyPipeline(source=attempt)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
