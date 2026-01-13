"""
Briefings API

Public API endpoints for accessing daily tech news briefings
Supports both public access and authenticated user features
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from models import Brief, Job
from services import PipelineOrchestrator
from config import API_SETTINGS, get_all_categories
from utils.logger import get_logger, log_api_request
from utils.metrics import performance_tracker

logger = get_logger(__name__)


class BriefingsAPI:
    """
    Briefings API handler for public and authenticated access
    """

    def __init__(self):
        self.brief_model = Brief()
        self.job_model = Job()
        self.orchestrator = PipelineOrchestrator()

    def get_latest_briefs(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the latest available briefings

        Args:
            user_id: Optional user ID for authenticated features

        Returns:
            Latest briefings response
        """
        try:
            # Get today's date
            today = datetime.utcnow().strftime('%Y-%m-%d')

            # Try today first, then yesterday if no briefs available
            briefs_data = self._get_briefs_for_date(today)
            if not briefs_data['briefs']:
                yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
                briefs_data = self._get_briefs_for_date(yesterday)

            # Add user-specific features if authenticated
            if user_id:
                briefs_data['user_features'] = {
                    'can_download': True,
                    'can_share': True,
                    'listening_history': True
                }

            return {
                'success': True,
                'data': briefs_data
            }

        except Exception as e:
            logger.error(f"Error getting latest briefs: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to fetch latest briefs'
            }

    def get_briefs_by_date(self, date: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get briefings for a specific date

        Args:
            date: Date in YYYY-MM-DD format
            user_id: Optional user ID

        Returns:
            Briefings response for the date
        """
        try:
            briefs_data = self._get_briefs_for_date(date)

            if user_id:
                briefs_data['user_features'] = {
                    'can_download': True,
                    'can_share': True,
                    'listening_history': True
                }

            return {
                'success': True,
                'data': briefs_data
            }

        except Exception as e:
            logger.error(f"Error getting briefs for {date}: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to fetch briefs for {date}'
            }

    def get_brief_by_category(self, category: str, date: str = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a specific brief by category

        Args:
            category: Brief category
            date: Date (defaults to today)
            user_id: Optional user ID

        Returns:
            Brief response
        """
        try:
            if not date:
                date = datetime.utcnow().strftime('%Y-%m-%d')

            brief = self.brief_model.get_brief(category, date)
            if not brief:
                return {
                    'success': False,
                    'error': f'Brief not found for {category} on {date}'
                }

            # Format brief for API response
            brief_data = self._format_brief_for_api(brief)

            if user_id:
                brief_data['user_features'] = {
                    'can_download': True,
                    'can_share': True,
                    'listening_history': True
                }

            return {
                'success': True,
                'data': brief_data
            }

        except Exception as e:
            logger.error(f"Error getting brief {category} for {date}: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to fetch brief'
            }

    def get_available_dates(self, limit: int = 30) -> Dict[str, Any]:
        """
        Get list of dates with available briefings

        Args:
            limit: Maximum number of dates to return

        Returns:
            Available dates response
        """
        try:
            # Get recent jobs to determine available dates
            jobs = self.job_model.get_recent_jobs(limit)

            available_dates = []
            for job in jobs:
                if job.get('status') in ['completed', 'partial']:
                    # Get brief summary for this date
                    summary = self.brief_model.get_daily_briefing_summary(job['date'])
                    if summary['ready_briefs'] > 0:
                        available_dates.append({
                            'date': job['date'],
                            'briefs_available': summary['ready_briefs'],
                            'total_duration': summary['total_duration'],
                            'categories': list(summary['categories'].keys())
                        })

            return {
                'success': True,
                'data': {
                    'available_dates': available_dates,
                    'total_dates': len(available_dates)
                }
            }

        except Exception as e:
            logger.error(f"Error getting available dates: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to fetch available dates'
            }

    def get_pipeline_status(self, date: str = None) -> Dict[str, Any]:
        """
        Get pipeline status for monitoring

        Args:
            date: Date to check (defaults to today)

        Returns:
            Pipeline status response
        """
        try:
            if not date:
                date = datetime.utcnow().strftime('%Y-%m-%d')

            status = self.orchestrator.get_pipeline_status(date)

            return {
                'success': True,
                'data': status
            }

        except Exception as e:
            logger.error(f"Error getting pipeline status: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to fetch pipeline status'
            }

    def _get_briefs_for_date(self, date: str) -> Dict[str, Any]:
        """
        Internal method to get all briefs for a date

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Formatted briefs data
        """
        briefs = self.brief_model.get_briefs_by_date(date)
        ready_briefs = [brief for brief in briefs if brief.get('status') == 'ready']

        # Get pipeline status for this date
        pipeline_status = self.orchestrator.get_pipeline_status(date)

        # Format briefs for API
        formatted_briefs = []
        total_duration = 0

        for brief in ready_briefs:
            formatted_brief = self._format_brief_for_api(brief)
            formatted_briefs.append(formatted_brief)
            total_duration += formatted_brief.get('duration', 0)

        return {
            'date': date,
            'briefs': formatted_briefs,
            'total_briefs': len(formatted_briefs),
            'total_duration': total_duration,
            'pipeline_status': pipeline_status.get('overall_status'),
            'last_updated': max([brief.get('updated_at', '') for brief in ready_briefs]) if ready_briefs else None
        }

    def _format_brief_for_api(self, brief: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a brief for API response

        Args:
            brief: Brief data from database

        Returns:
            API-formatted brief
        """
        return {
            'id': brief['brief_id'],
            'category': brief['category'],
            'date': brief['date'],
            'title': f"{brief['category'].replace('-', ' ').title()} Tech Brief",
            'description': f"Daily {brief['category'].replace('-', ' ')} technology news and updates",
            'duration': brief.get('actual_duration', brief.get('estimated_duration', 0)),
            'word_count': brief.get('word_count', 0),
            'audio_url': brief.get('audio_url'),
            'created_at': brief.get('created_at'),
            'updated_at': brief.get('updated_at'),
            'articles_count': len(brief.get('articles_used', [])),
            'status': brief.get('status'),
            'type': 'news-brief',
            'is_public': True
        }


def lambda_handler(event, context):
    """
    AWS Lambda handler for briefings API

    Supports API Gateway integration with routing
    """
    start_time = datetime.utcnow()

    try:
        # Parse event
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '')
        query_params = event.get('queryStringParameters') or {}
        headers = event.get('headers') or {}
        body = event.get('body')

        # Extract user info from headers (if using Cognito)
        user_id = None
        auth_header = headers.get('Authorization')
        if auth_header:
            # In a real implementation, you'd decode the JWT token here
            # For now, we'll extract from a custom header for demo
            user_id = headers.get('X-User-Id')

        api = BriefingsAPI()
        response_data = None

        # Route requests
        if path == '/briefings' or path == '/briefings/latest':
            if http_method == 'GET':
                response_data = api.get_latest_briefs(user_id)
            else:
                return _error_response(405, 'Method not allowed')

        elif path.startswith('/briefings/date/'):
            date = path.split('/')[-1]
            if http_method == 'GET':
                response_data = api.get_briefs_by_date(date, user_id)
            else:
                return _error_response(405, 'Method not allowed')

        elif path.startswith('/briefings/category/'):
            category = path.split('/')[-1]
            date = query_params.get('date')
            if http_method == 'GET':
                response_data = api.get_brief_by_category(category, date, user_id)
            else:
                return _error_response(405, 'Method not allowed')

        elif path == '/briefings/dates':
            if http_method == 'GET':
                limit = int(query_params.get('limit', 30))
                response_data = api.get_available_dates(limit)
            else:
                return _error_response(405, 'Method not allowed')

        elif path == '/briefings/status':
            if http_method == 'GET':
                date = query_params.get('date')
                response_data = api.get_pipeline_status(date)
            else:
                return _error_response(405, 'Method not allowed')

        else:
            return _error_response(404, 'Endpoint not found')

        # Log API request
        duration = (datetime.utcnow() - start_time).total_seconds()
        status_code = 200 if response_data and response_data.get('success') else 400
        log_api_request(path, http_method, status_code, duration, logger)

        # Return response
        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-User-Id'
            },
            'body': json.dumps(response_data)
        }

    except Exception as e:
        logger.error(f"API handler error: {str(e)}")
        duration = (datetime.utcnow() - start_time).total_seconds()
        log_api_request(path, http_method, 500, duration, logger)

        return _error_response(500, 'Internal server error')


def _error_response(status_code: int, message: str) -> Dict[str, Any]:
    """Create standardized error response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'success': False,
            'error': message
        })
    }


if __name__ == '__main__':
    # For local testing
    api = BriefingsAPI()

    # Test getting latest briefs
    result = api.get_latest_briefs()
    print(json.dumps(result, indent=2))

    # Test getting pipeline status
    status = api.get_pipeline_status()
    print(json.dumps(status, indent=2))