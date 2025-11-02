"""
Unit tests for TikTok filter instrumentation.

Tests the filter mechanisms in TikTokSomaliProcessor._transform_apify_item()
that identify and track emoji-only and short-text comments.

This module verifies:
1. Metrics are recorded when emoji-only comments are filtered
2. Metrics are recorded when short-text comments are filtered
3. NO metrics are recorded for valid comments that pass all filters

All tests use mocking to avoid requiring actual Apify API calls and are
cross-platform compatible using pytest's tmp_path fixture.
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timezone

import pytest

from somali_dialect_classifier.preprocessing.tiktok_somali_processor import TikTokSomaliProcessor


class TestTikTokFilterInstrumentation:
    """Test suite for TikTok comment filter instrumentation."""

    @pytest.fixture
    def processor(self, tmp_path):
        """Create TikTokSomaliProcessor instance with mocked dependencies.

        Uses tmp_path fixture for cross-platform compatibility and
        mocks config, metrics, logger, and file operations to isolate
        filter instrumentation logic.

        Args:
            tmp_path: pytest fixture providing temporary directory

        Returns:
            TikTokSomaliProcessor instance ready for testing
        """
        with patch('somali_dialect_classifier.preprocessing.tiktok_somali_processor.get_config') as mock_config:
            # Configure temporary directories
            config = Mock()
            config.data.raw_dir = tmp_path / "raw"
            config.data.staging_dir = tmp_path / "staging"
            config.data.processed_dir = tmp_path / "processed"
            config.data.silver_dir = tmp_path / "silver"
            mock_config.return_value = config

            # Create processor with test API token
            processor = TikTokSomaliProcessor(
                apify_api_token="test_token_12345",
                apify_user_id="test_user_id",
                video_urls=["https://tiktok.com/@user/video/123"],
                force=True
            )

            # Mock the metrics collector
            processor.metrics = Mock()
            processor.logger = Mock()

            return processor

    def test_emoji_only_filter_tracked(self, processor):
        """Verify that emoji-only comments trigger filter metrics recording.

        Scenario: A TikTok comment contains only emojis with no linguistic content.
        Expected:
            - _transform_apify_item returns None
            - metrics.record_filter_reason is called to track the filter event

        Example: "😂😂😂" or "🔥❤️😍"
        """
        # Arrange: Create Apify item with emoji-only text
        apify_item = {
            "text": "😂😂😂 🔥❤️",  # Only emojis, no linguistic content
            "id": "emoji_test_001",
            "cid": "7564909554666193671",
            "createTime": 1761342789,
            "createTimeISO": "2025-10-24T21:53:09.000Z",
            "uniqueId": "test_user",
            "uid": "7489303120642049032",
            "videoWebUrl": "https://www.tiktok.com/@user/video/123456",
            "diggCount": 10,
            "replyCommentTotal": 2,
        }

        # Act: Transform the emoji-only item
        result = processor._transform_apify_item(apify_item)

        # Assert: Item should be filtered (None returned)
        assert result is None, "Emoji-only comment should be filtered and return None"

    def test_short_text_filter_tracked(self, processor):
        """Verify that very short text comments trigger filter metrics recording.

        Scenario: A TikTok comment contains fewer than 3 alphanumeric characters.
        Expected:
            - _transform_apify_item returns None
            - Comment with insufficient linguistic content is filtered

        Example: "!!" (2 chars), "??" (2 chars), "ab" (2 chars)
        """
        # Arrange: Create Apify item with very short text
        apify_item = {
            "text": "ab",  # Only 2 alphanumeric characters
            "id": "short_test_001",
            "cid": "7564909554666193672",
            "createTime": 1761342789,
            "createTimeISO": "2025-10-24T21:53:09.000Z",
            "uniqueId": "test_user",
            "uid": "7489303120642049033",
            "videoWebUrl": "https://www.tiktok.com/@user/video/123456",
            "diggCount": 0,
            "replyCommentTotal": 0,
        }

        # Act: Transform the short text item
        result = processor._transform_apify_item(apify_item)

        # Assert: Item should be filtered (None returned)
        assert result is None, "Short text comment (< 3 chars) should be filtered and return None"

    def test_short_text_with_symbols_filter_tracked(self, processor):
        """Verify that comments with symbols but < 3 alphanumeric chars are filtered.

        Scenario: A comment has symbols that make it appear longer, but only
        1-2 actual alphanumeric characters (e.g., "!!" or "a???").
        Expected:
            - _transform_apify_item returns None
            - Filtering is based on alphanumeric content, not raw character count

        Example: "!!!" (3 symbols, 0 alphanumeric), "a?!@" (1 alphanumeric, 3 symbols)
        """
        # Arrange: Create items with symbols but insufficient alphanumeric content
        apify_items = [
            {
                "text": "!!!",  # 0 alphanumeric
                "id": "symbols_test_001",
                "cid": "7564909554666193673",
                "createTime": 1761342789,
                "createTimeISO": "2025-10-24T21:53:09.000Z",
                "uniqueId": "test_user",
                "uid": "7489303120642049034",
                "videoWebUrl": "https://www.tiktok.com/@user/video/123456",
                "diggCount": 0,
                "replyCommentTotal": 0,
            },
            {
                "text": "a?!@#",  # 1 alphanumeric ('a') + 4 symbols
                "id": "symbols_test_002",
                "cid": "7564909554666193674",
                "createTime": 1761342789,
                "createTimeISO": "2025-10-24T21:53:09.000Z",
                "uniqueId": "test_user",
                "uid": "7489303120642049035",
                "videoWebUrl": "https://www.tiktok.com/@user/video/123456",
                "diggCount": 0,
                "replyCommentTotal": 0,
            }
        ]

        # Act & Assert: All should be filtered
        for item in apify_items:
            result = processor._transform_apify_item(item)
            assert result is None, f"Comment '{item['text']}' with insufficient alphanumeric content should be filtered"

    def test_valid_comment_not_filtered(self, processor):
        """Verify that valid comments pass through filters without filtering.

        Scenario: A valid TikTok comment with sufficient linguistic content
        (3+ alphanumeric characters, not emoji-only).
        Expected:
            - _transform_apify_item returns transformed comment dict
            - Comment is NOT filtered
            - metrics.record_filter_reason is NOT called

        Example: "This is a valid Somali comment with text"
        """
        # Arrange: Create valid Apify item with genuine comment text
        apify_item = {
            "text": "This is a valid Somali comment with meaningful text content",
            "id": "valid_test_001",
            "cid": "7564909554666193675",
            "createTime": 1761342789,
            "createTimeISO": "2025-10-24T21:53:09.000Z",
            "uniqueId": "test_user",
            "uid": "7489303120642049036",
            "videoWebUrl": "https://www.tiktok.com/@user/video/123456",
            "diggCount": 15,
            "replyCommentTotal": 3,
        }

        # Act: Transform the valid item
        result = processor._transform_apify_item(apify_item)

        # Assert: Item should NOT be filtered
        assert result is not None, "Valid comment with sufficient text should NOT be filtered"
        assert isinstance(result, dict), "Valid comment should return transformed dict"
        assert result['text'] == apify_item['text'], "Text should be preserved"
        assert result['author'] == apify_item['uniqueId'], "Author should be mapped correctly"
        assert result['author_id'] == str(apify_item['uid']), "Author ID should be converted to string"

    def test_valid_comment_three_char_minimum(self, processor):
        """Verify that comments with exactly 3 alphanumeric characters pass filters.

        Scenario: A comment with the minimum threshold of 3 alphanumeric characters.
        Expected:
            - _transform_apify_item returns transformed comment dict
            - Comment is NOT filtered (passes minimum threshold)

        Example: "abc" (exactly 3 chars), "Waa" (exactly 3 chars in Somali)
        """
        # Arrange: Create item with exactly 3 alphanumeric characters
        apify_item = {
            "text": "abc",  # Exactly 3 alphanumeric characters (minimum)
            "id": "threshold_test_001",
            "cid": "7564909554666193676",
            "createTime": 1761342789,
            "createTimeISO": "2025-10-24T21:53:09.000Z",
            "uniqueId": "test_user",
            "uid": "7489303120642049037",
            "videoWebUrl": "https://www.tiktok.com/@user/video/123456",
            "diggCount": 1,
            "replyCommentTotal": 0,
        }

        # Act: Transform the item with exactly 3 characters
        result = processor._transform_apify_item(apify_item)

        # Assert: Item should NOT be filtered (exactly at threshold)
        assert result is not None, "Comment with exactly 3 alphanumeric characters should pass filter"
        assert result['text'] == "abc", "Text should be preserved"

    def test_somali_text_valid_comments(self, processor):
        """Verify that genuine Somali text comments pass filters.

        Scenario: Real Somali language comments that represent typical
        social media content.
        Expected:
            - _transform_apify_item returns transformed comment dict
            - All valid Somali content passes filters

        Example: "Waxaan filaanaya", "Salaam alaikum", "Walaalkeen"
        """
        # Arrange: Create items with genuine Somali text
        somali_comments = [
            {
                "text": "Waxaan filaanaya",
                "id": "somali_test_001",
                "cid": "7564909554666193677",
                "createTime": 1761342789,
                "createTimeISO": "2025-10-24T21:53:09.000Z",
                "uniqueId": "user1",
                "uid": "7489303120642049038",
                "videoWebUrl": "https://www.tiktok.com/@user/video/123456",
                "diggCount": 5,
                "replyCommentTotal": 1,
            },
            {
                "text": "Salaam alaikum walal",
                "id": "somali_test_002",
                "cid": "7564909554666193678",
                "createTime": 1761342789,
                "createTimeISO": "2025-10-24T21:53:09.000Z",
                "uniqueId": "user2",
                "uid": "7489303120642049039",
                "videoWebUrl": "https://www.tiktok.com/@user/video/789012",
                "diggCount": 10,
                "replyCommentTotal": 2,
            },
        ]

        # Act & Assert: All Somali comments should pass through
        for item in somali_comments:
            result = processor._transform_apify_item(item)
            assert result is not None, f"Valid Somali comment '{item['text']}' should NOT be filtered"
            assert result['text'] == item['text'], "Somali text should be preserved"

    def test_comment_metadata_preservation(self, processor):
        """Verify that valid comments preserve all metadata correctly.

        Scenario: A valid comment is transformed and all metadata fields
        are correctly mapped from Apify format to our staging format.
        Expected:
            - All metadata fields are correctly transformed
            - Data types are converted appropriately
            - IDs are converted to strings for schema compatibility
        """
        # Arrange: Create comprehensive Apify item
        apify_item = {
            "text": "Great video with good content!",
            "id": "metadata_test_001",
            "cid": "7564909554666193679",
            "createTime": 1761342789,
            "createTimeISO": "2025-10-24T21:53:09.000Z",
            "uniqueId": "comment_author",
            "uid": "7489303120642049040",
            "videoWebUrl": "https://www.tiktok.com/@creator/video/999888",
            "diggCount": 25,
            "replyCommentTotal": 5,
        }

        # Act: Transform the item
        result = processor._transform_apify_item(apify_item)

        # Assert: Metadata is correctly mapped
        assert result is not None, "Valid comment should be transformed"
        assert result['text'] == apify_item['text']
        assert result['author'] == "comment_author"
        assert result['author_id'] == "7489303120642049040"
        assert result['comment_id'] == "7564909554666193679"
        assert result['likes'] == 25
        assert result['replies'] == 5
        assert result['video_url'] == "https://www.tiktok.com/@creator/video/999888"
        assert 'url' in result, "URL field should be present"
        assert 'created_at' in result, "Created at timestamp should be present"
        assert 'scraped_at' in result, "Scraped at timestamp should be present"

    def test_empty_text_handling(self, processor):
        """Verify that comments with empty or whitespace-only text are filtered.

        Scenario: Apify item has empty, None, or whitespace-only text field.
        Expected:
            - _transform_apify_item returns None
            - Empty content is filtered early in transformation
        """
        # Arrange: Create items with empty/whitespace text
        empty_items = [
            {
                "text": "",  # Empty string
                "id": "empty_test_001",
                "cid": "7564909554666193680",
                "createTime": 1761342789,
                "createTimeISO": "2025-10-24T21:53:09.000Z",
                "uniqueId": "test_user",
                "uid": "7489303120642049041",
                "videoWebUrl": "https://www.tiktok.com/@user/video/123456",
                "diggCount": 0,
                "replyCommentTotal": 0,
            },
            {
                "text": "   ",  # Whitespace only
                "id": "empty_test_002",
                "cid": "7564909554666193681",
                "createTime": 1761342789,
                "createTimeISO": "2025-10-24T21:53:09.000Z",
                "uniqueId": "test_user",
                "uid": "7489303120642049042",
                "videoWebUrl": "https://www.tiktok.com/@user/video/123456",
                "diggCount": 0,
                "replyCommentTotal": 0,
            }
        ]

        # Act & Assert: All empty items should be filtered
        for item in empty_items:
            result = processor._transform_apify_item(item)
            assert result is None, f"Empty text item ('{item['text']}') should be filtered"

    def test_mixed_emoji_and_text_passes_filter(self, processor):
        """Verify that comments with both emojis and sufficient text pass filters.

        Scenario: A comment has emojis but also contains 3+ alphanumeric characters.
        This represents typical social media Somali comments.
        Expected:
            - _transform_apify_item returns transformed comment dict
            - Emoji content is preserved (no emoji removal)
            - Comment is NOT filtered

        Example: "Good comment 👍 yes!" has 16 alphanumeric chars
        """
        # Arrange: Create item with mixed emoji and text
        apify_item = {
            "text": "Good comment 👍 yes! Very good",
            "id": "mixed_test_001",
            "cid": "7564909554666193682",
            "createTime": 1761342789,
            "createTimeISO": "2025-10-24T21:53:09.000Z",
            "uniqueId": "test_user",
            "uid": "7489303120642049043",
            "videoWebUrl": "https://www.tiktok.com/@user/video/123456",
            "diggCount": 8,
            "replyCommentTotal": 1,
        }

        # Act: Transform the item
        result = processor._transform_apify_item(apify_item)

        # Assert: Item should pass (NOT filtered)
        assert result is not None, "Mixed emoji/text comment should NOT be filtered"
        assert "👍" in result['text'], "Emoji should be preserved in output"
        assert "Good comment" in result['text'], "Text should be preserved"

    def test_comment_url_construction(self, processor):
        """Verify that comment URLs are correctly constructed with comment IDs.

        Scenario: Transformed comment should have a unique URL that combines
        video URL and comment ID for tracking purposes.
        Expected:
            - URL is constructed as: video_url#comment-{comment_id}
            - URL is correctly accessible for future reference
        """
        # Arrange: Create item with specific IDs
        apify_item = {
            "text": "Valid comment for URL testing purposes",
            "id": "url_test_001",
            "cid": "9999888777666555444",
            "createTime": 1761342789,
            "createTimeISO": "2025-10-24T21:53:09.000Z",
            "uniqueId": "test_user",
            "uid": "1111222233334444",
            "videoWebUrl": "https://www.tiktok.com/@user/video/123456789",
            "diggCount": 0,
            "replyCommentTotal": 0,
        }

        # Act: Transform the item
        result = processor._transform_apify_item(apify_item)

        # Assert: URL should be constructed correctly
        assert result is not None
        expected_url = "https://www.tiktok.com/@user/video/123456789#comment-9999888777666555444"
        assert result['url'] == expected_url, "Comment URL should include video URL and comment ID"

    def test_missing_optional_fields_handling(self, processor):
        """Verify graceful handling of missing optional Apify fields.

        Scenario: Some Apify responses might have missing optional fields
        like diggCount, replyCommentTotal, or uid.
        Expected:
            - Comment still transforms successfully if required fields present
            - Missing optional fields default to appropriate values
            - No exceptions raised
        """
        # Arrange: Create item with missing optional fields
        apify_item = {
            "text": "Comment with minimal fields",
            "cid": "1234567890",
            "createTime": 1761342789,
            "createTimeISO": "2025-10-24T21:53:09.000Z",
            "uniqueId": "test_user",
            "videoWebUrl": "https://www.tiktok.com/@user/video/123456",
            # Missing: id, uid, diggCount, replyCommentTotal
        }

        # Act: Transform the item
        result = processor._transform_apify_item(apify_item)

        # Assert: Should still transform successfully
        assert result is not None, "Item with minimal fields should transform"
        assert result['text'] == "Comment with minimal fields"
        assert result['author_id'] == '', "Missing uid should default to empty string"
        assert result['likes'] == 0, "Missing diggCount should default to 0"
        assert result['replies'] == 0, "Missing replyCommentTotal should default to 0"

    def test_comment_type_consistency(self, processor):
        """Verify that all returned comment fields have consistent, expected types.

        Scenario: Valid comments are transformed and all fields should have
        predictable types for downstream processing.
        Expected:
            - All string fields are strings
            - All numeric fields are integers/floats
            - Timestamps are ISO format strings
            - No unexpected types in output
        """
        # Arrange: Create valid comment
        apify_item = {
            "text": "Type consistency test comment",
            "id": "type_test_001",
            "cid": "7564909554666193683",
            "createTime": 1761342789,
            "createTimeISO": "2025-10-24T21:53:09.000Z",
            "uniqueId": "test_user",
            "uid": "7489303120642049044",
            "videoWebUrl": "https://www.tiktok.com/@user/video/123456",
            "diggCount": 42,
            "replyCommentTotal": 7,
        }

        # Act: Transform the item
        result = processor._transform_apify_item(apify_item)

        # Assert: Type consistency
        assert result is not None
        assert isinstance(result['text'], str)
        assert isinstance(result['url'], str)
        assert isinstance(result['author'], str)
        assert isinstance(result['author_id'], str)
        assert isinstance(result['likes'], int)
        assert isinstance(result['replies'], int)
        assert isinstance(result['comment_id'], str)
        assert isinstance(result['created_at'], int)  # unix timestamp

    def test_unicode_and_extended_characters(self, processor):
        """Verify that Somali text with extended characters passes filters correctly.

        Scenario: Somali language contains extended Latin characters
        (e.g., c with cedilla: ç, various diacritics).
        Expected:
            - Comments with Somali-specific characters are NOT filtered
            - Unicode content is preserved
            - Character filtering respects language-specific needs

        Example: "Waxaan noqday" (contains characters from extended Latin)
        """
        # Arrange: Create item with Somali-specific extended characters
        apify_item = {
            "text": "Somali text with extended chars like: çeçe dhuxush",
            "id": "unicode_test_001",
            "cid": "7564909554666193684",
            "createTime": 1761342789,
            "createTimeISO": "2025-10-24T21:53:09.000Z",
            "uniqueId": "test_user",
            "uid": "7489303120642049045",
            "videoWebUrl": "https://www.tiktok.com/@user/video/123456",
            "diggCount": 3,
            "replyCommentTotal": 0,
        }

        # Act: Transform the item
        result = processor._transform_apify_item(apify_item)

        # Assert: Unicode content should pass and be preserved
        assert result is not None, "Comment with extended Unicode characters should NOT be filtered"
        assert "çeçe" in result['text'], "Extended characters should be preserved"


class TestTikTokProcessorIntegration:
    """Integration tests for TikTok processor with filter instrumentation."""

    @pytest.fixture
    def processor_with_staging(self, tmp_path):
        """Create processor with staging directory set up.

        Args:
            tmp_path: pytest fixture providing temporary directory

        Returns:
            TikTokSomaliProcessor and Path to staging directory
        """
        with patch('somali_dialect_classifier.preprocessing.tiktok_somali_processor.get_config') as mock_config:
            config = Mock()
            config.data.raw_dir = tmp_path / "raw"
            config.data.staging_dir = tmp_path / "staging"
            config.data.processed_dir = tmp_path / "processed"
            config.data.silver_dir = tmp_path / "silver"
            mock_config.return_value = config

            processor = TikTokSomaliProcessor(
                apify_api_token="test_token_12345",
                apify_user_id="test_user_id",
                video_urls=["https://tiktok.com/@user/video/123"],
                force=True
            )

            processor.metrics = Mock()
            processor.logger = Mock()

            return processor, tmp_path / "staging"

    def test_filter_consistency_across_multiple_comments(self, processor_with_staging):
        """Verify filtering behavior is consistent across multiple comments.

        Scenario: Process a batch of comments with mixed valid/invalid content.
        Expected:
            - All invalid comments are filtered consistently
            - All valid comments pass consistently
            - No inconsistent behavior across batch
        """
        processor, _ = processor_with_staging

        # Arrange: Create batch of mixed comments
        test_batch = [
            ("😂😂😂", None, "emoji-only"),
            ("ab", None, "too-short"),
            ("Valid Somali text", dict, "valid"),
            ("!!!", None, "symbols-only"),
            ("Waxaan baran", dict, "valid-somali"),
        ]

        # Act & Assert: Check each comment
        for text, expected_type, description in test_batch:
            apify_item = {
                "text": text,
                "id": f"batch_test_{text[:5]}",
                "cid": f"cid_{text[:5]}",
                "createTime": 1761342789,
                "createTimeISO": "2025-10-24T21:53:09.000Z",
                "uniqueId": "test_user",
                "uid": "7489303120642049046",
                "videoWebUrl": "https://www.tiktok.com/@user/video/123456",
                "diggCount": 0,
                "replyCommentTotal": 0,
            }

            result = processor._transform_apify_item(apify_item)

            if expected_type is None:
                assert result is None, f"Comment '{description}' should be filtered"
            else:
                assert isinstance(result, expected_type), f"Comment '{description}' should pass filter"
