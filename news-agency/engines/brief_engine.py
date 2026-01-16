"""
Engine 4: Brief Generation Engine

Generates conversational audio briefs from ranked articles using LangChain LLM
Optimized for cost efficiency with detailed token management
"""

import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from models import Article, Brief, Job, EngineStatus
from config import (
    COST_OPTIMIZATION, BRIEF_GENERATION,
    get_all_categories, get_classification_prompt
)
from utils.logger import get_logger, log_engine_start, log_engine_complete, log_engine_error
from utils.metrics import cost_tracker, time_operation, estimate_tokens, calculate_llm_cost
from utils.llm_service import llm_service
from utils.extractor import ArticleExtractor

logger = get_logger(__name__)


class BriefGenerationEngine:
    """
    Brief Generation Engine

    Responsible for:
    1. Collecting top-ranked articles for each category
    2. Generating conversational audio briefs using LLM
    3. Managing word count and token usage
    4. Storing generated briefs for audio processing
    """

    def __init__(self):
        self.article_model = Article()
        self.brief_model = Brief()
        self.extractor = ArticleExtractor()
        self.job_model = Job()
        # LLM service is already initialized as a global instance

    def generate_daily_briefs(self, date: str = None) -> Dict[str, any]:
        """
        Main entry point for daily brief generation

        Args:
            date: Date in YYYY-MM-DD format (defaults to today)

        Returns:
            Brief generation results summary
        """
        if not date:
            date = datetime.utcnow().strftime('%Y-%m-%d')

        logger.info(f"Starting brief generation for {date}")
        log_engine_start('brief_engine', date, logger)

        # Start job tracking
        job = self.job_model.get_job(date)
        if not job:
            raise ValueError(f"No job found for date {date}. Previous engines must run first.")

        self.job_model.start_engine(date, 'brief_engine')

        try:
            results = {
                'date': date,
                'briefs_generated': 0,
                'total_words': 0,
                'token_usage': 0,
                'cost_usd': 0.0,
                'processing_time': 0,
                'categories': {}
            }

            start_time = time.time()

            # Check budget before processing
            if cost_tracker.is_budget_exceeded(date):
                logger.warning("Daily budget exceeded, skipping brief generation")
                self.job_model.fail_engine(date, 'brief_engine', 'Daily budget exceeded')
                return results

            # Generate briefs for each category
            for category in get_all_categories():
                logger.info(f"Generating brief for category: {category}")

                try:
                    category_results = self._generate_category_brief(category, date)
                    results['categories'][category] = category_results

                    if category_results['success']:
                        results['briefs_generated'] += 1
                        results['total_words'] += category_results['word_count']
                        results['token_usage'] += category_results['token_usage']
                        results['cost_usd'] += category_results['cost_usd']

                except Exception as e:
                    logger.error(f"Error generating brief for {category}: {str(e)}")
                    results['categories'][category] = {
                        'success': False,
                        'error': str(e),
                        'word_count': 0,
                        'token_usage': 0,
                        'cost_usd': 0.0
                    }

            results['processing_time'] = time.time() - start_time

            # Complete engine tracking
            self.job_model.complete_engine(date, 'brief_engine', {
                'briefs_generated': results['briefs_generated'],
                'total_words': results['total_words'],
                'token_usage': results['token_usage']
            })

            log_engine_complete('brief_engine', date, results, logger)

            logger.info(f"Brief generation completed. Generated {results['briefs_generated']} briefs, "
                       f"{results['total_words']} total words, used {results['token_usage']} tokens, "
                       f"cost ${results['cost_usd']:.4f}")

            return results

        except Exception as e:
            logger.error(f"Brief generation failed: {str(e)}")
            log_engine_error('brief_engine', date, str(e), logger)
            self.job_model.fail_engine(date, 'brief_engine', str(e))
            raise

    def _generate_category_brief(self, category: str, date: str) -> Dict[str, any]:
        """
        Generate a brief for a specific category

        Args:
            category: Category name
            date: Processing date

        Returns:
            Category brief generation results
        """
        # Get top-ranked articles for this category
        top_articles = self.article_model.get_top_articles(category, date,
                                                           BRIEF_GENERATION['max_articles_per_brief'])

        if len(top_articles) < BRIEF_GENERATION['min_articles_per_brief']:
            return {
                'success': False,
                'error': f'Insufficient articles: {len(top_articles)} < {BRIEF_GENERATION["min_articles_per_brief"]}',
                'word_count': 0,
                'token_usage': 0,
                'cost_usd': 0.0
            }

        # Extract full article content for richer briefs
        logger.info(f"Extracting full content from {len(top_articles)} articles for {category}")
        enriched_articles = self._extract_article_contents_sync(top_articles)

        # Create brief generation prompt
        prompt = self._create_brief_prompt(category, enriched_articles, date)

        # Estimate cost and check budget
        estimated_tokens = estimate_tokens(prompt) + BRIEF_GENERATION['target_word_count'][category] // 3
        estimated_cost = calculate_llm_cost(prompt, 'gpt-4o-mini', estimated_tokens // 2)

        if cost_tracker.get_daily_cost() + estimated_cost > COST_OPTIMIZATION['target_daily_cost']:
            return {
                'success': False,
                'error': 'Would exceed daily budget',
                'word_count': 0,
                'token_usage': 0,
                'cost_usd': 0.0
            }

        try:
            # Generate brief using LangChain LLM service
            brief_result = llm_service.generate_brief(
                category=category,
                articles=enriched_articles,
                date=date,
                prompt_template=prompt,
                target_word_count=BRIEF_GENERATION['target_word_count'][category]
            )

            generated_content = brief_result['content']
            word_count = brief_result['word_count']

            # Track usage and cost
            token_usage = brief_result.get('token_usage', {})
            tokens_used = token_usage.get('total_tokens', estimated_tokens)
            cost = cost_tracker.track_llm_usage(
                'brief_generation',
                'gpt-4o-mini',
                token_usage.get('input_tokens', estimated_tokens // 2),
                token_usage.get('output_tokens', estimated_tokens // 2)
            )

            # Calculate estimated audio duration (150 words per minute)
            estimated_duration = int((word_count / 150) * 60)  # seconds

            # Store brief in database
            article_urls = [article['url'] for article in enriched_articles]
            brief_data = self.brief_model.create_brief(
                category=category,
                date=date,
                content=generated_content,
                articles_used=article_urls,
                word_count=word_count,
                estimated_duration=estimated_duration
            )

            if not brief_data or 'brief_id' not in brief_data:
                logger.error(f"Failed to create/update brief for {category}")
                return {
                    'success': False,
                    'error': 'Failed to save brief to database',
                    'word_count': word_count,
                    'token_usage': tokens_used,
                    'cost_usd': cost
                }

            # Update generation stats
            self.brief_model.update_generation_stats(category, date, {
                'generation_time': time.time(),
                'token_usage': tokens_used,
                'articles_processed': len(top_articles)
            })

            return {
                'success': True,
                'brief_id': brief_data['brief_id'],
                'word_count': word_count,
                'estimated_duration': estimated_duration,
                'articles_used': len(top_articles),
                'token_usage': tokens_used,
                'cost_usd': cost
            }

        except Exception as e:
            logger.error(f"Error in LLM brief generation for {category}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'word_count': 0,
                'token_usage': 0,
                'cost_usd': 0.0
            }

    def _create_brief_prompt(self, category: str, articles: List[Dict], date: str) -> str:
        """
        Create the brief generation prompt

        Args:
            category: Category name
            articles: List of top articles
            date: Processing date

        Returns:
            Formatted prompt for LLM
        """
        category_info = {
            'general-tech': {
                'name': 'General Tech',
                'description': 'consumer technology, business tech, and startup news',
                'audience': 'tech enthusiasts and business professionals'
            },
            'ai-ml': {
                'name': 'AI & Machine Learning',
                'description': 'artificial intelligence research, model releases, and AI applications',
                'audience': 'AI researchers, developers, and tech professionals interested in machine learning'
            },
            'devops-platform': {
                'name': 'DevOps & Platform Engineering',
                'description': 'cloud infrastructure, development tools, and platform engineering',
                'audience': 'DevOps engineers, platform engineers, and cloud developers'
            }
        }

        info = category_info.get(category, category_info['general-tech'])
        target_words = BRIEF_GENERATION['target_word_count'][category]
        info_name_lower = info['name'].lower()

        # Format articles for prompt - escape braces in content to prevent format string errors
        def escape_braces(text):
            """Escape curly braces to prevent format string errors"""
            if text is None:
                return "N/A"
            return str(text).replace('{', '{{').replace('}', '}}')

        articles_text = "\n".join([
            f"**{i+1}. {escape_braces(article.get('title', 'No Title'))}** (Source: {escape_braces(article.get('source', 'Unknown'))})\n"
            f"{'Full Content' if article.get('content_extracted') else 'Summary'}: {escape_braces(article.get('full_content') or article.get('summary') or 'No content available')}\n"
            f"Relevance Score: {escape_braces(article.get('final_ranking_score') or article.get('relevance_score') or 'N/A')}/10\n"
            for i, article in enumerate(articles)
        ])

        prompt = f"""Create a {target_words}-word conversational audio brief about {info['description']} for {info['audience']}.

⚠️  CRITICAL: You MUST write EXACTLY {target_words} words (±50 acceptable). This is NOT a summary - it's a full-length podcast brief.

**Date**: {date}
**Category**: {info['name']}
**Target Audience**: {info['audience']}
**REQUIRED LENGTH**: {target_words} words
**Style**: Conversational, engaging, informative (suitable for audio)

**Source Articles**:
{articles_text}

**Requirements**:
- Write exactly {target_words} words (±50 words acceptable) - this is critical for proper audio length
- Use the full article content provided (not just headlines or summaries)
- Conversational tone suitable for audio narration
- Include an engaging introduction that sets the context
- Cover each story in depth with technical details, implications, and context
- Provide comprehensive analysis, not just surface-level summaries
- Explain technical terms and provide background information
- Include a concluding summary of key takeaways and future outlook
- Attribution: Mention key sources naturally in the narrative
- No markdown formatting - write for spoken delivery
- Aim for podcast-quality depth and analysis

**Brief Structure**:
1. Hook/Introduction (100-150 words) - Set context and preview key stories
2. Main stories with analysis (800-900 words) - Cover each story with technical details and context
3. Conclusion and outlook (100-150 words) - Synthesize trends and implications

IMPORTANT: Each main story should receive 100-150 words of coverage. Use the full article content to provide meaningful analysis, technical details, and context. This is a concise yet informative podcast brief.

Begin with something like "Good morning! Here are today's top {info_name_lower} stories..." and write as if speaking directly to the listener.

FINAL REMINDER: Write exactly {target_words} words. Count carefully - this determines the audio length."""

        return prompt

    def _get_system_prompt(self) -> str:
        """Get the system prompt for brief generation"""
        return """You are a professional tech news narrator creating long-form audio briefings. Your role is to:

1. Transform news articles into comprehensive, engaging audio content
2. STRICTLY FOLLOW word count requirements - this is critical for audio timing
3. Use the FULL article content provided to create detailed analysis
4. Explain complex topics in accessible but thorough language
5. Maintain a professional but approachable tone
6. Provide context and connections between stories
7. Write for spoken delivery with natural flow

CRITICAL REQUIREMENT: You MUST write the exact number of words requested (±50 words). Do not write short summaries - this is for professional podcast-length audio content.

Key principles:
- Use natural speech patterns and transitions
- Provide comprehensive coverage of each story with technical details
- Include relevant context, implications, and industry background
- Make technical news accessible but detailed for your audience
- Each story should receive substantial coverage (150-200 words minimum)
- This is NOT a news summary - it's an in-depth audio briefing
- Write as if speaking to an intelligent colleague who wants thorough analysis"""

    def get_brief_by_category(self, category: str, date: str) -> Optional[Dict]:
        """
        Get generated brief for a specific category and date

        Args:
            category: Category name
            date: Date in YYYY-MM-DD format

        Returns:
            Brief data or None if not found
        """
        return self.brief_model.get_brief(category, date)

    def get_all_daily_briefs(self, date: str) -> List[Dict]:
        """
        Get all briefs for a specific date

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            List of brief data
        """
        return self.brief_model.get_briefs_by_date(date)

    def get_brief_generation_stats(self, date: str) -> Dict[str, any]:
        """
        Get brief generation statistics for a specific date

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Brief generation statistics
        """
        job = self.job_model.get_job(date)
        if not job:
            return {'error': 'No brief generation job found for date'}

        engine_data = job.get('engines', {}).get('brief_engine', {})

        return {
            'date': date,
            'status': engine_data.get('status'),
            'briefs_generated': engine_data.get('briefs_generated', 0),
            'total_words': engine_data.get('total_words', 0),
            'token_usage': engine_data.get('token_usage', 0),
            'duration': engine_data.get('duration'),
            'started_at': engine_data.get('started_at'),
            'completed_at': engine_data.get('completed_at'),
            'error_message': engine_data.get('error_message')
        }

    def regenerate_brief(self, category: str, date: str) -> Dict[str, any]:
        """
        Regenerate a brief for a specific category (useful for testing or manual triggers)

        Args:
            category: Category name
            date: Processing date

        Returns:
            Regeneration results
        """
        logger.info(f"Regenerating brief for {category} on {date}")

        # Check budget
        if cost_tracker.is_budget_exceeded(date):
            return {'error': 'Daily budget exceeded'}

        try:
            result = self._generate_category_brief(category, date)

            if result['success']:
                logger.info(f"Successfully regenerated brief for {category}")
            else:
                logger.warning(f"Failed to regenerate brief for {category}: {result.get('error')}")

            return result

        except Exception as e:
            logger.error(f"Error regenerating brief for {category}: {str(e)}")
            return {'error': str(e)}

    def _extract_article_contents_sync(self, articles: List[Dict]) -> List[Dict]:
        """
        Extract full article content for richer brief generation (synchronous version).

        Args:
            articles: List of article metadata from database

        Returns:
            List of articles with full extracted content
        """
        enriched_articles = []

        for article in articles:
            try:
                # Extract full article content
                url = article.get('url')
                if not url:
                    # Keep original if no URL
                    enriched_articles.append(article)
                    continue

                logger.info(f"Extracting content from: {url}")

                # Use the article extractor (synchronous version)
                title, full_content, is_paywalled = self.extractor.extract_article_sync(url)

                if is_paywalled:
                    logger.warning(f"Article is paywalled, using original summary: {url}")
                    enriched_articles.append(article)
                    continue

                if full_content and len(full_content.strip()) > 200:
                    # Create enriched article with full content
                    enriched_article = article.copy()

                    # Clean the content for better TTS
                    cleaned_content = self.extractor.clean_content(full_content)

                    # Truncate if too long to manage token costs
                    max_content_length = BRIEF_GENERATION.get('max_article_content_length', 2000)
                    if len(cleaned_content) > max_content_length:
                        cleaned_content = cleaned_content[:max_content_length] + "..."

                    # Use extracted title if available and better
                    if title and len(title) > len(article.get('title', '')):
                        enriched_article['title'] = title

                    # Replace summary with full content for richer briefs
                    enriched_article['full_content'] = cleaned_content
                    enriched_article['summary'] = cleaned_content[:500] + "..." if len(cleaned_content) > 500 else cleaned_content
                    enriched_article['content_extracted'] = True

                    logger.info(f"Successfully extracted {len(cleaned_content)} chars from {url}")
                    enriched_articles.append(enriched_article)
                else:
                    logger.warning(f"Insufficient content extracted from {url}, using original")
                    enriched_articles.append(article)

            except Exception as e:
                logger.error(f"Failed to extract content from {article.get('url', 'unknown')}: {str(e)}")
                # Fall back to original article data
                enriched_articles.append(article)

        logger.info(f"Article extraction complete: {len([a for a in enriched_articles if a.get('content_extracted')])} of {len(articles)} articles enriched")
        return enriched_articles


def lambda_handler(event, context):
    """
    AWS Lambda handler for brief generation

    Expected event format:
    {
        "date": "2024-01-15",  # optional, defaults to today
        "category": "general-tech"  # optional, if provided only generates for this category
    }
    """
    try:
        date = event.get('date')
        category = event.get('category')

        engine = BriefGenerationEngine()

        if category:
            # Generate brief for specific category only
            result = engine._generate_category_brief(category, date or datetime.utcnow().strftime('%Y-%m-%d'))
            return {
                'statusCode': 200,
                'body': {
                    'category': category,
                    'result': result
                }
            }
        else:
            # Generate all daily briefs
            results = engine.generate_daily_briefs(date)
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
    engine = BriefGenerationEngine()
    results = engine.generate_daily_briefs()
    print(f"Brief generation completed: {results}")