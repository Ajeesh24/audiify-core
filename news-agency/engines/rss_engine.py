"""
Engine 1: RSS Collection

Collects tech news articles from RSS feeds and stores metadata in DynamoDB
Optimized for cost efficiency - stores only metadata, not full content
"""

import feedparser
import requests
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, urljoin
import re
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from models import Article, Job, EngineStatus
from config import (
    RSS_FEEDS, COLLECTION_SETTINGS, COST_OPTIMIZATION,
    get_feeds_by_category, get_high_priority_feeds
)
from utils.logger import get_logger

logger = get_logger(__name__)


class RSSEngine:
    """
    RSS Collection Engine

    Responsible for collecting articles from RSS feeds and storing
    metadata in DynamoDB for further processing by other engines.
    """

    def __init__(self):
        self.article_model = Article()
        self.job_model = Job()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': COLLECTION_SETTINGS['user_agent']
        })

    def collect_daily_articles(self, date: str = None) -> Dict[str, any]:
        """
        Main entry point for daily article collection

        Args:
            date: Date in YYYY-MM-DD format (defaults to today)

        Returns:
            Collection results summary
        """
        if not date:
            date = datetime.utcnow().strftime('%Y-%m-%d')

        logger.info(f"Starting RSS collection for {date}")

        # Start job tracking
        job = self.job_model.get_job(date) or self.job_model.create_daily_job(date)
        self.job_model.start_engine(date, 'rss_engine')

        try:
            results = {
                'date': date,
                'articles_collected': 0,
                'sources_processed': 0,
                'errors': [],
                'processing_time': 0,
                'feeds_processed': {}
            }

            start_time = time.time()

            # Collect from all categories
            for category in ['general-tech', 'ai-ml', 'devops-platform']:
                logger.info(f"Collecting articles for category: {category}")
                category_results = self._collect_category_articles(category, date)
                results['articles_collected'] += category_results['articles_collected']
                results['sources_processed'] += category_results['sources_processed']
                results['errors'].extend(category_results['errors'])
                results['feeds_processed'][category] = category_results

            results['processing_time'] = time.time() - start_time

            # Complete engine tracking
            self.job_model.complete_engine(date, 'rss_engine', {
                'articles_collected': results['articles_collected'],
                'sources_processed': results['sources_processed']
            })

            logger.info(f"RSS collection completed. Collected {results['articles_collected']} articles from {results['sources_processed']} sources")
            return results

        except Exception as e:
            logger.error(f"RSS collection failed: {str(e)}")
            self.job_model.fail_engine(date, 'rss_engine', str(e))
            raise

    def _collect_category_articles(self, category: str, date: str) -> Dict[str, any]:
        """
        Collect articles for a specific category

        Args:
            category: Category name (general-tech, ai-ml, devops-platform)
            date: Processing date

        Returns:
            Category collection results
        """
        # Use high priority feeds if we're in cost optimization mode
        if COST_OPTIMIZATION['enable_token_tracking']:
            feeds = get_high_priority_feeds(category)
        else:
            feeds = get_feeds_by_category(category)

        results = {
            'category': category,
            'articles_collected': 0,
            'sources_processed': 0,
            'errors': [],
            'feeds': {}
        }

        # Process feeds concurrently for better performance
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_feed = {
                executor.submit(self._process_feed, feed, category, date): feed
                for feed in feeds
            }

            for future in as_completed(future_to_feed):
                feed = future_to_feed[future]
                try:
                    feed_results = future.result()
                    results['articles_collected'] += feed_results['articles_collected']
                    results['sources_processed'] += 1
                    results['feeds'][feed['name']] = feed_results
                except Exception as e:
                    error_msg = f"Error processing {feed['name']}: {str(e)}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)

        return results

    def _process_feed(self, feed: Dict, category: str, date: str) -> Dict[str, any]:
        """
        Process a single RSS feed

        Args:
            feed: Feed configuration
            category: Article category
            date: Processing date

        Returns:
            Feed processing results
        """
        logger.info(f"Processing feed: {feed['name']} ({feed['url']})")

        try:
            # Fetch RSS feed with timeout and retries
            feed_data = self._fetch_feed_with_retry(feed['url'])
            if not feed_data:
                return {'articles_collected': 0, 'error': 'Failed to fetch feed'}

            articles = []
            max_articles = COLLECTION_SETTINGS['max_articles_per_feed']
            max_age_hours = COLLECTION_SETTINGS['max_article_age_hours']
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

            for entry in feed_data.entries[:max_articles]:
                try:
                    article = self._parse_feed_entry(entry, feed, category, date)
                    if article and self._is_article_valid(article, cutoff_time):
                        articles.append(article)
                except Exception as e:
                    logger.warning(f"Error parsing entry from {feed['name']}: {str(e)}")
                    continue

            # Store articles in database
            stored_count = self._store_articles(articles)

            logger.info(f"Processed {feed['name']}: {stored_count} articles stored")

            return {
                'articles_collected': stored_count,
                'articles_parsed': len(articles),
                'total_entries': len(feed_data.entries)
            }

        except Exception as e:
            logger.error(f"Error processing feed {feed['name']}: {str(e)}")
            return {'articles_collected': 0, 'error': str(e)}

    def _fetch_feed_with_retry(self, url: str) -> Optional[feedparser.FeedParserDict]:
        """
        Fetch RSS feed with retry logic

        Args:
            url: RSS feed URL

        Returns:
            Parsed feed data or None if failed
        """
        max_retries = COLLECTION_SETTINGS['max_retries']
        retry_delay = COLLECTION_SETTINGS['retry_delay']
        timeout = COLLECTION_SETTINGS['request_timeout']

        for attempt in range(max_retries + 1):
            try:
                logger.debug(f"Fetching {url} (attempt {attempt + 1}/{max_retries + 1})")

                # Use requests to fetch with proper headers and timeout
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()

                # Parse with feedparser
                feed_data = feedparser.parse(response.content)

                if feed_data.bozo and feed_data.bozo_exception:
                    logger.warning(f"Feed parsing warning for {url}: {feed_data.bozo_exception}")

                if hasattr(feed_data, 'entries') and feed_data.entries:
                    return feed_data

                logger.warning(f"No entries found in feed: {url}")
                return None

            except requests.exceptions.RequestException as e:
                logger.warning(f"Request error for {url} (attempt {attempt + 1}): {str(e)}")
                if attempt < max_retries:
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                continue

            except Exception as e:
                logger.error(f"Unexpected error fetching {url}: {str(e)}")
                break

        return None

    def _parse_feed_entry(self, entry: feedparser.FeedParserDict, feed: Dict, category: str, date: str) -> Optional[Dict]:
        """
        Parse a single RSS feed entry into article metadata

        Args:
            entry: RSS entry from feedparser
            feed: Feed configuration
            category: Article category
            date: Processing date

        Returns:
            Article metadata dict or None if invalid
        """
        try:
            # Extract basic information
            title = self._clean_text(getattr(entry, 'title', ''))
            link = getattr(entry, 'link', '')
            summary = self._clean_text(getattr(entry, 'summary', ''))

            if not title or not link:
                return None

            # Parse publication date
            published_date = self._parse_date(entry)
            if not published_date:
                published_date = datetime.utcnow()

            # Generate content hash for duplicate detection
            content_hash = self._generate_content_hash(title, link)

            # Create article metadata
            article = {
                'url': link,
                'title': title[:COLLECTION_SETTINGS['max_title_length']],
                'summary': summary[:500],  # Limit summary length
                'source': feed['name'],
                'published_date': published_date,
                'category': category,
                'content_hash': content_hash,
                'priority': feed.get('priority', 3),
                'processing_date': date,
                'feed_url': feed['url']
            }

            return article

        except Exception as e:
            logger.error(f"Error parsing entry: {str(e)}")
            return None

    def _parse_date(self, entry: feedparser.FeedParserDict) -> Optional[datetime]:
        """Parse publication date from RSS entry"""
        try:
            # Try different date fields
            for date_field in ['published_parsed', 'updated_parsed', 'created_parsed']:
                if hasattr(entry, date_field):
                    date_tuple = getattr(entry, date_field)
                    if date_tuple:
                        return datetime(*date_tuple[:6])

            # Try string dates
            for date_field in ['published', 'updated', 'created']:
                if hasattr(entry, date_field):
                    date_str = getattr(entry, date_field)
                    if date_str:
                        # feedparser usually handles this, but just in case
                        try:
                            return datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z').replace(tzinfo=None)
                        except:
                            pass

        except Exception as e:
            logger.debug(f"Error parsing date: {str(e)}")

        return None

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ''

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)

        # Decode HTML entities
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _generate_content_hash(self, title: str, url: str) -> str:
        """Generate hash for duplicate detection"""
        content = f"{title.lower()}{url}"
        return hashlib.md5(content.encode()).hexdigest()

    def _is_article_valid(self, article: Dict, cutoff_time: datetime) -> bool:
        """
        Check if article meets quality criteria

        Args:
            article: Article metadata
            cutoff_time: Maximum age cutoff

        Returns:
            True if article is valid for processing
        """
        # Check age
        if article['published_date'] < cutoff_time:
            return False

        # Check title length
        title = article['title']
        if len(title) < COLLECTION_SETTINGS['min_title_length']:
            return False

        # Check for filtered keywords
        title_lower = title.lower()
        for keyword in COLLECTION_SETTINGS['filter_keywords']:
            if keyword in title_lower:
                return False

        return True

    def _store_articles(self, articles: List[Dict]) -> int:
        """
        Store articles in DynamoDB

        Args:
            articles: List of article metadata

        Returns:
            Number of successfully stored articles
        """
        stored_count = 0

        for article in articles:
            try:
                # Check for duplicates before storing
                existing = self.article_model.get_article(article['url'])
                if existing:
                    logger.debug(f"Article already exists: {article['url']}")
                    continue

                # Store new article
                self.article_model.create_article(
                    url=article['url'],
                    title=article['title'],
                    summary=article['summary'],
                    source=article['source'],
                    published_date=article['published_date'],
                    category=article['category']
                )
                stored_count += 1

            except Exception as e:
                logger.error(f"Error storing article {article['url']}: {str(e)}")
                continue

        return stored_count

    def get_collection_stats(self, date: str) -> Dict[str, any]:
        """
        Get collection statistics for a specific date

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Collection statistics
        """
        job = self.job_model.get_job(date)
        if not job:
            return {'error': 'No collection job found for date'}

        rss_engine_data = job.get('engines', {}).get('rss_engine', {})

        return {
            'date': date,
            'status': rss_engine_data.get('status'),
            'articles_collected': rss_engine_data.get('articles_collected', 0),
            'sources_processed': rss_engine_data.get('sources_processed', 0),
            'duration': rss_engine_data.get('duration'),
            'started_at': rss_engine_data.get('started_at'),
            'completed_at': rss_engine_data.get('completed_at'),
            'error_message': rss_engine_data.get('error_message')
        }


def lambda_handler(event, context):
    """
    AWS Lambda handler for RSS collection

    Expected event format:
    {
        "date": "2024-01-15"  # optional, defaults to today
    }
    """
    try:
        date = event.get('date')
        engine = RSSEngine()
        results = engine.collect_daily_articles(date)

        return {
            'statusCode': 200,
            'body': results
        }
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}")
        return {
            'statusCode': 500,
            'body': {'error': str(e)}
        }


if __name__ == '__main__':
    # For local testing
    engine = RSSEngine()
    results = engine.collect_daily_articles()
    print(f"Collection completed: {results}")