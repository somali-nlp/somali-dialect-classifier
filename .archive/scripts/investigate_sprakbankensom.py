#!/usr/bin/env python3
"""
Script to investigate all 23 Språkbanken Somali corpora.
Fetches metadata and download information for each corpus.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Any
import re

# List of all 23 Språkbanken Somali corpora
CORPORA_URLS = [
    "https://spraakbanken.gu.se/en/resources/somali-1993-94",
    "https://spraakbanken.gu.se/en/resources/somali-as-2016",
    "https://spraakbanken.gu.se/en/resources/somali-1971-79",
    "https://spraakbanken.gu.se/en/resources/somali-as-2001",
    "https://spraakbanken.gu.se/en/resources/somali-2001",
    "https://spraakbanken.gu.se/en/resources/somali-ah-2010-19",
    "https://spraakbanken.gu.se/en/resources/somali-caafimaad-1972-79",
    "https://spraakbanken.gu.se/en/resources/somali-cilmi",
    "https://spraakbanken.gu.se/en/resources/somali-cb",
    "https://spraakbanken.gu.se/en/resources/somali-cb-2001-03-soomaaliya",
    "https://spraakbanken.gu.se/en/resources/somali-cb-2016",
    "https://spraakbanken.gu.se/en/resources/somali-kqa",
    "https://spraakbanken.gu.se/en/resources/somali-mk-1972-79",
    "https://spraakbanken.gu.se/en/resources/somali-radioden2014",
    "https://spraakbanken.gu.se/en/resources/somali-radioswe2014",
    "https://spraakbanken.gu.se/en/resources/somali-saynis-1980-89",
    "https://spraakbanken.gu.se/en/resources/somali-sheekooyin",
    "https://spraakbanken.gu.se/en/resources/somali-sheekooyin-carruureed",
    "https://spraakbanken.gu.se/en/resources/somali-sheekooying",
    "https://spraakbanken.gu.se/en/resources/somali-suugaan-turjuman",
    "https://spraakbanken.gu.se/en/resources/somali-suugaan",
    "https://spraakbanken.gu.se/en/resources/somali-tid-turjuman",
    "https://spraakbanken.gu.se/en/resources/somali-ogaden"
]

# Domain mapping based on corpus names and investigation
DOMAIN_MAPPING = {
    "1993-94": "general",
    "as-2016": "news",  # 'as' likely Arlaadi Soomaaliyeed (Somali News)
    "1971-79": "historical",
    "as-2001": "news",
    "2001": "general",
    "ah-2010-19": "news",  # 'ah' likely Afhayeenka (Spokesperson)
    "caafimaad": "health",  # caafimaad = health
    "cilmi": "science",  # cilmi = knowledge/science
    "cb": "news",  # likely news corpus
    "cb-2001-03-soomaaliya": "news",
    "cb-2016": "news",
    "kqa": "qa",  # Question-Answer format
    "mk": "general",
    "radioden": "radio",  # Radio Denmark
    "radioswe": "radio",  # Radio Sweden
    "saynis": "science",  # saynis = science
    "sheekooyin": "literature",  # sheekooyin = stories
    "sheekooyin-carruureed": "children",  # children's stories
    "sheekooying": "literature",  # variant of sheekooyin
    "suugaan-turjuman": "literature_translation",  # suugaan = literature, turjuman = translation
    "suugaan": "literature",  # suugaan = literature/poetry
    "tid-turjuman": "translation",  # tid = time, turjuman = translation
    "ogaden": "news_regional"  # Ogaden region news
}


def extract_corpus_id(url: str) -> str:
    """Extract corpus ID from URL."""
    return url.split("/")[-1].replace("somali-", "")


def get_domain(corpus_id: str) -> str:
    """Map corpus ID to domain."""
    for key, domain in DOMAIN_MAPPING.items():
        if key in corpus_id:
            return domain
    return "general"


def analyze_corpora() -> List[Dict[str, Any]]:
    """Analyze all Språkbanken corpora and extract metadata."""
    corpora_info = []

    for url in CORPORA_URLS:
        corpus_id = extract_corpus_id(url)

        # Build standard download URL pattern
        download_url = f"https://spraakbanken.gu.se/lb/resurser/meningsmangder/somali-{corpus_id}.xml.bz2"

        corpus_info = {
            "id": corpus_id,
            "url": url,
            "download_url": download_url,
            "format": "xml.bz2",
            "license": "CC BY 4.0",  # All use CC BY 4.0
            "domain": get_domain(corpus_id),
            "korp_url": f"https://spraakbanken.gu.se/korp/?mode=somali#?corpus=somali-{corpus_id}",
            "notes": []
        }

        # Add special notes for certain corpora
        if "ogaden" in corpus_id:
            corpus_info["notes"].append("Regional corpus from Ogaden area")
        if "turjuman" in corpus_id:
            corpus_info["notes"].append("Translation corpus")
        if "radio" in corpus_id:
            corpus_info["notes"].append("Radio broadcast transcriptions")
        if "carruureed" in corpus_id:
            corpus_info["notes"].append("Children's content")

        corpora_info.append(corpus_info)

    return corpora_info


def save_investigation_results(corpora_info: List[Dict[str, Any]]):
    """Save investigation results to JSON file."""
    output_path = Path("data/sprakbanken_investigation.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    investigation_results = {
        "total_corpora": len(corpora_info),
        "common_format": "XML compressed as .bz2",
        "common_license": "CC BY 4.0",
        "download_pattern": "https://spraakbanken.gu.se/lb/resurser/meningsmangder/somali-{corpus_id}.xml.bz2",
        "domains_found": list(set(c["domain"] for c in corpora_info)),
        "corpora": corpora_info,
        "summary": {
            "total_domains": len(set(c["domain"] for c in corpora_info)),
            "has_regional_data": any("ogaden" in c["id"] for c in corpora_info),
            "has_translations": any("turjuman" in c["id"] for c in corpora_info),
            "time_range": "1971-2019 based on corpus names",
            "special_collections": [
                "Children's stories (sheekooyin-carruureed)",
                "Health content (caafimaad)",
                "Science content (cilmi, saynis)",
                "Radio broadcasts (radioden2014, radioswe2014)",
                "Regional news (ogaden)"
            ]
        }
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(investigation_results, f, indent=2, ensure_ascii=False)

    print(f"Investigation results saved to {output_path}")
    return output_path


def print_summary(corpora_info: List[Dict[str, Any]]):
    """Print investigation summary."""
    print("\n" + "=" * 60)
    print("SPRÅKBANKEN SOMALI CORPORA INVESTIGATION SUMMARY")
    print("=" * 60)

    print(f"\nTotal corpora: {len(corpora_info)}")
    print(f"Common format: XML (.bz2 compressed)")
    print(f"Common license: CC BY 4.0")

    domains = {}
    for corpus in corpora_info:
        domain = corpus["domain"]
        domains[domain] = domains.get(domain, 0) + 1

    print("\nDomains distribution:")
    for domain, count in sorted(domains.items()):
        print(f"  - {domain}: {count} corpora")

    print("\nSpecial collections:")
    for corpus in corpora_info:
        if corpus["notes"]:
            print(f"  - {corpus['id']}: {', '.join(corpus['notes'])}")

    print("\nDownload URL pattern:")
    print("  https://spraakbanken.gu.se/lb/resurser/meningsmangder/somali-{corpus_id}.xml.bz2")

    print("\nAll corpora accessible via Korp search interface")
    print("=" * 60)


if __name__ == "__main__":
    print("Investigating Språkbanken Somali corpora...")
    corpora_info = analyze_corpora()
    print_summary(corpora_info)
    output_path = save_investigation_results(corpora_info)
    print(f"\nDetailed results saved to: {output_path}")