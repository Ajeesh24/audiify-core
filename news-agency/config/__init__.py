"""
News Agency Configuration

This package contains all configuration settings for the news agency system.
"""

from .settings import *
from .rss_feeds import RSS_FEEDS, COLLECTION_SETTINGS, get_feeds_by_category, get_all_feeds, get_high_priority_feeds
from .categories import MAIN_CATEGORIES, SUB_CATEGORIES, RELEVANCE_FACTORS, CLASSIFICATION_PROMPTS, get_category_info, get_category_keywords, get_subcategories, get_all_categories, get_classification_prompt

__all__ = [
    # Settings
    'ENVIRONMENT', 'DEBUG', 'AWS_REGION', 'DYNAMODB_TABLES', 'S3_SETTINGS',
    'OPENAI_SETTINGS', 'AUDIO_SETTINGS', 'PIPELINE_SCHEDULE', 'COST_OPTIMIZATION',
    'BRIEF_GENERATION', 'MONITORING', 'API_SETTINGS', 'LOGGING', 'RELIABILITY',
    'get_setting', 'get_db_table_name', 'get_s3_key', 'is_production', 'is_development',

    # RSS Feeds
    'RSS_FEEDS', 'COLLECTION_SETTINGS', 'get_feeds_by_category', 'get_all_feeds', 'get_high_priority_feeds',

    # Categories
    'MAIN_CATEGORIES', 'SUB_CATEGORIES', 'RELEVANCE_FACTORS', 'CLASSIFICATION_PROMPTS',
    'get_category_info', 'get_category_keywords', 'get_subcategories', 'get_all_categories', 'get_classification_prompt'
]