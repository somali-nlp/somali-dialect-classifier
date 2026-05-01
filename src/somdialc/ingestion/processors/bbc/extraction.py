"""Extraction helpers for the BBC Somali processor."""

import asyncio
import json
from datetime import datetime, timezone
from http.client import RemoteDisconnected
from pathlib import Path
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from urllib3.exceptions import ProtocolError

from ....infra.logging_utils import set_context
from ....infra.metrics import MetricsCollector, PipelineType, QualityReporter
from ....infra.rate_limiter import TimedRequest
from ....ingestion.pipeline_setup import PipelineSetup

try:
    import aiohttp
except ImportError:
    aiohttp = None

_REQUEST_TIMEOUT = 30


def _extract_paragraphs_from_soup(soup: BeautifulSoup) -> str:
    """Extract paragraph text from BBC article HTML using fallback selectors."""
    main_content = soup.find("main") or soup.find(role="main")
    if main_content:
        paragraphs = main_content.find_all("p")
    else:
        article_tag = soup.find("article")
        if article_tag:
            paragraphs = article_tag.find_all("p")
        else:
            article_body = soup.find(attrs={"data-component": "text-block"})
            if article_body:
                paragraphs = article_body.find_all("p")
            else:
                paragraphs = soup.find_all("p")
    return "\n".join([p.text.strip() for p in paragraphs if p.text.strip()])


def compute_text_hash(processor, text: str, url: str) -> str:
    """Compute text hash via the processor's dedup hasher."""
    return processor.dedup.hasher.compute_hash(text=text, url=url)


async def fetch_article_async(
    processor, session: "aiohttp.ClientSession", url: str, semaphore: asyncio.Semaphore
) -> dict[str, Any]:
    """Fetch a single article asynchronously."""
    async with semaphore:
        try:
            conditional_headers = processor.ledger.get_conditional_headers(url)
            headers = {**processor.headers, **conditional_headers}

            async with session.get(url, headers=headers, timeout=_REQUEST_TIMEOUT) as response:
                if response.status == 304:
                    processor.logger.info(f"Article not modified: {url}")
                    processor.metrics.increment("urls_not_modified")
                    return {"url": url, "status": 304, "not_modified": True}

                response.raise_for_status()
                return {
                    "url": url,
                    "html": await response.text(),
                    "status": response.status,
                    "etag": response.headers.get("ETag"),
                    "last_modified": response.headers.get("Last-Modified"),
                }
        except asyncio.TimeoutError:
            processor.logger.warning(f"Timeout fetching {url}")
            return {"url": url, "error": "timeout", "status": None}
        except aiohttp.ClientError as err:
            error_msg = str(err)
            processor.logger.warning(f"Client error fetching {url}: {error_msg}")
            return {"url": url, "error": error_msg, "status": getattr(err, "status", None)}
        except Exception as err:
            processor.logger.error(f"Unexpected error fetching {url}: {err}")
            return {"url": url, "error": str(err), "status": None}


async def fetch_all_articles_async(
    processor, urls: list[str], max_concurrent: int = 10
) -> list[dict]:
    """Fetch multiple articles concurrently."""
    semaphore = asyncio.Semaphore(max_concurrent)
    timeout = aiohttp.ClientTimeout(total=60, connect=10, sock_read=30)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = [fetch_article_async(processor, session, url, semaphore) for url in urls]
        results = []
        for coro in tqdm(
            asyncio.as_completed(tasks),
            total=len(tasks),
            desc="Fetching articles (async)",
            unit="article",
        ):
            results.append(await coro)
        return results


def parse_article_from_html(processor, html: str, url: str) -> Optional[dict]:
    """Parse article content and metadata from BBC HTML."""
    try:
        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.find("h1")
        title = title_tag.text.strip() if title_tag else "No title"

        text = _extract_paragraphs_from_soup(soup)

        if not text:
            processor.logger.warning(
                f"Empty text extracted from {url} - BBC may have changed their HTML structure"
            )

        date_tag = soup.find("time")
        date_published = (
            date_tag["datetime"] if date_tag and date_tag.has_attr("datetime") else None
        )

        return {
            "url": url,
            "title": title,
            "text": text,
            "date": date_published,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "category": "news",
        }
    except Exception as err:
        processor.logger.error(f"Error parsing article {url}: {err}")
        return None


def extract_async(processor) -> Path:
    """Scrape articles using async HTTP."""
    if not processor.article_links_file.exists():
        raise FileNotFoundError(f"Article links not found: {processor.article_links_file}")

    processor.staging_dir.mkdir(parents=True, exist_ok=True)
    if processor.staging_file.exists() and not processor.force:
        processor.logger.info(f"Staging file already exists: {processor.staging_file}")
        processor.logger.info("Use force=True to re-scrape")
        return processor.staging_file
    if processor.staging_file.exists() and processor.force:
        processor.logger.info(f"Force re-scraping: removing existing file {processor.staging_file}")
        processor.staging_file.unlink()

    with open(processor.article_links_file, encoding="utf-8") as handle:
        data = json.load(handle)
        links = data["links"]

    quota_limit = processor.config.orchestration.get_quota("bbc")
    has_quota, remaining = processor.ledger.check_quota_available("bbc", quota_limit)
    if not has_quota:
        processor.logger.warning(f"Daily quota already reached for BBC: {quota_limit} articles")
        if processor.metrics is None:
            processor.metrics = MetricsCollector(
                processor.run_id, "BBC-Somali", pipeline_type=PipelineType.WEB_SCRAPING
            )
        processor.metrics.increment("quota_hit")
        return processor.staging_file

    if quota_limit is not None and remaining < len(links):
        processor.logger.info(
            f"Quota enforcement: processing {remaining} of {len(links)} links "
            f"(quota: {quota_limit} articles/day)"
        )
        links = links[:remaining]
    else:
        processor.logger.info(
            f"Processing {len(links)} links (quota: {quota_limit or 'unlimited'})"
        )

    set_context(run_id=processor.run_id, source="bbc-somali", phase="fetch")
    if processor.metrics is None:
        processor.metrics = MetricsCollector(
            processor.run_id, "BBC-Somali", pipeline_type=PipelineType.WEB_SCRAPING
        )

    processor.logger.info("=" * 60)
    processor.logger.info("PHASE 2: Article Extraction (Async)")
    processor.logger.info("=" * 60)

    urls_to_fetch = []
    for url in links:
        if processor.ledger.should_fetch_url(url, force=processor.force):
            urls_to_fetch.append(url)
        else:
            processor.metrics.increment("urls_skipped")

    processor.logger.info(f"Fetching {len(urls_to_fetch)} articles (async)...")
    fetch_results = asyncio.run(fetch_all_articles_async(processor, urls_to_fetch))

    articles_count = 0
    failed_count = 0

    with open(processor.staging_file, "w", encoding="utf-8") as staging_out:
        for index, result in enumerate(fetch_results, 1):
            url = result["url"]
            if result.get("not_modified"):
                continue
            if "error" in result:
                processor.ledger.mark_failed(url, result["error"])
                processor.metrics.increment("urls_failed")
                processor.metrics.record_error(result["error"])
                failed_count += 1
                continue

            html = result.get("html")
            if not html:
                processor.ledger.mark_failed(url, "Empty HTML")
                processor.metrics.increment("urls_failed")
                failed_count += 1
                continue

            article = parse_article_from_html(processor, html, url)
            if not article or not article.get("text"):
                processor.ledger.mark_failed(url, "Failed to parse or empty text")
                processor.metrics.increment("urls_failed")
                failed_count += 1
                continue

            is_dup, dup_type, similar_url, text_hash, minhash_sig = (
                processor.dedup.process_document(article["text"], url)
            )
            if is_dup:
                processor.logger.info(
                    f"{dup_type.capitalize()} duplicate detected: {url} (similar to {similar_url})"
                )
                processor.ledger.mark_duplicate(url, similar_url)
                if dup_type == "exact":
                    processor.metrics.increment("urls_deduplicated")
                elif dup_type == "near":
                    processor.metrics.increment("near_duplicates")
                continue

            article["text_hash"] = text_hash
            article["minhash_signature"] = minhash_sig
            processor.ledger.mark_fetched(
                url=url,
                http_status=result["status"],
                etag=result.get("etag"),
                last_modified=result.get("last_modified"),
                content_length=len(article["text"]),
                source=processor.source,
            )
            processor.metrics.increment("urls_fetched")
            processor.metrics.record_http_status(result["status"])
            processor.metrics.record_text_length(len(article["text"]))
            staging_out.write(json.dumps(article, ensure_ascii=False) + "\n")
            articles_count += 1

            if quota_limit is not None:
                processor.ledger.increment_daily_quota(
                    source="bbc", count=1, quota_limit=quota_limit
                )

            individual_file = (
                processor.raw_dir / f"bbc-somali_{processor.run_id}_raw_article-{index:04d}.json"
            )
            with open(individual_file, "w", encoding="utf-8") as handle:
                json.dump(article, handle, ensure_ascii=False, indent=2)

    if quota_limit is not None:
        with open(processor.article_links_file, encoding="utf-8") as handle:
            data = json.load(handle)
            total_links = len(data["links"])

        if len(links) < total_links:
            items_remaining = total_links - len(links)
            processor.ledger.mark_quota_hit(
                source="bbc", items_remaining=items_remaining, quota_limit=quota_limit
            )
            processor.logger.info(
                f"Quota hit: {quota_limit} articles processed, {items_remaining} links remaining for next run"
            )
            processor.metrics.increment("quota_hit")

    total_attempted = len(urls_to_fetch)
    success_rate = (articles_count / total_attempted * 100) if total_attempted > 0 else 0
    processor.logger.info("=" * 60)
    processor.logger.info(
        f"Extraction complete: {articles_count}/{total_attempted} articles extracted"
    )
    processor.logger.info(
        f"Failed: {failed_count} articles ({failed_count / total_attempted * 100:.1f}%)"
    )
    processor.logger.info(f"Success rate: {success_rate:.1f}%")
    processor.logger.info("=" * 60)

    metrics_path = Path("data/metrics") / f"{processor.run_id}_extraction.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    processor.metrics.export_json(metrics_path)
    report_path = Path("data/reports") / f"{processor.run_id}_extraction_quality_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    QualityReporter(processor.metrics).generate_markdown_report(report_path)
    processor.logger.info(f"Metrics exported: {metrics_path}")
    processor.logger.info(f"Extraction quality report: {report_path}")
    return processor.staging_file


def extract_sync(processor) -> Path:
    """Scrape articles synchronously."""
    if not processor.article_links_file.exists():
        raise FileNotFoundError(f"Article links not found: {processor.article_links_file}")

    processor.staging_dir.mkdir(parents=True, exist_ok=True)
    if processor.staging_file.exists() and not processor.force:
        processor.logger.info(f"Staging file already exists: {processor.staging_file}")
        processor.logger.info("Use force=True to re-scrape")
        return processor.staging_file
    if processor.staging_file.exists() and processor.force:
        processor.logger.info(f"Force re-scraping: removing existing file {processor.staging_file}")
        processor.staging_file.unlink()

    with open(processor.article_links_file, encoding="utf-8") as handle:
        data = json.load(handle)
        links = data["links"]

    quota_limit = processor.config.orchestration.get_quota("bbc")
    has_quota, remaining = processor.ledger.check_quota_available("bbc", quota_limit)
    if not has_quota:
        processor.logger.warning(f"Daily quota already reached for BBC: {quota_limit} articles")
        if processor.metrics is None:
            processor.metrics = MetricsCollector(
                processor.run_id, "BBC-Somali", pipeline_type=PipelineType.WEB_SCRAPING
            )
        processor.metrics.increment("quota_hit")
        return processor.staging_file

    if quota_limit is not None and remaining < len(links):
        processor.logger.info(
            f"Quota enforcement: processing {remaining} of {len(links)} links "
            f"(quota: {quota_limit} articles/day)"
        )
        links = links[:remaining]
    else:
        processor.logger.info(
            f"Processing {len(links)} links (quota: {quota_limit or 'unlimited'})"
        )

    set_context(run_id=processor.run_id, source="bbc-somali", phase="fetch")
    if processor.metrics is None:
        processor.metrics = MetricsCollector(
            processor.run_id, "BBC-Somali", pipeline_type=PipelineType.WEB_SCRAPING
        )

    processor.logger.info("=" * 60)
    processor.logger.info("PHASE 2: Article Extraction (Sync)")
    processor.logger.info("=" * 60)

    session = processor._get_http_session()
    articles_count = 0
    failed_count = 0
    connection_errors = 0

    with open(processor.staging_file, "w", encoding="utf-8") as staging_out:
        with tqdm(total=len(links), desc="Scraping BBC articles", unit="article") as pbar:
            for index, link in enumerate(links, 1):
                with TimedRequest() as timer:
                    try:
                        if not processor.ledger.should_fetch_url(link, force=processor.force):
                            processor.metrics.increment("urls_skipped")
                            pbar.update(1)
                            continue

                        article = processor._scrape_article(session, link)
                        if article and article.get("text"):
                            is_dup, dup_type, similar_url, text_hash, minhash_sig = (
                                processor.dedup.process_document(article["text"], link)
                            )
                            if is_dup:
                                processor.logger.info(
                                    f"{dup_type.capitalize()} duplicate detected: {link} (similar to {similar_url})"
                                )
                                processor.ledger.mark_duplicate(link, similar_url)
                                if dup_type == "exact":
                                    processor.metrics.increment("urls_deduplicated")
                                elif dup_type == "near":
                                    processor.metrics.increment("near_duplicates")
                            else:
                                article["text_hash"] = text_hash
                                article["minhash_signature"] = minhash_sig
                                processor.ledger.mark_fetched(
                                    url=link,
                                    http_status=200,
                                    content_length=len(article["text"]),
                                    source=processor.source,
                                )
                                processor.metrics.increment("urls_fetched")
                                processor.metrics.record_http_status(200)
                                processor.metrics.record_text_length(len(article["text"]))
                                staging_out.write(json.dumps(article, ensure_ascii=False) + "\n")
                                articles_count += 1

                                if quota_limit is not None:
                                    processor.ledger.increment_daily_quota(
                                        source="bbc", count=1, quota_limit=quota_limit
                                    )

                                individual_file = (
                                    processor.raw_dir
                                    / f"bbc-somali_{processor.run_id}_raw_article-{index:04d}.json"
                                )
                                with open(individual_file, "w", encoding="utf-8") as handle:
                                    json.dump(article, handle, ensure_ascii=False, indent=2)

                                if index == 1 or index % 10 == 0:
                                    word_count = len(article["text"].split())
                                    processor.logger.info(
                                        f"Article {index}: {word_count} words extracted"
                                    )
                        else:
                            processor.ledger.mark_failed(link, "Failed to scrape or empty text")
                            processor.metrics.increment("urls_failed")
                            processor.metrics.record_error("scrape_failed")
                            failed_count += 1
                    except (RemoteDisconnected, ProtocolError, ConnectionError) as err:
                        error_type = type(err).__name__
                        processor.logger.warning(
                            f"Connection error on article {index}/{len(links)} ({link}): {error_type} - skipping and continuing"
                        )
                        processor.ledger.mark_failed(link, f"Connection error: {error_type}")
                        processor.metrics.increment("urls_failed")
                        processor.metrics.record_error("connection_error")
                        failed_count += 1
                        connection_errors += 1
                        if connection_errors % 3 == 0:
                            processor.logger.info(
                                "Resetting HTTP session due to repeated connection errors"
                            )
                            session = processor._get_http_session()
                        pbar.update(1)
                        continue
                    except requests.HTTPError as err:
                        if err.response.status_code == 429:
                            retry_after = err.response.headers.get("Retry-After")
                            processor.rate_limiter.handle_429(retry_after)
                            processor.metrics.record_http_status(429)
                            processor.metrics.increment("rate_limit_errors")
                            pbar.update(1)
                            continue
                        processor.logger.warning(
                            f"HTTP {err.response.status_code} on article {index}/{len(links)} ({link}) - skipping and continuing"
                        )
                        processor.ledger.mark_failed(link, f"HTTP {err.response.status_code}")
                        processor.metrics.record_http_status(err.response.status_code)
                        processor.metrics.increment("urls_failed")
                        failed_count += 1
                        pbar.update(1)
                        continue
                    except requests.Timeout:
                        processor.logger.warning(
                            f"Timeout on article {index}/{len(links)} ({link}) - skipping and continuing"
                        )
                        processor.ledger.mark_failed(link, "Timeout")
                        processor.metrics.increment("urls_failed")
                        processor.metrics.record_error("timeout")
                        failed_count += 1
                        pbar.update(1)
                        continue

                    processor.metrics.record_fetch_duration(timer.get_elapsed_ms())
                    pbar.update(1)
                    pbar.set_postfix(
                        {
                            "extracted": articles_count,
                            "failed": failed_count,
                            "success_rate": f"{(articles_count / index) * 100:.1f}%",
                        }
                    )

    success_rate = (articles_count / len(links) * 100) if links else 0
    if quota_limit is not None:
        with open(processor.article_links_file, encoding="utf-8") as handle:
            data = json.load(handle)
            total_links = len(data["links"])
        if len(links) < total_links:
            items_remaining = total_links - len(links)
            processor.ledger.mark_quota_hit(
                source="bbc", items_remaining=items_remaining, quota_limit=quota_limit
            )
            processor.logger.info(
                f"Quota hit: {quota_limit} articles processed, {items_remaining} links remaining for next run"
            )
            processor.metrics.increment("quota_hit")

    processor.logger.info("=" * 60)
    processor.logger.info(f"Extraction complete: {articles_count}/{len(links)} articles extracted")
    processor.logger.info(
        f"Failed: {failed_count} articles ({failed_count / len(links) * 100:.1f}%)"
    )
    processor.logger.info(f"Success rate: {success_rate:.1f}%")
    if connection_errors > 0:
        processor.logger.info(f"Connection errors encountered: {connection_errors}")
    processor.logger.info("=" * 60)
    processor._export_stage_metrics("extraction")
    processor._generate_quality_report("extraction")
    return processor.staging_file


def scrape_article(processor, session: requests.Session, url: str) -> Optional[dict]:
    """Scrape a single BBC Somali article with conditional requests support."""
    try:
        conditional_headers = processor.ledger.get_conditional_headers(url)
        headers = {**processor.headers, **conditional_headers}
        response = session.get(url, headers=headers, timeout=_REQUEST_TIMEOUT)

        if response.status_code == 304:
            processor.logger.info(f"Article not modified: {url}")
            processor.metrics.increment("urls_not_modified")
            return None

        response.raise_for_status()
        etag = response.headers.get("ETag")
        last_modified = response.headers.get("Last-Modified")

        soup = BeautifulSoup(response.content, "html.parser")
        title_tag = soup.find("h1")
        title = title_tag.text.strip() if title_tag else "No title"

        text = _extract_paragraphs_from_soup(soup)

        if not text:
            processor.logger.warning(
                f"Empty text extracted from {url} - BBC may have changed their HTML structure"
            )

        date_tag = soup.find("time")
        date_published = (
            date_tag["datetime"] if date_tag and date_tag.has_attr("datetime") else None
        )

        article_data = {
            "url": url,
            "title": title,
            "text": text,
            "date": date_published,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "category": "news",
        }

        if etag or last_modified:
            processor.ledger.mark_fetched(
                url=url,
                http_status=200,
                etag=etag,
                last_modified=last_modified,
                content_length=len(text),
                source=processor.source,
            )

        return article_data
    except requests.HTTPError as err:
        if err.response.status_code == 304:
            return None
        raise
    except (RemoteDisconnected, ProtocolError, ConnectionError, requests.Timeout):
        raise
    except (ValueError, KeyError) as err:
        processor.logger.error(f"Error parsing article {url}: {err}")
        return None


def get_http_session(processor) -> requests.Session:
    """Create an HTTP session with default retry behavior."""
    return PipelineSetup.create_default_http_session(max_retries=3, backoff_factor=1.0)
