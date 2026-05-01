"""Discovery helpers for the BBC Somali processor."""

import json
import random
import time
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

from ....infra.logging_utils import set_context
from ....infra.metrics import MetricsCollector, PipelineType

_REQUEST_TIMEOUT = 30


def download(processor) -> Path:
    """Discover and persist BBC article links."""
    processor.raw_dir.mkdir(parents=True, exist_ok=True)
    set_context(run_id=processor.run_id, source="bbc-somali", phase="discovery")
    processor.metrics = MetricsCollector(
        processor.run_id, "BBC-Somali", pipeline_type=PipelineType.WEB_SCRAPING
    )

    if processor.article_links_file.exists() and not processor.force:
        with open(processor.article_links_file, encoding="utf-8") as handle:
            cached_data = json.load(handle)
        cached_max_articles = cached_data.get("max_articles_limit")
        if cached_max_articles == processor.max_articles:
            processor.logger.info(
                f"Article links already exist with matching parameters: {processor.article_links_file}"
            )
            return processor.article_links_file
        processor.logger.info(
            f"Parameter mismatch: cached max_articles={cached_max_articles}, "
            f"current max_articles={processor.max_articles}. Re-discovering articles..."
        )

    processor._check_robots_txt()
    rss_links = processor._scrape_rss_feeds()
    processor.logger.info(f"RSS feeds discovered: {len(rss_links)} articles")

    if len(rss_links) < 50:
        processor.logger.info("RSS yielded few results, falling back to web scraping...")
        web_links = processor._get_article_links()
        article_links = list(set(rss_links + web_links))
        processor.logger.info(f"Combined discovery: {len(article_links)} total articles")
    else:
        article_links = rss_links

    for url in article_links:
        processor.ledger.discover_url(
            url, "bbc", metadata={"discovered_at": processor.date_accessed}
        )
        processor.metrics.increment("urls_discovered")

    links_to_scrape = (
        article_links[: processor.max_articles] if processor.max_articles else article_links
    )

    with open(processor.article_links_file, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "links": links_to_scrape,
                "total_discovered": len(article_links),
                "total_to_scrape": len(links_to_scrape),
                "discovered_at": processor.date_accessed,
                "max_articles_limit": processor.max_articles,
                "run_id": processor.run_id,
            },
            handle,
            ensure_ascii=False,
            indent=2,
        )

    if processor.max_articles and len(article_links) > processor.max_articles:
        processor.logger.info(
            f"Limiting scrape to {processor.max_articles} of {len(article_links)} discovered articles"
        )

    processor.logger.info(
        f"Saved {len(links_to_scrape)} article links -> {processor.article_links_file}"
    )
    processor._export_stage_metrics("discovery")
    return processor.article_links_file


def discover_topic_sections(processor, soup: BeautifulSoup) -> list[tuple[str, str]]:
    """Dynamically discover unique topic section URLs from the homepage."""
    seen_urls = set()
    sections = []

    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "/somali/topics/" in href:
            full_url = f"https://www.bbc.com{href}" if href.startswith("/") else href
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)
            sections.append((full_url, link.get_text(strip=True)))

    return sections


def extract_article_links_from_soup(processor, soup: BeautifulSoup) -> set[str]:
    """Extract valid BBC Somali article URLs from parsed HTML."""
    from ....infra.security import validate_url_for_source

    bbc_allowed_domains = {"bbc.com", "bbc.co.uk"}
    links = set()
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "/somali/" in href and "/articles/" in href:
            full_url = f"https://www.bbc.com{href}" if href.startswith("/") else href
            is_valid, _ = validate_url_for_source(full_url, "bbc", bbc_allowed_domains)
            if is_valid:
                links.add(full_url)
            else:
                processor.logger.debug(f"  REJECTED: {full_url}")
                processor.metrics.increment("urls_rejected_security")
    return links


def scrape_homepage(
    processor, session: requests.Session
) -> tuple[set[str], Optional[BeautifulSoup]]:
    """Scrape BBC Somali homepage for article links."""
    article_links: set[str] = set()
    processor.logger.info("Scraping homepage...")

    try:
        response = session.get(processor.base_url, headers=processor.headers, timeout=_REQUEST_TIMEOUT)
        response.raise_for_status()

        homepage_soup = BeautifulSoup(response.content, "html.parser")
        article_links = processor._extract_article_links_from_soup(homepage_soup)
        processor.logger.info(f"  ✓ Homepage: {len(article_links)} articles")
        time.sleep(random.uniform(1, 2))
        return article_links, homepage_soup
    except (requests.RequestException, ValueError) as err:
        processor.logger.error(f"  ✗ Homepage failed: {err}")
        return article_links, None


def scrape_topic_sections(
    processor, session: requests.Session, homepage_soup: BeautifulSoup
) -> set[str]:
    """Scrape topic sections discovered from the homepage."""
    article_links: set[str] = set()
    topic_sections = processor._discover_topic_sections(homepage_soup)

    if not topic_sections:
        return article_links

    processor.logger.info(f"Scraping {len(topic_sections)} topic sections...")

    for section_url, section_name in topic_sections:
        try:
            response = session.get(section_url, headers=processor.headers, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            before_count = len(article_links)
            section_links = processor._extract_article_links_from_soup(soup)
            article_links.update(section_links)

            added = len(article_links) - before_count
            processor.logger.info(f"  ✓ {section_name}: +{added} articles")
            time.sleep(random.uniform(1, 2))
        except (requests.RequestException, ValueError) as err:
            processor.logger.warning(f"  ✗ {section_name}: {err}")

    return article_links
