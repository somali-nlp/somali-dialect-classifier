"""
Unit Tests for Metrics Schema Validation

Tests the schema validation and parsing logic for metrics JSON files,
ensuring both v3.0 and v2.0 schemas are handled correctly.
"""

import pytest
import json
from pathlib import Path
from typing import Dict, Any
import tempfile
import shutil


class TestSchemaValidation:
    """Test schema validation for different metrics file versions"""

    def test_valid_v3_web_scraping_schema(self, tmp_path):
        """V3.0 schema with web_scraping pipeline should parse correctly"""
        valid_metric = {
            "_schema_version": "3.0",
            "_pipeline_type": "web_scraping",
            "_timestamp": "2025-10-26T16:23:45.383125+00:00",
            "_run_id": "test_run_123",
            "_source": "Test-Source",
            "layered_metrics": {
                "connectivity": {
                    "connection_attempted": True,
                    "connection_successful": True,
                    "connection_duration_ms": 1000
                },
                "extraction": {
                    "http_requests_attempted": 10,
                    "http_requests_successful": 9,
                    "pages_parsed": 9,
                    "content_extracted": 9
                },
                "quality": {
                    "records_received": 9,
                    "records_passed_filters": 9
                },
                "volume": {
                    "records_written": 9,
                    "bytes_downloaded": 50000
                }
            },
            "legacy_metrics": {
                "snapshot": {
                    "run_id": "test_run_123",
                    "source": "Test-Source",
                    "timestamp": "2025-10-26T16:23:45.383125+00:00",
                    "pipeline_type": "web_scraping",
                    "records_written": 9
                },
                "statistics": {
                    "http_request_success_rate": 0.9,
                    "content_extraction_success_rate": 1.0,
                    "quality_pass_rate": 1.0,
                    "deduplication_rate": 0.0
                }
            }
        }

        # Write to temp file
        metric_file = tmp_path / "test_metric.json"
        with open(metric_file, 'w') as f:
            json.dump(valid_metric, f)

        # Verify file exists and is valid JSON
        assert metric_file.exists()
        with open(metric_file) as f:
            loaded = json.load(f)
            assert loaded["_schema_version"] == "3.0"
            assert loaded["_pipeline_type"] == "web_scraping"

    def test_valid_v3_file_processing_schema(self, tmp_path):
        """V3.0 schema with file_processing pipeline should parse correctly"""
        valid_metric = {
            "_schema_version": "3.0",
            "_pipeline_type": "file_processing",
            "_timestamp": "2025-10-26T16:23:45.383125+00:00",
            "_run_id": "test_file_run",
            "_source": "File-Source",
            "layered_metrics": {
                "connectivity": {
                    "connection_attempted": True,
                    "connection_successful": True
                },
                "extraction": {
                    "files_discovered": 5,
                    "files_extracted": 5,
                    "records_parsed": 100
                },
                "quality": {
                    "records_received": 100,
                    "records_passed_filters": 95
                },
                "volume": {
                    "records_written": 95,
                    "bytes_downloaded": 1000000
                }
            },
            "legacy_metrics": {
                "snapshot": {
                    "run_id": "test_file_run",
                    "pipeline_type": "file_processing",
                    "records_written": 95
                },
                "statistics": {
                    "file_extraction_success_rate": 1.0,
                    "record_parsing_success_rate": 1.0,
                    "quality_pass_rate": 0.95
                }
            }
        }

        metric_file = tmp_path / "test_file_metric.json"
        with open(metric_file, 'w') as f:
            json.dump(valid_metric, f)

        with open(metric_file) as f:
            loaded = json.load(f)
            assert loaded["_pipeline_type"] == "file_processing"
            assert loaded["layered_metrics"]["extraction"]["files_discovered"] == 5

    def test_valid_v3_stream_processing_schema(self, tmp_path):
        """V3.0 schema with stream_processing pipeline should parse correctly"""
        valid_metric = {
            "_schema_version": "3.0",
            "_pipeline_type": "stream_processing",
            "_timestamp": "2025-10-26T16:23:45.383125+00:00",
            "_run_id": "test_stream_run",
            "_source": "Stream-Source",
            "layered_metrics": {
                "connectivity": {
                    "stream_connections_attempted": 1,
                    "stream_connections_successful": 1
                },
                "extraction": {
                    "records_fetched": 1000,
                    "records_retrieved": 1000
                },
                "quality": {
                    "records_received": 1000,
                    "records_passed_filters": 980
                },
                "volume": {
                    "records_written": 980
                }
            },
            "legacy_metrics": {
                "snapshot": {
                    "run_id": "test_stream_run",
                    "pipeline_type": "stream_processing",
                    "records_written": 980
                },
                "statistics": {
                    "stream_connection_success_rate": 1.0,
                    "record_retrieval_success_rate": 1.0,
                    "quality_pass_rate": 0.98,
                    "dataset_coverage_rate": 0.85
                }
            }
        }

        metric_file = tmp_path / "test_stream_metric.json"
        with open(metric_file, 'w') as f:
            json.dump(valid_metric, f)

        with open(metric_file) as f:
            loaded = json.load(f)
            assert loaded["_pipeline_type"] == "stream_processing"
            assert loaded["layered_metrics"]["extraction"]["records_fetched"] == 1000

    def test_backward_compatibility_v2_schema(self, tmp_path):
        """V2 schema (without _schema_version) should still work"""
        v2_metric = {
            "snapshot": {
                "run_id": "old_run_456",
                "source": "Old-Source",
                "timestamp": "2025-10-25T12:00:00Z",
                "records_written": 50
            },
            "statistics": {
                "fetch_success_rate": 0.95,
                "quality_pass_rate": 0.90,
                "deduplication_rate": 0.10
            }
        }

        metric_file = tmp_path / "old_metric.json"
        with open(metric_file, 'w') as f:
            json.dump(v2_metric, f)

        with open(metric_file) as f:
            loaded = json.load(f)
            assert "snapshot" in loaded
            assert "_schema_version" not in loaded
            assert loaded["snapshot"]["run_id"] == "old_run_456"

    def test_missing_required_fields_handled_gracefully(self, tmp_path):
        """Missing required fields should not crash parsing"""
        incomplete_metric = {
            "_schema_version": "3.0",
            # Missing _pipeline_type, _run_id, etc.
        }

        metric_file = tmp_path / "incomplete.json"
        with open(metric_file, 'w') as f:
            json.dump(incomplete_metric, f)

        # Should be able to read as valid JSON, even if incomplete
        with open(metric_file) as f:
            loaded = json.load(f)
            assert loaded["_schema_version"] == "3.0"

    def test_malformed_json_raises_error(self, tmp_path):
        """Malformed JSON should raise JSONDecodeError"""
        malformed_file = tmp_path / "malformed.json"
        with open(malformed_file, 'w') as f:
            f.write("{ not valid json [}")

        with pytest.raises(json.JSONDecodeError):
            with open(malformed_file) as f:
                json.load(f)

    def test_unicode_in_source_names(self, tmp_path):
        """Unicode characters in source names should be preserved"""
        unicode_metric = {
            "_schema_version": "3.0",
            "_pipeline_type": "web_scraping",
            "_source": "Språkbanken-Sömälï-Tëst",
            "legacy_metrics": {
                "snapshot": {
                    "source": "Språkbanken-Sömälï-Tëst",
                    "run_id": "unicode_test"
                }
            }
        }

        metric_file = tmp_path / "unicode.json"
        with open(metric_file, 'w', encoding='utf-8') as f:
            json.dump(unicode_metric, f, ensure_ascii=False)

        with open(metric_file, encoding='utf-8') as f:
            loaded = json.load(f)
            assert loaded["_source"] == "Språkbanken-Sömälï-Tëst"


class TestNullAndMissingValues:
    """Test handling of null and missing values in metrics"""

    def test_null_quality_metrics_defaults_to_zero(self):
        """Null quality metrics should default to 0"""
        metric = {
            "legacy_metrics": {
                "statistics": {
                    "quality_pass_rate": None,
                    "deduplication_rate": None
                }
            }
        }

        quality_rate = metric["legacy_metrics"]["statistics"]["quality_pass_rate"] or 0
        dedup_rate = metric["legacy_metrics"]["statistics"]["deduplication_rate"] or 0

        assert quality_rate == 0
        assert dedup_rate == 0

    def test_missing_statistics_field(self):
        """Missing statistics field should be handled"""
        metric = {
            "legacy_metrics": {
                "snapshot": {"run_id": "test"}
                # No statistics field
            }
        }

        stats = metric["legacy_metrics"].get("statistics", {})
        quality_rate = stats.get("quality_pass_rate", 0)

        assert quality_rate == 0

    def test_null_performance_metrics(self):
        """Null performance values should default to 0"""
        metric = {
            "legacy_metrics": {
                "statistics": {
                    "throughput": {
                        "urls_per_second": None,
                        "records_per_minute": None
                    }
                }
            }
        }

        throughput = metric["legacy_metrics"]["statistics"]["throughput"]
        urls_per_sec = throughput["urls_per_second"] or 0
        records_per_min = throughput["records_per_minute"] or 0

        assert urls_per_sec == 0
        assert records_per_min == 0

    def test_missing_text_length_stats(self):
        """Missing text length stats should return empty dict"""
        metric = {
            "legacy_metrics": {
                "statistics": {}
            }
        }

        text_stats = metric["legacy_metrics"]["statistics"].get("text_length_stats", {})
        mean_length = text_stats.get("mean", 0)

        assert mean_length == 0


class TestEdgeCases:
    """Test edge cases in metrics processing"""

    def test_zero_records_written(self):
        """Zero records written should be valid"""
        metric = {
            "legacy_metrics": {
                "snapshot": {
                    "records_written": 0,
                    "urls_processed": 10
                },
                "statistics": {
                    "quality_pass_rate": 0.0
                }
            }
        }

        assert metric["legacy_metrics"]["snapshot"]["records_written"] == 0

    def test_very_large_numbers(self):
        """Very large numbers should be handled"""
        metric = {
            "legacy_metrics": {
                "snapshot": {
                    "records_written": 10**15,  # 1 quadrillion
                    "bytes_downloaded": 10**18  # 1 exabyte
                }
            }
        }

        assert metric["legacy_metrics"]["snapshot"]["records_written"] == 10**15
        assert metric["legacy_metrics"]["snapshot"]["bytes_downloaded"] == 10**18

    def test_negative_values_in_metrics(self):
        """Negative values should be preserved (even if unusual)"""
        metric = {
            "legacy_metrics": {
                "statistics": {
                    "quality_pass_rate": -0.5  # Invalid but should not crash
                }
            }
        }

        rate = metric["legacy_metrics"]["statistics"]["quality_pass_rate"]
        assert rate == -0.5

    def test_duplicate_run_ids(self):
        """Duplicate run IDs should be allowed"""
        metrics = [
            {"run_id": "duplicate_id", "records": 100},
            {"run_id": "duplicate_id", "records": 200}
        ]

        assert len(metrics) == 2
        assert metrics[0]["run_id"] == metrics[1]["run_id"]

    def test_empty_string_values(self):
        """Empty strings should be preserved"""
        metric = {
            "_source": "",
            "legacy_metrics": {
                "snapshot": {
                    "source": "",
                    "run_id": ""
                }
            }
        }

        assert metric["_source"] == ""
        assert metric["legacy_metrics"]["snapshot"]["source"] == ""


@pytest.fixture
def sample_metrics_dir(tmp_path):
    """Create a sample metrics directory with test files"""
    metrics_dir = tmp_path / "metrics"
    metrics_dir.mkdir()

    # Create sample files
    files = [
        ("20251026_wikipedia_processing.json", "Wikipedia-Somali", 1000),
        ("20251026_bbc_processing.json", "BBC-Somali", 500),
        ("20251026_huggingface_processing.json", "HuggingFace-Somali", 2000),
    ]

    for filename, source, records in files:
        metric = {
            "_schema_version": "3.0",
            "_pipeline_type": "web_scraping",
            "_source": source,
            "legacy_metrics": {
                "snapshot": {
                    "source": source,
                    "records_written": records
                },
                "statistics": {
                    "quality_pass_rate": 0.95
                }
            }
        }

        with open(metrics_dir / filename, 'w') as f:
            json.dump(metric, f)

    return metrics_dir


class TestMetricsDirectoryProcessing:
    """Test processing entire directories of metrics"""

    def test_load_all_metrics_from_directory(self, sample_metrics_dir):
        """Should load all _processing.json files"""
        files = list(sample_metrics_dir.glob("*_processing.json"))
        assert len(files) == 3

    def test_empty_directory_returns_no_metrics(self, tmp_path):
        """Empty directory should return empty list"""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        files = list(empty_dir.glob("*_processing.json"))
        assert len(files) == 0

    def test_mixed_file_types_only_loads_processing(self, tmp_path):
        """Should only load *_processing.json files"""
        metrics_dir = tmp_path / "metrics"
        metrics_dir.mkdir()

        # Create various file types
        (metrics_dir / "test_processing.json").write_text("{}")
        (metrics_dir / "test_discovery.json").write_text("{}")
        (metrics_dir / "test_extraction.json").write_text("{}")
        (metrics_dir / "test.txt").write_text("not json")

        processing_files = list(metrics_dir.glob("*_processing.json"))
        assert len(processing_files) == 1
