"""
Tests for campaign-scale configuration and cost guards.

Covers:
- RunConfig and CampaignConfig: defaults and env overrides
- TikTokScrapingConfig.max_budget_usd: default and env override
- ApifyTikTokClient budget guard (BudgetExceededError)
- Budget guard composes with idempotency guard (no double-spend on retries)
- SprakbankenSomaliProcessor corpus-selection: "all" sentinel and list
- HuggingFace max_records=None unbounded support (config default)
"""

from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from somdialc.infra.config import (
    CampaignConfig,
    RunConfig,
    TikTokScrapingConfig,
    get_config,
    reset_config,
)
from somdialc.ingestion.apify_tiktok_client import ApifyTikTokClient, BudgetExceededError

# ---------------------------------------------------------------------------
# RunConfig
# ---------------------------------------------------------------------------


class TestRunConfig:
    """RunConfig defaults and environment overrides."""

    def test_default_purpose_is_production(self, monkeypatch):
        # The conftest autouse fixture sets SDC_RUN__PURPOSE=test for the test session.
        # Remove it to verify the field-level default is "production".
        monkeypatch.delenv("SDC_RUN__PURPOSE", raising=False)
        reset_config()
        cfg = RunConfig()
        assert cfg.purpose == "production"

    def test_env_override_validation(self, monkeypatch):
        monkeypatch.setenv("SDC_RUN__PURPOSE", "validation")
        reset_config()
        cfg = RunConfig()
        assert cfg.purpose == "validation"

    def test_env_override_test(self, monkeypatch):
        monkeypatch.setenv("SDC_RUN__PURPOSE", "test")
        reset_config()
        cfg = RunConfig()
        assert cfg.purpose == "test"

    def test_invalid_purpose_raises(self, monkeypatch):
        monkeypatch.setenv("SDC_RUN__PURPOSE", "staging")
        reset_config()
        with pytest.raises(ValueError):
            RunConfig()

    def test_accessible_via_get_config(self, monkeypatch):
        monkeypatch.setenv("SDC_RUN__PURPOSE", "validation")
        reset_config()
        config = get_config()
        assert config.run.purpose == "validation"

    def teardown_method(self):
        reset_config()


# ---------------------------------------------------------------------------
# CampaignConfig
# ---------------------------------------------------------------------------


class TestCampaignConfig:
    """CampaignConfig defaults and environment overrides."""

    def test_default_id(self):
        reset_config()
        cfg = CampaignConfig()
        assert cfg.id == "campaign_init_001"

    def test_default_duration_days(self):
        reset_config()
        cfg = CampaignConfig()
        assert cfg.duration_days == 6

    def test_env_override_id(self, monkeypatch):
        monkeypatch.setenv("SDC_CAMPAIGN__ID", "campaign_aymay_001")
        reset_config()
        cfg = CampaignConfig()
        assert cfg.id == "campaign_aymay_001"

    def test_env_override_duration_days(self, monkeypatch):
        monkeypatch.setenv("SDC_CAMPAIGN__DURATION_DAYS", "14")
        reset_config()
        cfg = CampaignConfig()
        assert cfg.duration_days == 14

    def test_accessible_via_get_config(self, monkeypatch):
        monkeypatch.setenv("SDC_CAMPAIGN__ID", "test_campaign")
        monkeypatch.setenv("SDC_CAMPAIGN__DURATION_DAYS", "3")
        reset_config()
        config = get_config()
        assert config.campaign.id == "test_campaign"
        assert config.campaign.duration_days == 3

    def test_duration_days_lower_bound(self, monkeypatch):
        monkeypatch.setenv("SDC_CAMPAIGN__DURATION_DAYS", "0")
        reset_config()
        with pytest.raises(ValueError):
            CampaignConfig()

    def teardown_method(self):
        reset_config()


# ---------------------------------------------------------------------------
# TikTokScrapingConfig cost guard field
# ---------------------------------------------------------------------------


class TestTikTokScrapingConfigBudget:
    """max_budget_usd field on TikTokScrapingConfig."""

    def test_default_max_budget_usd(self):
        reset_config()
        cfg = TikTokScrapingConfig()
        assert cfg.max_budget_usd == 20.0

    def test_env_override_max_budget_usd(self, monkeypatch):
        monkeypatch.setenv("SDC_SCRAPING__TIKTOK__MAX_BUDGET_USD", "50.0")
        reset_config()
        cfg = TikTokScrapingConfig()
        assert cfg.max_budget_usd == 50.0

    def test_max_budget_usd_none_when_env_unset(self, monkeypatch):
        # When the env var is absent, the field default (20.0) applies.
        # To exercise the None path, instantiate the model directly with None.
        monkeypatch.delenv("SDC_SCRAPING__TIKTOK__MAX_BUDGET_USD", raising=False)
        reset_config()
        cfg = TikTokScrapingConfig(max_budget_usd=None)
        assert cfg.max_budget_usd is None

    def test_accessible_via_get_config(self, monkeypatch):
        monkeypatch.setenv("SDC_SCRAPING__TIKTOK__MAX_BUDGET_USD", "30.0")
        reset_config()
        config = get_config()
        assert config.scraping.tiktok.max_budget_usd == 30.0

    def teardown_method(self):
        reset_config()


# ---------------------------------------------------------------------------
# ApifyTikTokClient budget guard
# ---------------------------------------------------------------------------


class TestApifyBudgetGuard:
    """BudgetExceededError is raised before any POST when cap is exceeded."""

    def _make_client(self, max_budget_usd: Optional[float] = 20.0) -> ApifyTikTokClient:
        return ApifyTikTokClient(
            api_token="fake-token-000",
            max_budget_usd=max_budget_usd,
        )

    def test_budget_exceeded_raises_before_post(self):
        """With 100 videos × 300 comments = 30,000 raw → $30 > $20 cap."""
        client = self._make_client(max_budget_usd=20.0)
        video_urls = [f"https://www.tiktok.com/@user/video/{i}" for i in range(100)]

        with pytest.raises(BudgetExceededError) as exc_info:
            client._check_budget(video_urls, max_comments=300)

        err = exc_info.value
        assert err.budget_usd == 20.0
        assert err.projected_comments == 30_000
        assert err.projected_cost_usd == pytest.approx(30.0)

    def test_budget_within_cap_passes(self):
        """5 videos × 300 comments = 1,500 raw → $1.50 < $20 cap."""
        client = self._make_client(max_budget_usd=20.0)
        video_urls = [f"https://www.tiktok.com/@user/video/{i}" for i in range(5)]
        # Should not raise
        client._check_budget(video_urls, max_comments=300)

    def test_no_cap_configured_passes_any_size(self):
        """When max_budget_usd is None the guard is a no-op."""
        client = self._make_client(max_budget_usd=None)
        video_urls = [f"https://www.tiktok.com/@user/video/{i}" for i in range(1000)]
        # Should not raise regardless of video count
        client._check_budget(video_urls, max_comments=10_000)

    def test_uncapped_comments_uses_500_fallback(self):
        """When max_comments=None the guard projects 500 comments/video."""
        client = self._make_client(max_budget_usd=10.0)
        # 25 videos × 500 fallback = 12,500 comments = $12.50 > $10
        video_urls = [f"https://www.tiktok.com/@user/video/{i}" for i in range(25)]

        with pytest.raises(BudgetExceededError) as exc_info:
            client._check_budget(video_urls, max_comments=None)

        assert exc_info.value.projected_comments == 25 * 500

    def test_budget_guard_fires_before_post(self):
        """start_actor_run must raise BudgetExceededError without making any HTTP call."""
        client = self._make_client(max_budget_usd=1.0)
        # 10 videos × 300 comments = 3,000 raw = $3 > $1
        video_urls = [f"https://www.tiktok.com/@user/video/{i}" for i in range(10)]

        with patch.object(client, "session") as mock_session:
            with pytest.raises(BudgetExceededError):
                client.start_actor_run(video_urls, max_comments=300)

            # The POST must never have been called.
            mock_session.post.assert_not_called()

    def test_budget_guard_no_double_spend_on_retry_path(self):
        """Budget guard fires before the retry loop — if it raises, no run_id is created
        so the CQ-6 retry loop can never issue a second POST for the same over-budget run."""
        client = self._make_client(max_budget_usd=1.0)
        video_urls = ["https://www.tiktok.com/@user/video/1"] * 10

        post_call_count = 0

        def fake_post(*args, **kwargs):
            nonlocal post_call_count
            post_call_count += 1
            raise AssertionError("POST should never be called when budget is exceeded")

        client.session.post = fake_post  # type: ignore[assignment]

        with pytest.raises(BudgetExceededError):
            client.start_actor_run(video_urls, max_comments=300)

        assert post_call_count == 0, "No POST should have been issued"

    def test_budget_error_message_contains_guidance(self):
        """BudgetExceededError message must mention the config override."""
        client = self._make_client(max_budget_usd=5.0)
        video_urls = [f"https://www.tiktok.com/@user/video/{i}" for i in range(50)]

        with pytest.raises(BudgetExceededError) as exc_info:
            client._check_budget(video_urls, max_comments=200)

        assert "SDC_SCRAPING__TIKTOK__MAX_BUDGET_USD" in str(exc_info.value)


# ---------------------------------------------------------------------------
# SprakbankenSomaliProcessor corpus-selection seam
# ---------------------------------------------------------------------------


class TestSprakbankenCorpusSelection:
    """Corpus-selection logic: 'all' sentinel and comma-separated list."""

    def test_all_sentinel_loads_all_corpora(self):
        """corpus_id='all' must load all 66 corpora from CORPUS_INFO."""
        from somdialc.ingestion.processors.sprakbanken_somali_processor import (
            CORPUS_INFO,
            SprakbankenSomaliProcessor,
        )

        mock_ledger = MagicMock()
        processor = SprakbankenSomaliProcessor(
            corpus_id="all",
            ledger=mock_ledger,
        )
        assert processor.corpora_to_process == list(CORPUS_INFO.keys())
        assert len(processor.corpora_to_process) == len(CORPUS_INFO)

    def test_single_corpus_id(self):
        """A single corpus_id is stored as a one-element list."""
        from somdialc.ingestion.processors.sprakbanken_somali_processor import (
            SprakbankenSomaliProcessor,
        )

        mock_ledger = MagicMock()
        processor = SprakbankenSomaliProcessor(
            corpus_id="somali-cilmi",
            ledger=mock_ledger,
        )
        assert processor.corpora_to_process == ["somali-cilmi"]

    def test_comma_separated_corpus_list(self):
        """Comma-separated corpus IDs are split and validated."""
        from somdialc.ingestion.processors.sprakbanken_somali_processor import (
            SprakbankenSomaliProcessor,
        )

        mock_ledger = MagicMock()
        processor = SprakbankenSomaliProcessor(
            corpus_id="somali-cilmi,somali-bbc",
            ledger=mock_ledger,
        )
        assert processor.corpora_to_process == ["somali-cilmi", "somali-bbc"]

    def test_invalid_corpus_id_raises(self):
        """An unrecognised corpus_id must raise ValueError at construction time."""
        from somdialc.ingestion.processors.sprakbanken_somali_processor import (
            SprakbankenSomaliProcessor,
        )

        mock_ledger = MagicMock()
        with pytest.raises(ValueError, match="Unknown corpus_id"):
            SprakbankenSomaliProcessor(
                corpus_id="somali-nonexistent-corpus-xyz",
                ledger=mock_ledger,
            )

    def test_corpus_info_has_66_entries(self):
        """CORPUS_INFO must contain exactly 66 entries (audit finding)."""
        from somdialc.ingestion.processors.sprakbanken_somali_processor import CORPUS_INFO

        assert len(CORPUS_INFO) == 66, (
            f"Expected 66 corpora in CORPUS_INFO, found {len(CORPUS_INFO)}. "
            "Update this count if new corpora are added."
        )


# ---------------------------------------------------------------------------
# HuggingFace max_records=None — config default is unbounded
# ---------------------------------------------------------------------------


class TestHuggingFaceUnboundedConfig:
    """HuggingFaceScrapingConfig.max_records defaults to None (unbounded streaming)."""

    def test_default_max_records_is_none(self):
        """max_records=None is the default — no artificial cap at construction."""
        from somdialc.infra.config import HuggingFaceScrapingConfig

        reset_config()
        cfg = HuggingFaceScrapingConfig()
        assert cfg.max_records is None

    def test_env_override_max_records(self, monkeypatch):
        """Operator can cap max_records via env without modifying code."""
        from somdialc.infra.config import HuggingFaceScrapingConfig

        monkeypatch.setenv("SDC_SCRAPING__HUGGINGFACE__MAX_RECORDS", "150000")
        reset_config()
        cfg = HuggingFaceScrapingConfig()
        assert cfg.max_records == 150_000

    def test_max_records_none_when_passed_directly(self, monkeypatch):
        """max_records=None can be set via constructor (unbounded streaming)."""
        from somdialc.infra.config import HuggingFaceScrapingConfig

        monkeypatch.delenv("SDC_SCRAPING__HUGGINGFACE__MAX_RECORDS", raising=False)
        reset_config()
        cfg = HuggingFaceScrapingConfig(max_records=None)
        assert cfg.max_records is None

    def teardown_method(self):
        reset_config()


# ---------------------------------------------------------------------------
# BBC quota default
# ---------------------------------------------------------------------------


class TestBBCQuotaDefault:
    """BBC daily quota is 350 in OrchestrationConfig.quota_limits."""

    def test_bbc_quota_is_350(self):
        reset_config()
        config = get_config()
        assert config.orchestration.get_quota("bbc") == 350

    def teardown_method(self):
        reset_config()
