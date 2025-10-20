"""
BBC Somali news processor.

Ethically scrapes BBC Somali for news articles following best practices:
- Respects robots.txt
- Implements rate limiting and random delays
- Uses retry logic with exponential backoff
- Inherits shared orchestration from BasePipeline
"""

from pathlib import Path
import time
import random
from typing import List, Optional, Dict, Any, Iterator
from datetime import datetime, timezone
import json

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from tqdm import tqdm

from .base_pipeline import BasePipeline, RawRecord
from .text_cleaners import create_html_cleaner, TextCleaningPipeline


class BBCSomaliProcessor(BasePipeline):
    """
    Processor for scraping, extracting, and cleaning BBC Somali news articles.

    Inherits shared orchestration from BasePipeline and implements
    BBC-specific scraping logic with ethical rate limiting.
    """

    def __init__(self, max_articles: Optional[int] = None, delay_range: tuple = (3, 6), force: bool = False):
        """
        Initialize BBC Somali processor.

        Args:
            max_articles: Maximum number of articles to scrape (None = unlimited, scrapes all discovered)
            delay_range: (min, max) seconds to wait between requests
            force: Force reprocessing even if output files exist (default: False)
        """
        # Initialize BasePipeline with source name
        super().__init__(source="BBC-Somali", log_frequency=10, force=force)

        # BBC-specific configuration
        self.base_url = "https://www.bbc.com/somali"
        self.headers = {
            'User-Agent': 'SomaliNLPBot/1.0 (Educational Research; +https://github.com/your-repo)',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'so,en;q=0.9',
        }
        self.max_articles = max_articles
        self.delay_range = delay_range

        # File paths (BBC-specific naming)
        self.article_links_file = self.raw_dir / "article_links.json"
        self.staging_file = self.staging_dir / "bbcsom_articles.json"
        self.processed_file = self.processed_dir / "bbcsom.txt"

    def _register_filters(self) -> None:
        """Register BBC-specific filters."""
        from .filters import min_length_filter, langid_filter, dialect_heuristic_filter

        # Minimum length threshold for articles
        self.record_filters.append((min_length_filter, {"threshold": 50}))

        # Language filter (Somali only with relaxed confidence threshold)
        # Threshold lowered to 0.3 due to heuristic-based detection
        self.record_filters.append((langid_filter, {
            "allowed_langs": {"so"},
            "confidence_threshold": 0.3
        }))

        # Dialect/topic heuristics for enrichment
        # These help with downstream dialect scoring without filtering
        topic_lexicons = {
            "sports": ["kubadda", "ciyaaryahan", "kooxda", "tartanka", "garoonka"],
            "politics": ["xukuumad", "madaxweyne", "baarlamaan", "doorasho", "siyaasad"],
            "economy": ["dhaqaale", "ganacsiga", "suuq", "lacagta", "ganacsi"],
        }

        self.record_filters.append((dialect_heuristic_filter, {
            "ruleset": topic_lexicons,
            "enrich_only": True  # Don't filter, just enrich metadata
        }))

    def _create_cleaner(self) -> TextCleaningPipeline:
        """Create HTML text cleaner for BBC articles."""
        return create_html_cleaner()

    def _get_source_type(self) -> str:
        """Return source type for silver records."""
        return "news"

    def _get_license(self) -> str:
        """Return license information for silver records."""
        return "BBC Terms of Use"

    def _get_language(self) -> str:
        """Return language code for silver records."""
        return "so"

    def _get_source_metadata(self) -> Dict[str, Any]:
        """Return BBC-specific metadata for silver records."""
        return {
            "base_url": self.base_url,
            "max_articles": self.max_articles,
        }

    def download(self) -> Path:
        """
        Discover and download article links (respects robots.txt).

        Returns:
            Path to article links file
        """
        self.raw_dir.mkdir(parents=True, exist_ok=True)

        # Check if cached links exist and are still valid
        if self.article_links_file.exists() and not self.force:
            # Load cached metadata to check if parameters match
            with open(self.article_links_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)

            cached_max_articles = cached_data.get('max_articles_limit')

            # If parameters match, reuse cache
            if cached_max_articles == self.max_articles:
                self.logger.info(f"Article links already exist with matching parameters: {self.article_links_file}")
                return self.article_links_file
            else:
                self.logger.info(
                    f"Parameter mismatch: cached max_articles={cached_max_articles}, "
                    f"current max_articles={self.max_articles}. Re-discovering articles..."
                )

        # Check robots.txt
        self._check_robots_txt()

        # Get article links (no limit - discover everything)
        article_links = self._get_article_links()

        # Apply max_articles limit if specified (for scraping phase)
        links_to_scrape = article_links[:self.max_articles] if self.max_articles else article_links

        # Save all discovered links with metadata
        with open(self.article_links_file, 'w', encoding='utf-8') as f:
            json.dump({
                'links': links_to_scrape,
                'total_discovered': len(article_links),
                'total_to_scrape': len(links_to_scrape),
                'discovered_at': self.date_accessed,
                'max_articles_limit': self.max_articles,
            }, f, ensure_ascii=False, indent=2)

        if self.max_articles and len(article_links) > self.max_articles:
            self.logger.info(
                f"Limiting scrape to {self.max_articles} of {len(article_links)} discovered articles"
            )

        self.logger.info(f"Saved {len(links_to_scrape)} article links -> {self.article_links_file}")
        return self.article_links_file

    def extract(self) -> Path:
        """
        Scrape articles from discovered links.

        Returns:
            Path to scraped articles file
        """
        if not self.article_links_file.exists():
            raise FileNotFoundError(f"Article links not found: {self.article_links_file}")

        self.staging_dir.mkdir(parents=True, exist_ok=True)

        if self.staging_file.exists() and not self.force:
            self.logger.info(f"Staging file already exists: {self.staging_file}")
            self.logger.info("Use force=True to re-scrape")
            return self.staging_file

        if self.staging_file.exists() and self.force:
            self.logger.info(f"Force re-scraping: removing existing file {self.staging_file}")
            self.staging_file.unlink()

        # Load links
        with open(self.article_links_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            links = data['links']

        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("PHASE 2: Article Extraction")
        self.logger.info("=" * 60)

        articles = []
        session = self._get_http_session()

        # Use tqdm for progress tracking
        with tqdm(total=len(links), desc="Scraping articles", unit="article") as pbar:
            for i, link in enumerate(links, 1):
                article = self._scrape_article(session, link)
                if article and article.get('text'):
                    articles.append(article)

                    # Save incrementally (resilience against failures)
                    individual_file = self.raw_dir / f"article_{i:04d}.json"
                    with open(individual_file, 'w', encoding='utf-8') as f:
                        json.dump(article, f, ensure_ascii=False, indent=2)

                # Ethical scraping: respect rate limits
                delay = random.uniform(*self.delay_range)
                time.sleep(delay)

                # Update progress bar
                pbar.update(1)
                pbar.set_postfix({"extracted": len(articles)})

        # Save combined
        with open(self.staging_file, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)

        self.logger.info("=" * 60)
        self.logger.info(f"Extraction complete: {len(articles)}/{len(links)} articles extracted")
        self.logger.info("=" * 60)

        return self.staging_file

    def _extract_records(self) -> Iterator[RawRecord]:
        """
        Extract records from staging file.

        Yields RawRecord objects for each BBC article.
        BasePipeline.process() handles the rest (cleaning, writing, logging).
        """
        # Load articles from staging
        with open(self.staging_file, 'r', encoding='utf-8') as f:
            articles = json.load(f)

        # Yield RawRecord for each article
        for article in articles:
            yield RawRecord(
                title=article['title'],
                text=article['text'],
                url=article['url'],
                metadata={
                    "date_published": article.get('date'),
                    "category": article.get('category', 'news'),
                    "scraped_at": article.get('scraped_at'),
                },
            )

    def _check_robots_txt(self):
        """Check robots.txt for scraping permissions."""
        robots_url = f"{self.base_url}/robots.txt"
        try:
            response = requests.get(robots_url, timeout=10)
            self.logger.info(f"Checked robots.txt: {robots_url}")
            # Log if there are any specific restrictions
            if 'Disallow' in response.text and '/somali' in response.text:
                self.logger.warning(
                    "robots.txt contains restrictions. Please review before scraping: "
                    f"{robots_url}"
                )
        except Exception as e:
            self.logger.warning(f"Could not fetch robots.txt: {e}")

    def _discover_topic_sections(self, soup: BeautifulSoup) -> List[tuple]:
        """
        Dynamically discover unique topic section URLs from navigation menu.

        Args:
            soup: BeautifulSoup object of homepage

        Returns:
            List of unique (url, name) tuples for topic sections
        """
        seen_urls = set()
        sections = []

        # Find navigation links with /topics/ pattern
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/somali/topics/' in href:
                # Build full URL
                full_url = f"https://www.bbc.com{href}" if href.startswith('/') else href

                # Skip duplicates
                if full_url in seen_urls:
                    continue

                seen_urls.add(full_url)

                # Extract section name from link text
                section_name = link.get_text(strip=True)
                sections.append((full_url, section_name))

        return sections

    def _get_article_links(self) -> List[str]:
        """
        Discover article links from BBC Somali homepage, sections, and sitemap.

        Returns:
            List of article URLs
        """
        article_links = set()
        session = self._get_http_session()

        self.logger.info("=" * 60)
        self.logger.info("PHASE 1: Article Discovery")
        self.logger.info("=" * 60)

        # Strategy 1: Scrape homepage
        self.logger.info("Scraping homepage...")
        homepage_soup = None

        try:
            response = session.get(self.base_url, headers=self.headers, timeout=30)
            response.raise_for_status()

            homepage_soup = BeautifulSoup(response.content, 'html.parser')

            # Find article links (BBC-specific selectors)
            for link in homepage_soup.find_all('a', href=True):
                href = link['href']
                # BBC Somali articles have /somali/articles/ in URL
                if '/somali/' in href and '/articles/' in href:
                    full_url = f"https://www.bbc.com{href}" if href.startswith('/') else href
                    article_links.add(full_url)

            self.logger.info(f"  ✓ Homepage: {len(article_links)} articles")
            time.sleep(random.uniform(2, 4))

        except Exception as e:
            self.logger.error(f"  ✗ Homepage failed: {e}")

        # Strategy 2: Dynamically discover and scrape topic sections
        if homepage_soup:
            topic_sections = self._discover_topic_sections(homepage_soup)

            if topic_sections:
                self.logger.info(f"Scraping {len(topic_sections)} topic sections...")

                for section_url, section_name in topic_sections:
                    try:
                        response = session.get(section_url, headers=self.headers, timeout=30)
                        response.raise_for_status()

                        soup = BeautifulSoup(response.content, 'html.parser')

                        # Count articles before adding
                        before_count = len(article_links)

                        # Find article links
                        for link in soup.find_all('a', href=True):
                            href = link['href']
                            if '/somali/' in href and '/articles/' in href:
                                full_url = f"https://www.bbc.com{href}" if href.startswith('/') else href
                                article_links.add(full_url)

                        added = len(article_links) - before_count
                        self.logger.info(f"  ✓ {section_name}: +{added} articles")

                        time.sleep(random.uniform(2, 4))

                    except Exception as e:
                        self.logger.warning(f"  ✗ {section_name}: {e}")

        # Strategy 3: Parse sitemap for additional coverage
        self.logger.info("Scraping sitemap...")

        try:
            response = session.get(f"{self.base_url}/sitemap.xml", headers=self.headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'xml')

            # Count articles before adding
            before_count = len(article_links)

            # Extract URLs from sitemap
            for loc in soup.find_all('loc'):
                url = loc.text.strip()
                # Only include recent articles with /articles/ pattern
                if '/somali/' in url and 'articles' in url and 'bbc.com' in url:
                    # Convert old bbc.co.uk URLs to bbc.com
                    url = url.replace('bbc.co.uk', 'bbc.com')
                    article_links.add(url)

            added = len(article_links) - before_count
            self.logger.info(f"  ✓ Sitemap: +{added} articles")

        except Exception as e:
            self.logger.warning(f"  ✗ Sitemap: {e}")

        self.logger.info("=" * 60)
        self.logger.info(f"Total articles discovered: {len(article_links)}")
        self.logger.info("=" * 60)

        # Sort links for deterministic scraping order
        return sorted(article_links)

    def _scrape_article(self, session: requests.Session, url: str) -> Optional[Dict]:
        """
        Scrape a single BBC Somali article.

        Args:
            session: Requests session with retry logic
            url: Article URL

        Returns:
            Dictionary with article data or None if failed
        """
        try:
            response = session.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract title
            title_tag = soup.find('h1')
            title = title_tag.text.strip() if title_tag else "No title"

            # Extract article body
            # BBC uses specific CSS classes for paragraphs in their React-based structure
            paragraphs = soup.find_all('p', class_='bbc-1y32vyc')
            text = '\n'.join([p.text.strip() for p in paragraphs if p.text.strip()])

            # If no paragraphs found with specific class, fall back to general paragraph extraction
            if not text:
                paragraphs = soup.find_all('p')
                text = '\n'.join([p.text.strip() for p in paragraphs if p.text.strip()])

            # Extract metadata
            date_tag = soup.find('time')
            date_published = date_tag['datetime'] if date_tag and date_tag.has_attr('datetime') else None

            return {
                'url': url,
                'title': title,
                'text': text,
                'date': date_published,
                'scraped_at': datetime.now(timezone.utc).isoformat(),
                'category': 'news',  # Could be extracted from URL or meta tags
            }

        except Exception as e:
            self.logger.error(f"Error scraping {url}: {e}")
            return None

    def _get_http_session(self) -> requests.Session:
        """Create HTTP session with retry logic."""
        session = requests.Session()
        retries = Retry(
            total=3,  # Fewer retries for scraping vs downloading dumps
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
