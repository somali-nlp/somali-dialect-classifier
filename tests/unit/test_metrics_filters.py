"""Unit tests for somdialc.infra.metrics_filters.

Pure functions over consolidated-metrics dicts; no I/O beyond
export_filtered_metrics(), which uses tmp_path.
"""

import json

from somdialc.infra.metrics_filters import (
    apply_filters,
    export_filtered_metrics,
    filter_by_date_range,
    filter_by_pipeline_type,
    filter_by_quality,
    filter_by_records_threshold,
    filter_by_source,
    filter_by_status,
    get_recent_metrics,
    get_top_performers,
    search_metrics,
)


def _metric(**overrides):
    base = {
        "source": "BBC-Somali",
        "run_id": "run-1",
        "quality_pass_rate": 0.9,
        "records_written": 500,
        "pipeline_type": "web_scraping",
        "http_request_success_rate": 0.95,
        "timestamp": "2026-06-15T10:00:00Z",
    }
    base.update(overrides)
    return base


class TestFilterBySource:
    def test_empty_sources_returns_all(self):
        metrics = [_metric(), _metric(source="Wikipedia-Somali")]
        assert filter_by_source(metrics, []) == metrics

    def test_filters_case_insensitively(self):
        metrics = [_metric(source="BBC-Somali"), _metric(source="Wikipedia-Somali")]
        result = filter_by_source(metrics, ["bbc-somali"])
        assert len(result) == 1
        assert result[0]["source"] == "BBC-Somali"

    def test_no_match_returns_empty(self):
        metrics = [_metric(source="BBC-Somali")]
        assert filter_by_source(metrics, ["Nonexistent-Source"]) == []


class TestFilterByQuality:
    def test_filters_below_threshold(self):
        metrics = [_metric(quality_pass_rate=0.5), _metric(quality_pass_rate=0.95)]
        result = filter_by_quality(metrics, threshold=0.8)
        assert len(result) == 1
        assert result[0]["quality_pass_rate"] == 0.95

    def test_invalid_threshold_returns_unfiltered(self):
        metrics = [_metric(quality_pass_rate=0.5)]
        result = filter_by_quality(metrics, threshold=1.5)
        assert result == metrics

    def test_custom_metric_name(self):
        metrics = [{"custom_score": 0.9}, {"custom_score": 0.1}]
        result = filter_by_quality(metrics, threshold=0.5, metric_name="custom_score")
        assert len(result) == 1


class TestFilterByDateRange:
    def test_no_dates_returns_all(self):
        metrics = [_metric()]
        assert filter_by_date_range(metrics) == metrics

    def test_filters_before_start_date(self):
        metrics = [
            _metric(timestamp="2026-01-01T00:00:00Z"),
            _metric(timestamp="2026-06-15T00:00:00Z"),
        ]
        result = filter_by_date_range(metrics, start_date="2026-05-01")
        assert len(result) == 1
        assert result[0]["timestamp"] == "2026-06-15T00:00:00Z"

    def test_filters_after_end_date(self):
        metrics = [
            _metric(timestamp="2026-01-01T00:00:00Z"),
            _metric(timestamp="2026-06-15T00:00:00Z"),
        ]
        result = filter_by_date_range(metrics, end_date="2026-02-01")
        assert len(result) == 1
        assert result[0]["timestamp"] == "2026-01-01T00:00:00Z"

    def test_skips_metrics_without_timestamp(self):
        metrics = [{"source": "BBC-Somali"}]
        result = filter_by_date_range(metrics, start_date="2026-01-01")
        assert result == []

    def test_skips_metrics_with_unparseable_timestamp(self):
        metrics = [_metric(timestamp="not-a-date")]
        result = filter_by_date_range(metrics, start_date="2026-01-01")
        assert result == []

    def test_invalid_start_date_format_returns_unfiltered(self):
        metrics = [_metric()]
        result = filter_by_date_range(metrics, start_date="not-a-date")
        assert result == metrics


class TestFilterByStatus:
    def test_healthy_status(self):
        metrics = [_metric(http_request_success_rate=0.95)]
        result = filter_by_status(metrics, status="healthy")
        assert len(result) == 1

    def test_degraded_status(self):
        metrics = [_metric(http_request_success_rate=0.75)]
        result = filter_by_status(metrics, status="degraded")
        assert len(result) == 1

    def test_unhealthy_status(self):
        metrics = [_metric(http_request_success_rate=0.5)]
        result = filter_by_status(metrics, status="unhealthy")
        assert len(result) == 1

    def test_unknown_status_returns_unfiltered(self):
        metrics = [_metric()]
        result = filter_by_status(metrics, status="on-fire")
        assert result == metrics

    def test_file_processing_pipeline_type_uses_extraction_rate(self):
        metrics = [
            _metric(pipeline_type="file_processing", file_extraction_success_rate=0.95),
        ]
        result = filter_by_status(metrics, status="healthy")
        assert len(result) == 1

    def test_stream_processing_pipeline_type_uses_connection_rate(self):
        metrics = [
            _metric(pipeline_type="stream_processing", stream_connection_success_rate=0.95),
        ]
        result = filter_by_status(metrics, status="healthy")
        assert len(result) == 1

    def test_unknown_pipeline_type_falls_back_to_http_rate(self):
        metrics = [_metric(pipeline_type="mystery_type", http_request_success_rate=0.95)]
        result = filter_by_status(metrics, status="healthy")
        assert len(result) == 1


class TestFilterByRecordsThreshold:
    def test_min_records_filters_below(self):
        metrics = [_metric(records_written=100), _metric(records_written=1000)]
        result = filter_by_records_threshold(metrics, min_records=500)
        assert len(result) == 1
        assert result[0]["records_written"] == 1000

    def test_max_records_filters_above(self):
        metrics = [_metric(records_written=100), _metric(records_written=1000)]
        result = filter_by_records_threshold(metrics, max_records=500)
        assert len(result) == 1
        assert result[0]["records_written"] == 100

    def test_no_bounds_returns_all(self):
        metrics = [_metric(records_written=100), _metric(records_written=1000)]
        assert filter_by_records_threshold(metrics) == metrics


class TestFilterByPipelineType:
    def test_empty_list_returns_all(self):
        metrics = [_metric()]
        assert filter_by_pipeline_type(metrics, []) == metrics

    def test_filters_case_insensitively(self):
        metrics = [
            _metric(pipeline_type="web_scraping"),
            _metric(pipeline_type="file_processing"),
        ]
        result = filter_by_pipeline_type(metrics, ["WEB_SCRAPING"])
        assert len(result) == 1
        assert result[0]["pipeline_type"] == "web_scraping"


class TestApplyFilters:
    def test_no_filters_returns_all(self):
        metrics = [_metric()]
        assert apply_filters(metrics) == metrics

    def test_combines_multiple_filters(self):
        metrics = [
            _metric(source="BBC-Somali", quality_pass_rate=0.95, records_written=1000),
            _metric(source="BBC-Somali", quality_pass_rate=0.2, records_written=1000),
            _metric(source="Wikipedia-Somali", quality_pass_rate=0.95, records_written=1000),
        ]
        result = apply_filters(
            metrics,
            sources=["BBC-Somali"],
            quality_threshold=0.8,
            min_records=500,
        )
        assert len(result) == 1
        assert result[0]["source"] == "BBC-Somali"
        assert result[0]["quality_pass_rate"] == 0.95

    def test_status_and_pipeline_type_filters_applied(self):
        metrics = [_metric(pipeline_type="web_scraping", http_request_success_rate=0.95)]
        result = apply_filters(metrics, status="healthy", pipeline_types=["web_scraping"])
        assert len(result) == 1


class TestExportFilteredMetrics:
    def test_writes_json_file_with_filtered_metrics(self, tmp_path):
        metrics = [_metric(source="BBC-Somali"), _metric(source="Wikipedia-Somali")]
        output_file = tmp_path / "out" / "filtered.json"

        output = export_filtered_metrics(metrics, str(output_file), sources=["BBC-Somali"])

        assert output["count"] == 1
        assert output_file.exists()

        with open(output_file, encoding="utf-8") as f:
            written = json.load(f)
        assert written["count"] == 1
        assert written["filters_applied"] == {"sources": ["BBC-Somali"]}


class TestSearchMetrics:
    def test_empty_query_returns_all(self):
        metrics = [_metric()]
        assert search_metrics(metrics, "") == metrics

    def test_matches_default_fields(self):
        metrics = [_metric(source="BBC-Somali"), _metric(source="Wikipedia-Somali")]
        result = search_metrics(metrics, "bbc")
        assert len(result) == 1

    def test_matches_custom_fields(self):
        metrics = [{"custom_field": "hello world"}]
        result = search_metrics(metrics, "world", fields=["custom_field"])
        assert len(result) == 1


class TestGetTopPerformers:
    def test_sorts_descending_and_limits(self):
        metrics = [
            _metric(quality_pass_rate=0.5),
            _metric(quality_pass_rate=0.9),
            _metric(quality_pass_rate=0.7),
        ]
        result = get_top_performers(metrics, top_n=2)
        assert [m["quality_pass_rate"] for m in result] == [0.9, 0.7]


class TestGetRecentMetrics:
    def test_filters_out_old_metrics(self):
        from datetime import datetime, timedelta

        recent_ts = datetime.now().isoformat()
        old_ts = (datetime.now() - timedelta(days=30)).isoformat()
        metrics = [_metric(timestamp=recent_ts), _metric(timestamp=old_ts)]

        result = get_recent_metrics(metrics, num_days=7)
        assert len(result) == 1
        assert result[0]["timestamp"] == recent_ts

    def test_skips_missing_or_unparseable_timestamps(self):
        metrics = [{"source": "BBC-Somali"}, _metric(timestamp="garbage")]
        assert get_recent_metrics(metrics) == []
