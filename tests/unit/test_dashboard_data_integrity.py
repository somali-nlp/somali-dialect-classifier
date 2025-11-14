"""Dashboard data integrity tests.

Ensures the exported datasets that power the GitHub Pages dashboard remain
populated. These checks prevent regressions where placeholder datasets or empty
lists produce broken visualisations in production.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

DATA_DIR = Path(__file__).resolve().parents[2] / "_site" / "data"


def load_json(filename: str) -> dict:
    with (DATA_DIR / filename).open(encoding="utf-8") as handle:
        return json.load(handle)


def test_sankey_flow_has_stage_counts():
    data = load_json("sankey_flow.json")

    stage_counts = data.get("stage_counts", {})
    assert stage_counts, "Expected stage_counts to be populated for Sankey flow"

    discovered = stage_counts.get("discovered", 0)
    written = stage_counts.get("written", stage_counts.get("Silver Dataset", 0))

    assert discovered > 0, "Sankey flow should report discovered records"
    assert written > 0, "Sankey flow should report written records"
    assert discovered >= written, "Discovered volume should not be less than written output"


def test_text_distributions_are_non_empty():
    data = load_json("text_distributions.json")

    sources = data.get("sources", [])
    distributions = data.get("distributions", {})

    assert sources, "Text distribution sources must be defined"
    assert distributions, "Text distribution payload must include per-source data"

    for source in sources:
        dist = distributions.get(source)
        assert dist, f"Missing distribution for source {source}"

        counts = dist.get("counts", [])
        assert any(count > 0 for count in counts), f"Expected non-zero length counts for {source}"


@pytest.mark.skip(
    reason="Dashboard metadata not generated in test environment - requires full pipeline run"
)
def test_dashboard_metadata_exposes_visualisation_flags():
    data = load_json("dashboard_metadata.json")

    visualisations = data.get("visualizations") or data.get("visualisations")
    assert visualisations, "Dashboard metadata should expose visualization availability"

    available_flags = [
        key for key, value in visualisations.items() if key.endswith("_available") and value is True
    ]
    assert available_flags, "At least one dashboard visualisation must be marked available"
