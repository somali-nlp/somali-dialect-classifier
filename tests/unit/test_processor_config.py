"""Unit tests for somdialc.ingestion.processor_config.

Covers get_processor_kwargs() and get_processor_source_name(): pure mapping
functions used by ProcessorRegistry to construct processors by name.
"""

import pytest

from somdialc.ingestion.processor_config import (
    get_processor_kwargs,
    get_processor_source_name,
)


class TestGetProcessorKwargs:
    def test_wikipedia_returns_base_kwargs_only(self):
        kwargs = get_processor_kwargs("wikipedia", force=True, run_seed="seed-1")
        assert kwargs == {"force": True, "run_seed": "seed-1"}

    def test_bbc_includes_max_articles_when_present(self):
        kwargs = get_processor_kwargs("bbc", max_articles=100)
        assert kwargs["max_articles"] == 100
        assert kwargs["force"] is False
        assert kwargs["run_seed"] is None

    def test_bbc_omits_max_articles_when_absent(self):
        kwargs = get_processor_kwargs("bbc")
        assert "max_articles" not in kwargs

    def test_huggingface_defaults(self):
        kwargs = get_processor_kwargs("huggingface")
        assert kwargs["dataset_name"] == "allenai/c4"
        assert kwargs["dataset_config"] == "so"
        assert kwargs["url_field"] == "url"
        assert kwargs["max_records"] is None

    def test_huggingface_overrides(self):
        kwargs = get_processor_kwargs(
            "huggingface",
            dataset_name="allenai/mc4",
            dataset_config="som",
            url_field="link",
            max_records=5000,
        )
        assert kwargs["dataset_name"] == "allenai/mc4"
        assert kwargs["dataset_config"] == "som"
        assert kwargs["url_field"] == "link"
        assert kwargs["max_records"] == 5000

    def test_sprakbanken_includes_corpus_id_when_present(self):
        kwargs = get_processor_kwargs("sprakbanken", corpus_id="somali-cilmi")
        assert kwargs["corpus_id"] == "somali-cilmi"

    def test_sprakbanken_omits_corpus_id_when_absent(self):
        kwargs = get_processor_kwargs("sprakbanken")
        assert "corpus_id" not in kwargs

    def test_tiktok_includes_credentials_and_urls(self):
        kwargs = get_processor_kwargs(
            "tiktok",
            apify_api_token="tok",
            apify_user_id="user",
            video_urls=["https://tiktok.com/@u/video/1"],
        )
        assert kwargs["apify_api_token"] == "tok"
        assert kwargs["apify_user_id"] == "user"
        assert kwargs["video_urls"] == ["https://tiktok.com/@u/video/1"]

    def test_tiktok_defaults_to_none(self):
        kwargs = get_processor_kwargs("tiktok")
        assert kwargs["apify_api_token"] is None
        assert kwargs["apify_user_id"] is None
        assert kwargs["video_urls"] is None

    def test_ledger_passed_through_when_present(self):
        sentinel_ledger = object()
        kwargs = get_processor_kwargs("wikipedia", ledger=sentinel_ledger)
        assert kwargs["ledger"] is sentinel_ledger

    def test_ledger_absent_when_not_passed(self):
        kwargs = get_processor_kwargs("wikipedia")
        assert "ledger" not in kwargs

    def test_unknown_processor_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown processor"):
            get_processor_kwargs("not-a-real-processor")


class TestGetProcessorSourceName:
    @pytest.mark.parametrize(
        "processor_name,expected",
        [
            ("wikipedia", "wikipedia-somali"),
            ("bbc", "bbc-somali"),
            ("sprakbanken", "Sprakbanken-Somali-all"),
            ("tiktok", "tiktok-somali"),
        ],
    )
    def test_static_source_names(self, processor_name, expected):
        assert get_processor_source_name(processor_name) == expected

    def test_huggingface_default_dataset(self):
        assert get_processor_source_name("huggingface") == "HuggingFace-Somali_c4"

    def test_huggingface_custom_dataset_uses_slug(self):
        name = get_processor_source_name("huggingface", dataset_name="allenai/mc4")
        assert name == "HuggingFace-Somali_mc4"

    def test_sprakbanken_custom_corpus_id(self):
        name = get_processor_source_name("sprakbanken", corpus_id="somali-cilmi")
        assert name == "Sprakbanken-Somali-somali-cilmi"

    def test_unknown_processor_falls_back_to_capitalized_name(self):
        assert get_processor_source_name("mystery") == "Mystery"
