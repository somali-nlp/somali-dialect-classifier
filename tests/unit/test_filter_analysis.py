"""Unit tests for somdialc.infra.filter_analysis.

Covers FilteredSample, FilterAnalyzer, create_filter_analyzer(), and
analyze_filter_impact() -- quality-control insight utilities used to explain
why records were dropped during ingestion.
"""

import json

from somdialc.infra.filter_analysis import (
    FilterAnalyzer,
    FilteredSample,
    analyze_filter_impact,
    create_filter_analyzer,
)


class TestFilteredSample:
    def test_to_dict_contains_all_fields(self):
        sample = FilteredSample(
            record_id="abc123",
            title="Soomaaliya",
            text_preview="Soomaaliya waa dal...",
            filter_name="min_length_filter",
            reason="too short",
            metadata={"length": 10},
        )
        data = sample.to_dict()
        assert data["record_id"] == "abc123"
        assert data["title"] == "Soomaaliya"
        assert data["filter_name"] == "min_length_filter"
        assert data["reason"] == "too short"
        assert data["metadata"] == {"length": 10}
        assert "timestamp" in data

    def test_metadata_defaults_to_empty_dict(self):
        sample = FilteredSample(record_id="abc", title="T", text_preview="preview", filter_name="f")
        assert sample.metadata == {}


class TestFilterAnalyzerBasics:
    def test_init_defaults(self):
        analyzer = FilterAnalyzer(source="BBC-Somali")
        assert analyzer.source == "BBC-Somali"
        assert analyzer.sampling_rate == 0.0
        assert analyzer.total_processed == 0
        assert analyzer.total_passed == 0
        assert analyzer.total_filtered == 0

    def test_enable_sampling_clamps_rate(self):
        analyzer = FilterAnalyzer(source="BBC-Somali")
        analyzer.enable_sampling(rate=5.0)
        assert analyzer.sampling_rate == 1.0

        analyzer.enable_sampling(rate=-1.0)
        assert analyzer.sampling_rate == 0.0

    def test_record_processed_increments_counter(self):
        analyzer = FilterAnalyzer(source="BBC-Somali")
        analyzer.record_processed()
        analyzer.record_processed()
        assert analyzer.total_processed == 2

    def test_record_passed_increments_counter(self):
        analyzer = FilterAnalyzer(source="BBC-Somali")
        analyzer.record_passed({"id": "1"})
        assert analyzer.total_passed == 1


class TestFilterAnalyzerRecordFiltered:
    def test_increments_filter_counts(self):
        analyzer = FilterAnalyzer(source="BBC-Somali")
        analyzer.record_filtered("id1", "Title", "text", "min_length_filter", reason="short")
        analyzer.record_filtered("id2", "Title2", "text2", "min_length_filter", reason="short")

        assert analyzer.total_filtered == 2
        assert analyzer.get_filter_breakdown() == {"min_length_filter": 2}

    def test_tracks_reasons(self):
        analyzer = FilterAnalyzer(source="BBC-Somali")
        analyzer.record_filtered("id1", "T", "text", "langid_filter", reason="not somali")
        analyzer.record_filtered("id2", "T", "text", "langid_filter", reason="not somali")

        report = analyzer.generate_report()
        top_reasons = report["filter_breakdown"]["langid_filter"]["top_reasons"]
        assert top_reasons == {"not somali": 2}

    def test_sampling_records_sample_when_enabled(self):
        analyzer = FilterAnalyzer(source="BBC-Somali", sampling_rate=1.0)
        long_text = "x" * 300

        analyzer.record_filtered("id1", "Title", long_text, "min_length_filter", reason="short")

        samples = analyzer.filtered_samples["min_length_filter"]
        assert len(samples) == 1
        assert samples[0].text_preview.endswith("...")
        assert len(samples[0].text_preview) == 203  # 200 chars + "..."

    def test_sampling_respects_max_samples_per_filter(self):
        analyzer = FilterAnalyzer(source="BBC-Somali", sampling_rate=1.0, max_samples_per_filter=2)
        for i in range(5):
            analyzer.record_filtered(f"id{i}", "T", "short text", "min_length_filter")

        assert len(analyzer.filtered_samples["min_length_filter"]) == 2

    def test_no_sampling_when_rate_zero(self):
        analyzer = FilterAnalyzer(source="BBC-Somali", sampling_rate=0.0)
        analyzer.record_filtered("id1", "T", "text", "min_length_filter")
        assert analyzer.filtered_samples["min_length_filter"] == []


class TestFilterAnalyzerReporting:
    def test_compute_filter_percentages_zero_processed(self):
        analyzer = FilterAnalyzer(source="BBC-Somali")
        assert analyzer.compute_filter_percentages() == {}

    def test_compute_filter_percentages(self):
        analyzer = FilterAnalyzer(source="BBC-Somali")
        for _ in range(10):
            analyzer.record_processed()
        for _ in range(3):
            analyzer.record_filtered("id", "T", "text", "min_length_filter")

        percentages = analyzer.compute_filter_percentages()
        assert percentages["min_length_filter"] == 30.0

    def test_generate_report_structure(self):
        analyzer = FilterAnalyzer(source="BBC-Somali")
        for _ in range(10):
            analyzer.record_processed()
        for _ in range(7):
            analyzer.record_passed()
        for _ in range(3):
            analyzer.record_filtered("id", "T", "text", "min_length_filter", reason="short")

        report = analyzer.generate_report()

        assert report["source"] == "BBC-Somali"
        assert report["summary"]["total_processed"] == 10
        assert report["summary"]["total_passed"] == 7
        assert report["summary"]["total_filtered"] == 3
        assert report["summary"]["pass_rate"] == 0.7
        assert report["summary"]["filter_rate"] == 0.3
        assert "min_length_filter" in report["filter_breakdown"]
        assert report["sampling"]["enabled"] is False

    def test_generate_report_zero_processed_rates(self):
        analyzer = FilterAnalyzer(source="BBC-Somali")
        report = analyzer.generate_report()
        assert report["summary"]["pass_rate"] == 0.0
        assert report["summary"]["filter_rate"] == 0.0


class TestFilterAnalyzerExport:
    def test_export_stratified_dataset_writes_jsonl(self, tmp_path):
        analyzer = FilterAnalyzer(source="BBC-Somali", sampling_rate=1.0)
        analyzer.record_filtered("id1", "Title1", "text1", "min_length_filter")
        analyzer.record_filtered("id2", "Title2", "text2", "langid_filter")

        output_path = tmp_path / "reports" / "samples.jsonl"
        count = analyzer.export_stratified_dataset(output_path)

        assert count == 2
        assert output_path.exists()

        lines = output_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        parsed = [json.loads(line) for line in lines]
        assert {p["filter_name"] for p in parsed} == {"min_length_filter", "langid_filter"}

    def test_export_stratified_dataset_empty_when_no_samples(self, tmp_path):
        analyzer = FilterAnalyzer(source="BBC-Somali")
        output_path = tmp_path / "reports" / "samples.jsonl"
        count = analyzer.export_stratified_dataset(output_path)
        assert count == 0
        assert output_path.exists()

    def test_export_report_writes_json(self, tmp_path):
        analyzer = FilterAnalyzer(source="BBC-Somali")
        analyzer.record_processed()
        analyzer.record_passed()

        output_path = tmp_path / "reports" / "report.json"
        analyzer.export_report(output_path)

        assert output_path.exists()
        with open(output_path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["source"] == "BBC-Somali"

    def test_print_summary_outputs_source_and_counts(self, capsys):
        analyzer = FilterAnalyzer(source="BBC-Somali", sampling_rate=0.5)
        for _ in range(10):
            analyzer.record_processed()
        for _ in range(6):
            analyzer.record_passed()
        analyzer.record_filtered("id1", "T", "text", "min_length_filter", reason="too short")

        analyzer.print_summary()

        captured = capsys.readouterr()
        assert "FILTER ANALYSIS SUMMARY: BBC-Somali" in captured.out
        assert "min_length_filter" in captured.out


class TestCreateFilterAnalyzer:
    def test_sampling_disabled_by_default(self):
        analyzer = create_filter_analyzer(source="BBC-Somali")
        assert analyzer.sampling_rate == 0.0

    def test_sampling_enabled_uses_rate(self):
        analyzer = create_filter_analyzer(
            source="BBC-Somali", enable_sampling=True, sampling_rate=0.05
        )
        assert analyzer.sampling_rate == 0.05


class TestAnalyzeFilterImpact:
    def test_empty_breakdown_returns_zeroed_result(self):
        result = analyze_filter_impact({}, total_records=100)
        assert result == {
            "total_filtered": 0,
            "filter_rate": 0.0,
            "top_filters": [],
            "recommendations": [],
        }

    def test_zero_total_records_returns_zeroed_result(self):
        result = analyze_filter_impact({"min_length_filter": 5}, total_records=0)
        assert result["total_filtered"] == 0

    def test_high_filter_rate_warning(self):
        result = analyze_filter_impact({"min_length_filter": 60}, total_records=100)
        assert result["filter_rate"] == 0.6
        assert any("Over 50%" in r for r in result["recommendations"])

    def test_dominant_filter_warning(self):
        breakdown = {"min_length_filter": 90, "langid_filter": 10}
        result = analyze_filter_impact(breakdown, total_records=200)
        assert any("responsible for >70%" in r for r in result["recommendations"])
        assert result["top_filters"][0] == ("min_length_filter", 90)

    def test_low_filter_rate_warning(self):
        result = analyze_filter_impact({"min_length_filter": 2}, total_records=100)
        assert any("too permissive" in r for r in result["recommendations"])

    def test_normal_filter_rate_no_warnings(self):
        breakdown = {"min_length_filter": 8, "langid_filter": 7, "duplicate_filter": 5}
        result = analyze_filter_impact(breakdown, total_records=100)
        assert result["filter_rate"] == 0.2
        assert result["recommendations"] == []

    def test_top_filters_limited_to_five(self):
        breakdown = {f"filter_{i}": i + 1 for i in range(10)}
        result = analyze_filter_impact(breakdown, total_records=1000)
        assert len(result["top_filters"]) == 5
