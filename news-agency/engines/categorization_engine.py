"""
Engine 2: Categorization Engine

Uses LLM to categorize articles and score relevance
Optimized for cost efficiency with minimal token usage
"""

import openai
import time
import hashlib
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from models import Article, Job, EngineStatus
from config import (
    OPENAI_SETTINGS, COST_OPTIMIZATION, get_classification_prompt,
    get_all_categories, RELEVANCE_FACTORS
)
from utils.logger import get_logger, log_engine_start, log_engine_complete, log_engine_error
from utils.metrics import cost_tracker, time_operation, estimate_tokens, calculate_llm_cost

logger = get_logger(__name__)


class CategorizationEngine:
    """
    Categorization Engine

    Responsible for:
    1. Categorizing articles using LLM
    2. Scoring article relevance
    3. Detecting and filtering duplicates
    """

    def __init__(self):
        self.article_model = Article()
        self.job_model = Job()

        # Initialize OpenAI client
        openai.api_key = OPENAI_SETTINGS['api_key']
        self.model = OPENAI_SETTINGS['model']
        self.max_tokens = OPENAI_SETTINGS['max_tokens']
        self.temperature = OPENAI_SETTINGS['temperature']

    def categorize_daily_articles(self, date: str = None) -> Dict[str, any]:
        """
        Main entry point for daily article categorization

        Args:
            date: Date in YYYY-MM-DD format (defaults to today)

        Returns:
            Categorization results summary
        """
        if not date:
            date = datetime.utcnow().strftime('%Y-%m-%d')

        logger.info(f"Starting article categorization for {date}")
        log_engine_start('categorization_engine', date, logger)

        # Start job tracking
        job = self.job_model.get_job(date)
        if not job:
            raise ValueError(f"No job found for date {date}. RSS collection must run first.")

        self.job_model.start_engine(date, 'categorization_engine')

        try:
            results = {
                'date': date,
                'articles_processed': 0,
                'articles_categorized': 0,
                'duplicates_removed': 0,
                'token_usage': 0,
                'cost_usd': 0.0,
                'processing_time': 0,
                'categories': {
                    'general-tech': 0,
                    'ai-ml': 0,
                    'devops-platform': 0
                },
                'errors': []
            }

            start_time = time.time()

            # Get uncategorized articles
            uncategorized_articles = self.article_model.get_articles_by_date(date, status='collected')
            results['articles_processed'] = len(uncategorized_articles)

            if not uncategorized_articles:
                logger.warning(f"No uncategorized articles found for {date}")
                self.job_model.complete_engine(date, 'categorization_engine', results)
                return results

            # Check budget before processing
            if cost_tracker.is_budget_exceeded(date):
                logger.warning("Daily budget exceeded, skipping categorization")
                self.job_model.fail_engine(date, 'categorization_engine', 'Daily budget exceeded')
                return results

            # Remove duplicates first (saves on LLM costs)
            unique_articles = self._remove_duplicates(uncategorized_articles)
            results['duplicates_removed'] = len(uncategorized_articles) - len(unique_articles)

            # Process articles in batches to control costs
            batch_size = min(10, len(unique_articles))
            processed_articles = []

            for i in range(0, len(unique_articles), batch_size):
                batch = unique_articles[i:i + batch_size]

                # Check budget before each batch
                if cost_tracker.is_budget_exceeded(date):
                    logger.warning("Budget exceeded during processing, stopping early")
                    break

                batch_results = self._process_article_batch(batch, date)
                processed_articles.extend(batch_results['articles'])
                results['token_usage'] += batch_results['token_usage']
                results['cost_usd'] += batch_results['cost_usd']
                results['errors'].extend(batch_results['errors'])

                # Small delay to avoid rate limits
                time.sleep(0.1)

            # Update category counts and save articles
            for article in processed_articles:
                if article.get('category'):
                    results['categories'][article['category']] += 1

            # Save categorized articles
            self._save_categorized_articles(processed_articles)
            results['articles_categorized'] = len(processed_articles)

            results['processing_time'] = time.time() - start_time

            # Complete engine tracking
            self.job_model.complete_engine(date, 'categorization_engine', {
                'articles_categorized': results['articles_categorized'],
                'token_usage': results['token_usage']
            })

            log_engine_complete('categorization_engine', date, results, logger)

            logger.info(f"Categorization completed. Processed {results['articles_categorized']} articles, "
                       f"used {results['token_usage']} tokens, cost ${results['cost_usd']:.4f}")

            return results

        except Exception as e:
            logger.error(f"Categorization failed: {str(e)}")
            log_engine_error('categorization_engine', date, str(e), logger)
            self.job_model.fail_engine(date, 'categorization_engine', str(e))
            raise

    def _remove_duplicates(self, articles: List[Dict]) -> List[Dict]:
        """
        Remove duplicate articles based on content similarity

        Args:
            articles: List of article metadata

        Returns:
            List of unique articles
        """
        unique_articles = []
        seen_hashes = set()

        for article in articles:
            content_hash = article.get('content_hash')
            if not content_hash:
                # Generate hash if missing
                title_url = f"{article['title'].lower()}{article['url']}"
                content_hash = hashlib.md5(title_url.encode()).hexdigest()

            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_articles.append(article)

        logger.info(f"Removed {len(articles) - len(unique_articles)} duplicates")
        return unique_articles

    def _process_article_batch(self, articles: List[Dict], date: str) -> Dict[str, any]:
        """
        Process a batch of articles for categorization

        Args:
            articles: List of articles to process
            date: Processing date

        Returns:
            Batch processing results
        """
        results = {
            'articles': [],
            'token_usage': 0,
            'cost_usd': 0.0,
            'errors': []
        }

        # Use ThreadPoolExecutor for parallel processing (careful with rate limits)
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_article = {
                executor.submit(self._categorize_single_article, article): article
                for article in articles
            }

            for future in as_completed(future_to_article):
                article = future_to_article[future]
                try:
                    categorized_article, tokens_used, cost = future.result()
                    if categorized_article:
                        results['articles'].append(categorized_article)
                        results['token_usage'] += tokens_used
                        results['cost_usd'] += cost

                except Exception as e:
                    error_msg = f"Error categorizing article {article.get('url', 'unknown')}: {str(e)}"
                    logger.warning(error_msg)
                    results['errors'].append(error_msg)

        return results

    def _categorize_single_article(self, article: Dict) -> Tuple[Optional[Dict], int, float]:
        """
        Categorize a single article using LLM

        Args:
            article: Article metadata

        Returns:
            Tuple of (categorized_article, tokens_used, cost)
        """
        try:
            # Create categorization prompt
            prompt = get_classification_prompt(
                'category_classification',
                title=article['title'],
                summary=article['summary'],
                source=article['source']
            )

            # Estimate tokens for cost control
            estimated_tokens = estimate_tokens(prompt) + 50  # +50 for response
            estimated_cost = calculate_llm_cost(prompt, self.model, 50)

            # Check if this request would exceed budget
            if cost_tracker.get_daily_cost() + estimated_cost > COST_OPTIMIZATION['target_daily_cost']:
                logger.warning("Skipping article categorization - would exceed daily budget")
                return None, 0, 0

            # Make OpenAI request
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,  # Short response expected
                temperature=self.temperature,
                timeout=OPENAI_SETTINGS['timeout']
            )

            # Extract category from response
            category_response = response.choices[0].message.content.strip().lower()

            # Map response to valid category
            category = self._parse_category_response(category_response)
            if not category:
                logger.warning(f"Invalid category response: {category_response}")
                return None, 0, 0

            # Calculate relevance score
            relevance_score = self._calculate_relevance_score(article, category)

            # Update article with categorization results
            categorized_article = article.copy()
            categorized_article.update({
                'category': category,
                'relevance_score': relevance_score,
                'status': 'categorized',
                'categorized_at': datetime.utcnow().isoformat()
            })

            # Track usage and cost
            tokens_used = response.usage.total_tokens
            cost = cost_tracker.track_llm_usage(
                'categorization',
                self.model,
                response.usage.prompt_tokens,
                response.usage.completion_tokens
            )

            return categorized_article, tokens_used, cost

        except Exception as e:
            logger.error(f"Error in LLM categorization: {str(e)}")
            return None, 0, 0

    def _parse_category_response(self, response: str) -> Optional[str]:
        """
        Parse LLM response to extract valid category

        Args:
            response: Raw LLM response

        Returns:
            Valid category name or None
        """
        response = response.lower().strip()

        # Direct matches
        valid_categories = get_all_categories()
        for category in valid_categories:
            if category in response:
                return category

        # Handle common variations
        if 'ai' in response or 'ml' in response or 'artificial' in response:
            return 'ai-ml'
        elif 'devops' in response or 'cloud' in response or 'platform' in response:
            return 'devops-platform'
        elif 'general' in response or 'tech' in response:
            return 'general-tech'

        return None

    def _calculate_relevance_score(self, article: Dict, category: str) -> float:
        """
        Calculate relevance score for an article

        Args:
            article: Article metadata
            category: Assigned category

        Returns:
            Relevance score between 0.0 and 10.0
        """
        base_score = 5.0  # Start with medium relevance

        # Source credibility factor
        priority = article.get('priority', 3)
        credibility_multiplier = RELEVANCE_FACTORS['source_credibility'].get(priority, 0.8)
        base_score *= credibility_multiplier

        # Recency bonus
        published_date = article.get('published_date')
        if published_date:
            if isinstance(published_date, str):
                published_date = datetime.fromisoformat(published_date)

            hours_old = (datetime.utcnow() - published_date).total_seconds() / 3600

            if hours_old <= 2:
                base_score *= RELEVANCE_FACTORS['recency_bonus']['0-2_hours']
            elif hours_old <= 6:
                base_score *= RELEVANCE_FACTORS['recency_bonus']['2-6_hours']
            elif hours_old <= 12:
                base_score *= RELEVANCE_FACTORS['recency_bonus']['6-12_hours']
            else:
                base_score *= RELEVANCE_FACTORS['recency_bonus']['12-24_hours']

        # Quality indicators based on title/content
        title = article.get('title', '').lower()
        quality_bonus = 1.0

        if any(keyword in title for keyword in ['announces', 'launches', 'releases']):
            quality_bonus = RELEVANCE_FACTORS['quality_indicators']['product_launch']
        elif any(keyword in title for keyword in ['research', 'study', 'findings']):
            quality_bonus = RELEVANCE_FACTORS['quality_indicators']['research_findings']
        elif any(keyword in title for keyword in ['breaking', 'exclusive']):
            quality_bonus = RELEVANCE_FACTORS['quality_indicators']['breaking_news']

        base_score *= quality_bonus

        # Clamp to valid range
        return max(1.0, min(10.0, base_score))

    def _save_categorized_articles(self, articles: List[Dict]):
        """
        Save categorized articles to database

        Args:
            articles: List of categorized articles
        """
        for article in articles:
            try:
                self.article_model.update_article(
                    article['url'],
                    category=article['category'],
                    relevance_score=article['relevance_score'],
                    status='categorized'
                )
            except Exception as e:
                logger.error(f"Error saving article {article['url']}: {str(e)}")

    def get_categorization_stats(self, date: str) -> Dict[str, any]:
        """
        Get categorization statistics for a specific date

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Categorization statistics
        """
        job = self.job_model.get_job(date)
        if not job:
            return {'error': 'No categorization job found for date'}

        engine_data = job.get('engines', {}).get('categorization_engine', {})

        return {
            'date': date,
            'status': engine_data.get('status'),
            'articles_categorized': engine_data.get('articles_categorized', 0),
            'token_usage': engine_data.get('token_usage', 0),
            'duration': engine_data.get('duration'),
            'started_at': engine_data.get('started_at'),
            'completed_at': engine_data.get('completed_at'),
            'error_message': engine_data.get('error_message')
        }


def lambda_handler(event, context):
    """
    AWS Lambda handler for article categorization

    Expected event format:
    {
        "date": "2024-01-15"  # optional, defaults to today
    }
    """
    try:
        date = event.get('date')
        engine = CategorizationEngine()
        results = engine.categorize_daily_articles(date)

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
    engine = CategorizationEngine()
    results = engine.categorize_daily_articles()
    print(f"Categorization completed: {results}")