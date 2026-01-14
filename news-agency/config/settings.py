"""
News Agency Settings

Central configuration for the entire news pipeline system
Environment variables and service settings
"""

import os
from typing import Dict, Any

# Environment settings
ENVIRONMENT = os.getenv('NEWS_AGENCY_ENV', 'development')  # development, staging, production
DEBUG = os.getenv('DEBUG', 'true').lower() == 'true'

# AWS Settings
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')

# DynamoDB Table Names
DYNAMODB_TABLES = {
    'articles': os.getenv('ARTICLES_TABLE', 'audifyy-articles-dev'),
    'briefs': os.getenv('BRIEFS_TABLE', 'audifyy-briefs-dev'),
    'jobs': os.getenv('JOBS_TABLE', 'audifyy-news-jobs-dev')
}

# S3 Storage Settings
S3_SETTINGS = {
    'bucket_name': os.getenv('AUDIO_BUCKET', 'audifyy-news-audio-dev'),
    'audio_prefix': 'audio/',
    'archive_prefix': 'archive/',
    'region': AWS_REGION
}

# OpenAI API Settings (for LLM operations)
OPENAI_SETTINGS = {
    'api_key': os.getenv('OPENAI_API_KEY'),
    'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),  # Cost-optimized model
    'max_tokens': int(os.getenv('OPENAI_MAX_TOKENS', '1000')),
    'temperature': float(os.getenv('OPENAI_TEMPERATURE', '0.3')),
    'timeout': int(os.getenv('OPENAI_TIMEOUT', '30'))
}

# Audio Generation Settings (ElevenLabs or AWS Polly)
AUDIO_SETTINGS = {
    'provider': os.getenv('AUDIO_PROVIDER', 'elevenlabs'),  # elevenlabs or aws_polly
    'elevenlabs_api_key': os.getenv('ELEVENLABS_API_KEY'),
    'voice_id': os.getenv('ELEVENLABS_VOICE_ID', 'pNInz6obpgDQGcFmaJgB'),  # Adam voice
    'model': os.getenv('ELEVENLABS_MODEL', 'eleven_multilingual_v2'),
    'stability': float(os.getenv('ELEVENLABS_STABILITY', '0.5')),
    'similarity_boost': float(os.getenv('ELEVENLABS_SIMILARITY', '0.8')),
    'optimize_streaming_latency': int(os.getenv('ELEVENLABS_OPTIMIZE', '0')),
    'output_format': os.getenv('AUDIO_OUTPUT_FORMAT', 'mp3_44100_128')
}

# Pipeline Scheduling (UTC times)
PIPELINE_SCHEDULE = {
    'rss_collection': '05:00',        # 5:00 AM UTC
    'categorization': '05:15',        # 5:15 AM UTC
    'ranking': '05:25',               # 5:25 AM UTC
    'brief_generation': '05:35',      # 5:35 AM UTC
    'audio_generation': '06:00',      # 6:00 AM UTC
    'pipeline_complete': '06:30'      # 6:30 AM UTC (target)
}

# Cost Optimization Settings
COST_OPTIMIZATION = {
    'target_daily_cost': 0.50,        # Target: < $0.50/day
    'max_articles_per_category': 50,   # Limit articles processed per category
    'token_budget_per_day': 10000,    # 10K tokens/day budget
    'enable_token_tracking': True,
    'fallback_to_free_tier': True,    # Use AWS Polly if ElevenLabs budget exceeded
    'cache_llm_responses': True,      # Cache responses for duplicate articles
    'cleanup_old_data_days': 7       # Keep data for 7 days max
}

# Brief Generation Settings
BRIEF_GENERATION = {
    'target_word_count': {
        'general-tech': 1200,      # ~7-8 minutes
        'ai-ml': 1200,            # ~7-8 minutes
        'devops-platform': 1200   # ~7-8 minutes
    },
    'max_articles_per_brief': 8,   # Maximum articles to include in one brief
    'min_articles_per_brief': 3,   # Minimum articles needed to generate brief
    'max_article_content_length': 2000,  # Max chars per article to control token costs
    'include_source_attribution': True,
    'format_style': 'conversational',  # conversational, formal, casual
    'include_timestamps': False,
    'add_intro_outro': True
}

# Monitoring and Alerting
MONITORING = {
    'enable_cloudwatch_metrics': True,
    'enable_error_notifications': True,
    'sns_topic_arn': os.getenv('SNS_TOPIC_ARN'),
    'alert_on_pipeline_failure': True,
    'alert_on_cost_threshold': True,
    'cost_alert_threshold': 0.40,     # Alert at 80% of daily budget
    'performance_metrics_retention_days': 30
}

# API Settings
API_SETTINGS = {
    'enable_public_api': os.getenv('ENABLE_PUBLIC_API', 'true').lower() == 'true',
    'api_rate_limit': int(os.getenv('API_RATE_LIMIT', '100')),  # requests per minute
    'require_api_key': os.getenv('REQUIRE_API_KEY', 'false').lower() == 'true',
    'cors_origins': os.getenv('CORS_ORIGINS', '*').split(','),
    'cache_brief_responses': True,
    'cache_ttl_seconds': 3600  # 1 hour
}

# Logging Configuration
LOGGING = {
    'level': os.getenv('LOG_LEVEL', 'INFO'),
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'enable_cloudwatch_logs': ENVIRONMENT == 'production',
    'log_group_name': f'/aws/lambda/news-agency-{ENVIRONMENT}',
    'enable_structured_logging': True
}

# Retry and Circuit Breaker Settings
RELIABILITY = {
    'max_retries': 3,
    'base_delay': 1,              # Base delay for exponential backoff
    'max_delay': 60,              # Maximum delay between retries
    'circuit_breaker_threshold': 5, # Failures before circuit opens
    'circuit_breaker_timeout': 300, # Time before attempting reset (seconds)
    'request_timeout': 30,        # Default timeout for external requests
    'enable_circuit_breaker': True
}

# Development/Testing Settings
if ENVIRONMENT == 'development':
    # Override some settings for local development
    COST_OPTIMIZATION['token_budget_per_day'] = 1000  # Smaller budget for dev
    BRIEF_GENERATION['target_word_count'] = {
        'general-tech': 300,      # Shorter briefs for testing
        'ai-ml': 300,
        'devops-platform': 300
    }
    COST_OPTIMIZATION['max_articles_per_category'] = 10  # Fewer articles in dev

def get_setting(key: str, default: Any = None) -> Any:
    """
    Get a setting value with optional default

    Args:
        key: Setting key in dot notation (e.g., 'openai.model')
        default: Default value if setting not found

    Returns:
        Setting value or default
    """
    keys = key.split('.')
    value = globals()

    try:
        for k in keys:
            value = value[k]
        return value
    except (KeyError, TypeError):
        return default

def get_db_table_name(table_type: str) -> str:
    """
    Get DynamoDB table name for a given type

    Args:
        table_type: Type of table (articles, briefs, jobs)

    Returns:
        Full table name
    """
    return DYNAMODB_TABLES.get(table_type, f'news_{table_type}')

def get_s3_key(file_type: str, filename: str) -> str:
    """
    Generate S3 key for a file

    Args:
        file_type: Type of file (audio, archive)
        filename: Name of the file

    Returns:
        S3 key path
    """
    prefix = S3_SETTINGS.get(f'{file_type}_prefix', '')
    return f"{prefix}{filename}"

def is_production() -> bool:
    """Check if running in production environment"""
    return ENVIRONMENT == 'production'

def is_development() -> bool:
    """Check if running in development environment"""
    return ENVIRONMENT == 'development'