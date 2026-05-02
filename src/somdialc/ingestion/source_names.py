"""
Canonical source name constants for the Somali Dialect Classifier pipeline.

Convention: lowercase-hyphen-suffix ``<source>-somali`` is the single
authoritative form used in silver ``source`` column, ledger writes, and
MetricsCollector arguments.  Do not invent other forms.
"""

CANONICAL_SOURCES: dict[str, str] = {
    "wikipedia": "wikipedia-somali",
    "bbc": "bbc-somali",
    "sprakbanken": "sprakbanken-somali",
    "tiktok": "tiktok-somali",
    "huggingface": "huggingface-somali",
}
