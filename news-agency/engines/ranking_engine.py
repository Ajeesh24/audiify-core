"""
Engine 3: Ranking Engine

Ranks categorized articles and selects top stories for each category
Uses algorithmic ranking (no LLM) to optimize cost
"""

import time
import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict

from models import Article, Job, EngineStatus
from config import RELEVANCE_FACTORS, COST_OPTIMIZATION, BRIEF_GENERATION
from utils.logger import get_logger, log_engine_start, log_engine_complete, log_engine_error
from utils.metrics import performance_tracker, time_operation

logger = get_logger(__name__)


class RankingEngine:
    """
    Ranking Engine

    Responsible for:
    1. Ranking articles within each category
    2. Selecting top articles for brief generation
    3. Applying diversity and freshness factors
    """

    def __init__(self):
        self.article_model = Article()
        self.job_model = Job()

    def rank_daily_articles(self, date: str = None) -> Dict[str, any]:
        """
        Main entry point for daily article ranking

        Args:
            date: Date in YYYY-MM-DD format (defaults to today)

        Returns:
            Ranking results summary
        """
        if not date:
            date = datetime.utcnow().strftime('%Y-%m-%d')

        logger.info(f"Starting article ranking for {date}")
        log_engine_start('ranking_engine', date, logger)

        # Start job tracking
        job = self.job_model.get_job(date)
        if not job:
            raise ValueError(f"No job found for date {date}. Previous engines must run first.")

        self.job_model.start_engine(date, 'ranking_engine')

        try:
            results = {
                'date': date,
                'articles_processed': 0,
                'articles_ranked': 0,
                'processing_time': 0,
                'categories': {}
            }

            start_time = time.time()

            # Process each category
            for category in ['general-tech', 'ai-ml', 'devops-platform']:
                logger.info(f"Ranking articles for category: {category}")
                category_results = self._rank_category_articles(category, date)
                results['categories'][category] = category_results
                results['articles_processed'] += category_results['articles_processed']
                results['articles_ranked'] += category_results['articles_ranked']

            results['processing_time'] = time.time() - start_time

            # Complete engine tracking
            self.job_model.complete_engine(date, 'ranking_engine', {
                'articles_ranked': results['articles_ranked']
            })

            log_engine_complete('ranking_engine', date, results, logger)

            logger.info(f"Ranking completed. Processed {results['articles_processed']} articles, "
                       f"ranked {results['articles_ranked']} for brief generation")

            return results

        except Exception as e:
            logger.error(f"Ranking failed: {str(e)}")
            log_engine_error('ranking_engine', date, str(e), logger)
            self.job_model.fail_engine(date, 'ranking_engine', str(e))
            raise

    def _convert_decimals_to_floats(self, article: Dict) -> Dict:
        """
        Convert any Decimal values in article to floats for arithmetic operations

        Args:
            article: Article dictionary with potential Decimal values

        Returns:
            Article dictionary with Decimals converted to floats
        """
        converted_article = article.copy()
        for key, value in converted_article.items():
            if isinstance(value, Decimal):
                converted_article[key] = float(value)
        return converted_article

    def _rank_category_articles(self, category: str, date: str) -> Dict[str, any]:
        """
        Rank articles for a specific category

        Args:
            category: Category name
            date: Processing date

        Returns:
            Category ranking results
        """
        # Get categorized articles for this category
        articles = self.article_model.get_articles_by_category(category, date)

        # Filter only categorized articles
        categorized_articles = [a for a in articles if a.get('status') == 'categorized']

        results = {
            'category': category,
            'articles_processed': len(categorized_articles),
            'articles_ranked': 0,
            'top_articles': [],
            'ranking_scores': {}
        }

        if not categorized_articles:
            logger.warning(f"No categorized articles found for {category} on {date}")
            return results

        # Calculate enhanced ranking scores
        scored_articles = []
        for article in categorized_articles:
            # Convert any Decimal values to floats before calculations
            article = self._convert_decimals_to_floats(article)
            enhanced_score = self._calculate_enhanced_ranking_score(article, categorized_articles)
            scored_articles.append({
                'article': article,
                'final_score': enhanced_score,
                'components': self._get_score_components(article, categorized_articles)
            })

        # Sort by final score (highest first)
        scored_articles.sort(key=lambda x: x['final_score'], reverse=True)

        # Select top articles for brief generation
        max_articles = BRIEF_GENERATION['max_articles_per_brief']
        top_articles = scored_articles[:max_articles]

        # Apply diversity filter to ensure variety
        diverse_articles = self._apply_diversity_filter(top_articles, category)

        # Update articles with ranking status
        ranked_urls = []
        for i, scored_article in enumerate(diverse_articles):
            article = scored_article['article']
            ranking_position = i + 1
            final_score = scored_article['final_score']

            # Update article in database
            self.article_model.update_article(
                article['url'],
                status='ranked',
                ranking_position=ranking_position,
                final_ranking_score=final_score,
                ranked_at=datetime.utcnow().isoformat()
            )

            ranked_urls.append(article['url'])
            results['ranking_scores'][article['url']] = {
                'position': ranking_position,
                'score': final_score,
                'components': scored_article['components']
            }

        results['articles_ranked'] = len(diverse_articles)
        results['top_articles'] = [a['article'] for a in diverse_articles]

        logger.info(f"Ranked {len(diverse_articles)} articles for {category}")
        return results

    def _calculate_enhanced_ranking_score(self, article: Dict, all_articles: List[Dict]) -> float:
        """
        Calculate enhanced ranking score combining multiple factors

        Args:
            article: Article to score
            all_articles: All articles in category (for context)

        Returns:
            Enhanced ranking score
        """
        base_score = article.get('relevance_score', 5.0)
        # Convert Decimal to float for calculations
        if isinstance(base_score, Decimal):
            base_score = float(base_score)

        # Apply source authority boost
        source_boost = self._get_source_authority_boost(article)

        # Apply freshness factor
        freshness_factor = self._get_freshness_factor(article)

        # Apply engagement prediction
        engagement_factor = self._predict_engagement(article)

        # Apply uniqueness boost (avoid similar articles)
        uniqueness_factor = self._calculate_uniqueness(article, all_articles)

        # Combine factors
        enhanced_score = (
            base_score *
            source_boost *
            freshness_factor *
            engagement_factor *
            uniqueness_factor
        )

        return min(10.0, max(0.1, enhanced_score))

    def _get_source_authority_boost(self, article: Dict) -> float:
        """
        Calculate source authority boost based on source reputation

        Args:
            article: Article metadata

        Returns:
            Source authority multiplier
        """
        source = article.get('source', '').lower()

        # High authority sources
        high_authority = [
            'techcrunch', 'the verge', 'ars technica', 'wired', 'mit technology review',
            'openai', 'google ai', 'aws', 'microsoft', 'github'
        ]

        # Medium authority sources
        medium_authority = [
            'venturebeat', 'engadget', 'docker', 'kubernetes', 'hashicorp'
        ]

        for high_source in high_authority:
            if high_source in source:
                return 1.3

        for medium_source in medium_authority:
            if medium_source in source:
                return 1.1

        return 1.0  # Default multiplier

    def _get_freshness_factor(self, article: Dict) -> float:
        """
        Calculate freshness factor based on article age

        Args:
            article: Article metadata

        Returns:
            Freshness multiplier
        """
        published_date = article.get('published_date')
        if not published_date:
            return 1.0

        if isinstance(published_date, str):
            published_date = datetime.fromisoformat(published_date.replace('Z', ''))

        hours_old = (datetime.utcnow() - published_date).total_seconds() / 3600

        if hours_old <= 2:
            return 1.5    # Very fresh
        elif hours_old <= 6:
            return 1.3    # Fresh
        elif hours_old <= 12:
            return 1.1    # Recent
        elif hours_old <= 24:
            return 1.0    # Standard
        else:
            return 0.8    # Old

    def _predict_engagement(self, article: Dict) -> float:
        """
        Predict engagement based on title characteristics

        Args:
            article: Article metadata

        Returns:
            Engagement prediction multiplier
        """
        title = article.get('title', '').lower()

        # High engagement indicators
        high_engagement_words = [
            'breakthrough', 'revolutionary', 'first ever', 'launches', 'announces',
            'reveals', 'exclusive', 'breaking', 'major', 'significant'
        ]

        # Medium engagement indicators
        medium_engagement_words = [
            'new', 'update', 'releases', 'introduces', 'unveils', 'partnership'
        ]

        # Low engagement indicators
        low_engagement_words = [
            'rumor', 'speculation', 'might', 'could', 'possibly'
        ]

        for word in high_engagement_words:
            if word in title:
                return 1.4

        for word in medium_engagement_words:
            if word in title:
                return 1.2

        for word in low_engagement_words:
            if word in title:
                return 0.8

        return 1.0

    def _calculate_uniqueness(self, article: Dict, all_articles: List[Dict]) -> float:
        """
        Calculate uniqueness factor to avoid similar articles

        Args:
            article: Article to check
            all_articles: All articles in category

        Returns:
            Uniqueness multiplier
        """
        title = article.get('title', '').lower()
        title_words = set(title.split())

        similar_count = 0
        for other_article in all_articles:
            if other_article['url'] == article['url']:
                continue

            other_title = other_article.get('title', '').lower()
            other_words = set(other_title.split())

            # Calculate word overlap
            overlap = len(title_words.intersection(other_words))
            total_words = len(title_words.union(other_words))

            if total_words > 0:
                similarity = overlap / total_words
                if similarity > 0.4:  # 40% similarity threshold
                    similar_count += 1

        # Penalize articles with many similar articles
        if similar_count == 0:
            return 1.2  # Unique content bonus
        elif similar_count == 1:
            return 1.0  # Normal
        elif similar_count == 2:
            return 0.9  # Slight penalty
        else:
            return 0.7  # Higher penalty for very common topics

    def _apply_diversity_filter(self, scored_articles: List[Dict], category: str) -> List[Dict]:
        """
        Apply diversity filter to ensure variety in selected articles

        Args:
            scored_articles: Articles sorted by score
            category: Article category

        Returns:
            Filtered list with diversity applied
        """
        if len(scored_articles) <= BRIEF_GENERATION['min_articles_per_brief']:
            return scored_articles

        diverse_articles = []
        used_keywords = set()
        source_count = defaultdict(int)

        for scored_article in scored_articles:
            article = scored_article['article']
            title = article.get('title', '').lower()
            source = article.get('source', '')

            # Extract keywords from title
            keywords = self._extract_keywords(title)

            # Check diversity criteria
            keyword_overlap = len(keywords.intersection(used_keywords))
            source_limit = 2  # Max articles per source

            # Accept article if it adds diversity or is high-scoring enough
            should_include = (
                keyword_overlap <= 2 and  # Limited keyword overlap
                source_count[source] < source_limit and  # Source diversity
                len(diverse_articles) < BRIEF_GENERATION['max_articles_per_brief']
            )

            if should_include:
                diverse_articles.append(scored_article)
                used_keywords.update(keywords)
                source_count[source] += 1

            # Always include minimum number of top articles regardless of diversity
            elif len(diverse_articles) < BRIEF_GENERATION['min_articles_per_brief']:
                diverse_articles.append(scored_article)
                used_keywords.update(keywords)
                source_count[source] += 1

        return diverse_articles

    def _extract_keywords(self, title: str) -> set:
        """
        Extract meaningful keywords from article title

        Args:
            title: Article title

        Returns:
            Set of keywords
        """
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'will', 'would', 'could', 'should', 'may', 'might'
        }

        words = title.lower().split()
        keywords = {word for word in words if len(word) > 3 and word not in stop_words}
        return keywords

    def _get_score_components(self, article: Dict, all_articles: List[Dict]) -> Dict[str, float]:
        """
        Get breakdown of score components for transparency

        Args:
            article: Article metadata
            all_articles: All articles for context

        Returns:
            Dictionary of score components
        """
        base_relevance = article.get('relevance_score', 5.0)
        # Convert Decimal to float for consistency
        if isinstance(base_relevance, Decimal):
            base_relevance = float(base_relevance)

        return {
            'base_relevance': base_relevance,
            'source_authority': self._get_source_authority_boost(article),
            'freshness_factor': self._get_freshness_factor(article),
            'engagement_prediction': self._predict_engagement(article),
            'uniqueness_factor': self._calculate_uniqueness(article, all_articles)
        }

    def get_ranking_stats(self, date: str) -> Dict[str, any]:
        """
        Get ranking statistics for a specific date

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Ranking statistics
        """
        job = self.job_model.get_job(date)
        if not job:
            return {'error': 'No ranking job found for date'}

        engine_data = job.get('engines', {}).get('ranking_engine', {})

        return {
            'date': date,
            'status': engine_data.get('status'),
            'articles_ranked': engine_data.get('articles_ranked', 0),
            'duration': engine_data.get('duration'),
            'started_at': engine_data.get('started_at'),
            'completed_at': engine_data.get('completed_at'),
            'error_message': engine_data.get('error_message')
        }

    def get_top_articles_by_category(self, category: str, date: str, limit: int = 10) -> List[Dict]:
        """
        Get top-ranked articles for a category

        Args:
            category: Category name
            date: Processing date
            limit: Number of articles to return

        Returns:
            List of top articles with ranking information
        """
        articles = self.article_model.get_articles_by_category(category, date)

        # Filter ranked articles and sort by ranking position
        ranked_articles = [
            a for a in articles
            if a.get('status') == 'ranked' and a.get('ranking_position')
        ]

        ranked_articles.sort(key=lambda x: x.get('ranking_position', float('inf')))

        return ranked_articles[:limit]


def lambda_handler(event, context):
    """
    AWS Lambda handler for article ranking

    Expected event format:
    {
        "date": "2024-01-15"  # optional, defaults to today
    }
    """
    try:
        date = event.get('date')
        engine = RankingEngine()
        results = engine.rank_daily_articles(date)

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
    engine = RankingEngine()
    results = engine.rank_daily_articles()
    print(f"Ranking completed: {results}")