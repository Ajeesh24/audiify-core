"""
Internal API

Internal endpoints for pipeline management and administration
Used by EventBridge, monitoring systems, and admin tools
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from models import Brief, Job, Article
from services import PipelineOrchestrator, storage_service
from engines import (
    RSSEngine, CategorizationEngine, RankingEngine,
    BriefGenerationEngine, AudioGenerationEngine
)
from utils.logger import get_logger, log_api_request
from utils.metrics import cost_tracker, performance_tracker

logger = get_logger(__name__)


class InternalAPI:
    """
    Internal API handler for pipeline management and monitoring
    """

    def __init__(self):
        self.orchestrator = PipelineOrchestrator()
        self.brief_model = Brief()
        self.job_model = Job()
        self.article_model = Article()

        # Engine instances for direct control
        self.engines = {
            'rss': RSSEngine(),
            'categorization': CategorizationEngine(),
            'ranking': RankingEngine(),
            'brief': BriefGenerationEngine(),
            'audio': AudioGenerationEngine()
        }

    def trigger_pipeline(self, date: str = None, stages: List[str] = None) -> Dict[str, Any]:
        """
        Trigger pipeline execution (used by EventBridge scheduler)

        Args:
            date: Date to process (defaults to today)
            stages: Specific stages to run (defaults to all)

        Returns:
            Pipeline execution results
        """
        try:
            logger.info(f"Pipeline triggered for date: {date}, stages: {stages}")
            results = self.orchestrator.run_daily_pipeline(date, stages)

            return {
                'success': True,
                'data': results
            }

        except Exception as e:
            logger.error(f"Pipeline trigger error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def trigger_engine(self, engine: str, date: str = None, **kwargs) -> Dict[str, Any]:
        """
        Trigger a specific engine manually

        Args:
            engine: Engine name (rss, categorization, ranking, brief, audio)
            date: Processing date
            **kwargs: Additional engine parameters

        Returns:
            Engine execution results
        """
        try:
            if engine not in self.engines:
                return {
                    'success': False,
                    'error': f'Unknown engine: {engine}'
                }

            if not date:
                date = datetime.utcnow().strftime('%Y-%m-%d')

            logger.info(f"Triggering {engine} engine for {date}")

            engine_instance = self.engines[engine]

            # Execute appropriate engine method
            if engine == 'rss':
                result = engine_instance.collect_daily_articles(date)
            elif engine == 'categorization':
                result = engine_instance.categorize_daily_articles(date)
            elif engine == 'ranking':
                result = engine_instance.rank_daily_articles(date)
            elif engine == 'brief':
                result = engine_instance.generate_daily_briefs(date)
            elif engine == 'audio':
                result = engine_instance.generate_daily_audio(date)
            else:
                return {
                    'success': False,
                    'error': f'Engine method not implemented: {engine}'
                }

            return {
                'success': True,
                'engine': engine,
                'date': date,
                'data': result
            }

        except Exception as e:
            logger.error(f"Engine {engine} trigger error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_system_health(self) -> Dict[str, Any]:
        """
        Get comprehensive system health status

        Returns:
            System health information
        """
        try:
            # Get pipeline statistics
            pipeline_stats = self.job_model.get_pipeline_stats(7)

            # Get cost information
            today = datetime.utcnow().strftime('%Y-%m-%d')
            daily_cost = cost_tracker.get_daily_cost(today)
            daily_tokens = cost_tracker.get_daily_tokens(today)
            budget_remaining = cost_tracker.get_remaining_budget(today)

            # Get storage statistics
            storage_stats = storage_service.get_storage_stats()

            # Get recent job status
            recent_jobs = self.job_model.get_recent_jobs(3)

            health_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'overall_status': 'healthy',  # Will be calculated based on metrics
                'pipeline': {
                    'stats': pipeline_stats,
                    'recent_jobs': recent_jobs
                },
                'cost': {
                    'daily_cost_usd': daily_cost,
                    'budget_remaining_usd': budget_remaining,
                    'token_usage': daily_tokens,
                    'budget_utilization_percent': (daily_cost / 0.50) * 100
                },
                'storage': storage_stats,
                'services': {
                    'database': self._check_database_health(),
                    'storage': self._check_storage_health(),
                    'external_apis': self._check_external_apis_health()
                }
            }

            # Determine overall health status
            health_data['overall_status'] = self._calculate_overall_health(health_data)

            return {
                'success': True,
                'data': health_data
            }

        except Exception as e:
            logger.error(f"Health check error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'overall_status': 'unhealthy'
            }

    def get_metrics(self, days: int = 7) -> Dict[str, Any]:
        """
        Get system metrics for monitoring dashboard

        Args:
            days: Number of days of metrics to return

        Returns:
            System metrics
        """
        try:
            # Pipeline metrics
            pipeline_stats = self.job_model.get_pipeline_stats(days)

            # Cost metrics by day
            cost_metrics = []
            for i in range(days):
                date = (datetime.utcnow() - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
                daily_cost = cost_tracker.get_daily_cost(date)
                daily_tokens = cost_tracker.get_daily_tokens(date)

                cost_metrics.append({
                    'date': date,
                    'cost_usd': daily_cost,
                    'tokens': daily_tokens['total_tokens'],
                    'budget_utilization': (daily_cost / 0.50) * 100
                })

            # Performance metrics
            performance_metrics = {
                'avg_pipeline_duration': pipeline_stats.get('avg_pipeline_duration', 0),
                'success_rate': (pipeline_stats.get('successful_jobs', 0) / max(pipeline_stats.get('total_jobs', 1), 1)) * 100,
                'engine_reliability': pipeline_stats.get('engine_reliability', {})
            }

            # Content metrics
            content_metrics = self._get_content_metrics(days)

            return {
                'success': True,
                'data': {
                    'period_days': days,
                    'pipeline': pipeline_stats,
                    'cost': cost_metrics,
                    'performance': performance_metrics,
                    'content': content_metrics
                }
            }

        except Exception as e:
            logger.error(f"Metrics error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def cleanup_old_data(self, days_to_keep: int = 7) -> Dict[str, Any]:
        """
        Cleanup old data to manage storage costs

        Args:
            days_to_keep: Number of days of data to retain

        Returns:
            Cleanup results
        """
        try:
            results = {
                'storage_cleanup': storage_service.cleanup_old_files(days_to_keep),
                'database_cleanup': self._cleanup_old_database_records(days_to_keep)
            }

            return {
                'success': True,
                'data': results
            }

        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _check_database_health(self) -> Dict[str, Any]:
        """Check DynamoDB health"""
        try:
            # Try to query a recent job
            recent_jobs = self.job_model.get_recent_jobs(1)
            return {
                'status': 'healthy',
                'last_check': datetime.utcnow().isoformat(),
                'recent_jobs_count': len(recent_jobs)
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'last_check': datetime.utcnow().isoformat()
            }

    def _check_storage_health(self) -> Dict[str, Any]:
        """Check S3 storage health"""
        try:
            storage_stats = storage_service.get_storage_stats()
            return {
                'status': 'healthy',
                'last_check': datetime.utcnow().isoformat(),
                'total_files': storage_stats.get('total_files', 0)
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'last_check': datetime.utcnow().isoformat()
            }

    def _check_external_apis_health(self) -> Dict[str, Any]:
        """Check external API health (simplified)"""
        return {
            'openai': {'status': 'unknown', 'last_check': None},
            'elevenlabs': {'status': 'unknown', 'last_check': None},
            'rss_feeds': {'status': 'unknown', 'last_check': None}
        }

    def _calculate_overall_health(self, health_data: Dict[str, Any]) -> str:
        """Calculate overall system health"""
        # Check critical services
        db_healthy = health_data['services']['database']['status'] == 'healthy'
        storage_healthy = health_data['services']['storage']['status'] == 'healthy'

        # Check budget
        budget_ok = health_data['cost']['budget_utilization_percent'] < 90

        # Check recent pipeline success
        recent_success = health_data['pipeline']['stats']['success_rate'] > 50 if 'success_rate' in health_data['pipeline']['stats'] else True

        if db_healthy and storage_healthy and budget_ok and recent_success:
            return 'healthy'
        elif db_healthy and storage_healthy:
            return 'degraded'
        else:
            return 'unhealthy'

    def _get_content_metrics(self, days: int) -> Dict[str, Any]:
        """Get content generation metrics"""
        try:
            total_briefs = 0
            total_articles = 0

            for i in range(days):
                date = (datetime.utcnow() - datetime.timedelta(days=i)).strftime('%Y-%m-%d')

                # Count briefs
                briefs = self.brief_model.get_briefs_by_date(date)
                total_briefs += len([b for b in briefs if b.get('status') == 'ready'])

                # Count articles
                articles = self.article_model.get_articles_by_date(date)
                total_articles += len(articles)

            return {
                'total_briefs_generated': total_briefs,
                'total_articles_processed': total_articles,
                'avg_briefs_per_day': total_briefs / days,
                'avg_articles_per_day': total_articles / days
            }

        except Exception as e:
            logger.error(f"Content metrics error: {str(e)}")
            return {}

    def _cleanup_old_database_records(self, days_to_keep: int) -> Dict[str, Any]:
        """Cleanup old database records"""
        # This would implement cleanup of old articles and jobs
        # For now, return placeholder
        return {
            'articles_deleted': 0,
            'jobs_deleted': 0,
            'message': 'Database cleanup not implemented yet'
        }


def lambda_handler(event, context):
    """
    AWS Lambda handler for internal API

    Handles EventBridge triggers and admin requests
    """
    start_time = datetime.utcnow()

    try:
        # Handle EventBridge events (scheduled pipeline triggers)
        if 'source' in event and event['source'] == 'aws.events':
            # This is an EventBridge scheduled trigger
            detail = event.get('detail', {})
            action = detail.get('action', 'trigger_pipeline')
            date = detail.get('date')
            stages = detail.get('stages')

            api = InternalAPI()

            if action == 'trigger_pipeline':
                result = api.trigger_pipeline(date, stages)
            else:
                result = {'success': False, 'error': f'Unknown EventBridge action: {action}'}

            return result

        # Handle API Gateway requests
        http_method = event.get('httpMethod', 'POST')
        path = event.get('path', '')
        body = json.loads(event.get('body', '{}'))

        api = InternalAPI()
        response_data = None

        # Route internal API requests
        if path == '/internal/pipeline/trigger':
            if http_method == 'POST':
                date = body.get('date')
                stages = body.get('stages')
                response_data = api.trigger_pipeline(date, stages)

        elif path == '/internal/engine/trigger':
            if http_method == 'POST':
                engine = body.get('engine')
                date = body.get('date')
                response_data = api.trigger_engine(engine, date, **body)

        elif path == '/internal/health':
            if http_method == 'GET':
                response_data = api.get_system_health()

        elif path == '/internal/metrics':
            if http_method == 'GET':
                days = int(event.get('queryStringParameters', {}).get('days', 7))
                response_data = api.get_metrics(days)

        elif path == '/internal/cleanup':
            if http_method == 'POST':
                days_to_keep = body.get('days_to_keep', 7)
                response_data = api.cleanup_old_data(days_to_keep)

        else:
            response_data = {
                'success': False,
                'error': f'Unknown internal endpoint: {path}'
            }

        # Log API request
        duration = (datetime.utcnow() - start_time).total_seconds()
        status_code = 200 if response_data and response_data.get('success') else 400
        log_api_request(path, http_method, status_code, duration, logger)

        return {
            'statusCode': status_code,
            'body': json.dumps(response_data)
        }

    except Exception as e:
        logger.error(f"Internal API error: {str(e)}")
        duration = (datetime.utcnow() - start_time).total_seconds()
        log_api_request(event.get('path', '/internal'), event.get('httpMethod', 'POST'), 500, duration, logger)

        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': 'Internal server error'
            })
        }


if __name__ == '__main__':
    # For local testing
    api = InternalAPI()

    # Test system health
    health = api.get_system_health()
    print(json.dumps(health, indent=2))