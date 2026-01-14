"""
DynamoDB Job Model
Tracks daily pipeline execution and engine status
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional, List
import boto3
from boto3.dynamodb.conditions import Key, Attr
import uuid
from enum import Enum


class EngineStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some engines failed but others succeeded


class Job:
    """
    Job model for tracking daily pipeline execution

    Manages the orchestration of all 5 engines and provides
    real-time status tracking for the daily briefing pipeline
    """

    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        # Use environment variable for table name
        import os
        table_name = os.getenv('JOBS_TABLE', 'audifyy-news-jobs-dev')
        self.table = self.dynamodb.Table(table_name)

    def _get_job_key(self, date: str) -> Dict[str, str]:
        """Get the DynamoDB key structure for a job"""
        job_id = f"daily-pipeline-{date}"

        # Get the most recent job for this date to get the exact timestamp
        try:
            response = self.table.query(
                KeyConditionExpression=Key('job_id').eq(job_id),
                ScanIndexForward=False,  # Get latest first
                Limit=1
            )
            items = response.get('Items', [])
            if items:
                return {
                    'job_id': job_id,
                    'timestamp': items[0]['timestamp']
                }
        except:
            pass

        # If no existing job found, this shouldn't happen in update operations
        # but return a structure anyway
        return {
            'job_id': job_id,
            'timestamp': datetime.utcnow().isoformat()
        }

    def _clean_for_dynamodb(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert all float values to Decimal for DynamoDB"""
        cleaned = {}
        for key, value in data.items():
            if isinstance(value, float):
                cleaned[key] = Decimal(str(value))
            elif isinstance(value, dict):
                cleaned[key] = self._clean_for_dynamodb(value)
            elif isinstance(value, list):
                cleaned[key] = [self._clean_for_dynamodb(item) if isinstance(item, dict) else
                              Decimal(str(item)) if isinstance(item, float) else item for item in value]
            else:
                cleaned[key] = value
        return cleaned

    def create_daily_job(self, date: str) -> Dict[str, Any]:
        """
        Create a new daily job entry

        Args:
            date: Job date in YYYY-MM-DD format

        Returns:
            Created job data
        """
        # Create predictable job_id based on date for easy retrieval
        job_id = f"daily-pipeline-{date}"
        now = datetime.utcnow().isoformat()

        job_data = {
            'job_id': job_id,
            'timestamp': now,  # Range key for the table
            'date': date,  # Keep date for querying and logic
            'status': JobStatus.PENDING.value,
            'created_at': now,
            'updated_at': now,
            'started_at': None,
            'completed_at': None,
            'engines': {
                'rss_engine': {
                    'status': EngineStatus.PENDING.value,
                    'started_at': None,
                    'completed_at': None,
                    'duration': None,
                    'articles_collected': 0,
                    'sources_processed': 0,
                    'error_message': None,
                    'scheduled_time': '05:00'  # UTC
                },
                'categorization_engine': {
                    'status': EngineStatus.PENDING.value,
                    'started_at': None,
                    'completed_at': None,
                    'duration': None,
                    'articles_categorized': 0,
                    'token_usage': 0,
                    'error_message': None,
                    'scheduled_time': '05:15'
                },
                'ranking_engine': {
                    'status': EngineStatus.PENDING.value,
                    'started_at': None,
                    'completed_at': None,
                    'duration': None,
                    'articles_ranked': 0,
                    'error_message': None,
                    'scheduled_time': '05:25'
                },
                'brief_engine': {
                    'status': EngineStatus.PENDING.value,
                    'started_at': None,
                    'completed_at': None,
                    'duration': None,
                    'briefs_generated': 0,
                    'total_words': 0,
                    'token_usage': 0,
                    'error_message': None,
                    'scheduled_time': '05:35'
                },
                'audio_engine': {
                    'status': EngineStatus.PENDING.value,
                    'started_at': None,
                    'completed_at': None,
                    'duration': None,
                    'audio_files_generated': 0,
                    'total_audio_duration': 0,
                    'error_message': None,
                    'scheduled_time': '06:00'
                }
            },
            'metrics': {
                'total_articles': 0,
                'successful_briefs': 0,
                'total_cost_estimate': 0.0,
                'token_usage_total': 0,
                'pipeline_duration': None
            },
            'error_summary': []
        }

        try:
            # Check if job already exists for this date
            existing_job = self.get_job(date)
            if existing_job:
                return existing_job

            cleaned_data = self._clean_for_dynamodb(job_data)
            self.table.put_item(Item=cleaned_data)
            return job_data

        except Exception as e:
            print(f"Error creating job: {e}")
            return self.get_job(date) or job_data

    def get_job(self, date: str) -> Optional[Dict[str, Any]]:
        """Get job by date"""
        try:
            # Use predictable job_id and query with both keys
            job_id = f"daily-pipeline-{date}"

            # Since we need both keys for DynamoDB query, we'll scan for the latest job for this date
            response = self.table.query(
                KeyConditionExpression=Key('job_id').eq(job_id),
                ScanIndexForward=False,  # Get latest first
                Limit=1
            )

            items = response.get('Items', [])
            return items[0] if items else None
        except Exception as e:
            print(f"Error fetching job for date {date}: {e}")
            return None

    def get_job_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID"""
        try:
            response = self.table.query(
                IndexName='job_id-index',
                KeyConditionExpression=Key('job_id').eq(job_id)
            )
            items = response.get('Items', [])
            return items[0] if items else None
        except Exception as e:
            print(f"Error fetching job {job_id}: {e}")
            return None

    def start_engine(self, date: str, engine_name: str) -> bool:
        """Mark an engine as started"""
        now = datetime.utcnow().isoformat()

        try:
            # Also update job status to running if not already
            job = self.get_job(date)
            job_status_update = ""
            if job and job.get('status') == JobStatus.PENDING.value:
                job_status_update = ", #status = :job_status, started_at = :started_at"

            update_expression = f"""
                SET engines.{engine_name}.#status = :engine_status,
                    engines.{engine_name}.started_at = :started_at,
                    updated_at = :updated_at
                    {job_status_update}
            """

            expression_values = {
                ':engine_status': EngineStatus.RUNNING.value,
                ':started_at': now,
                ':updated_at': now
            }

            expression_names = {'#status': 'status'}

            if job_status_update:
                expression_values[':job_status'] = JobStatus.RUNNING.value

            job_key = self._get_job_key(date)
            self.table.update_item(
                Key=job_key,
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names
            )
            return True
        except Exception as e:
            print(f"Error starting engine {engine_name} for {date}: {e}")
            return False

    def complete_engine(self, date: str, engine_name: str, metrics: Dict[str, Any]) -> bool:
        """Mark an engine as completed with metrics"""
        now = datetime.utcnow().isoformat()

        try:
            # Calculate duration if start time exists
            job = self.get_job(date)
            duration = None
            if job and job.get('engines', {}).get(engine_name, {}).get('started_at'):
                start_time = datetime.fromisoformat(job['engines'][engine_name]['started_at'])
                end_time = datetime.fromisoformat(now)
                duration = int((end_time - start_time).total_seconds())

            # Build update expression for engine metrics
            update_expression = f"""
                SET engines.{engine_name}.#status = :status,
                    engines.{engine_name}.completed_at = :completed_at,
                    engines.{engine_name}.#duration = :duration,
                    updated_at = :updated_at
            """

            expression_values = {
                ':status': EngineStatus.COMPLETED.value,
                ':completed_at': now,
                ':duration': duration,
                ':updated_at': now
            }

            expression_names = {'#status': 'status', '#duration': 'duration'}

            # Add metrics to update expression
            for key, value in metrics.items():
                if key not in ['status', 'completed_at', 'duration']:
                    # Use expression attribute names for all metric keys to avoid reserved keyword issues
                    attr_name = f"#metric_{key}"
                    update_expression += f", engines.{engine_name}.{attr_name} = :{key}"
                    # Clean the value for DynamoDB
                    cleaned_value = Decimal(str(value)) if isinstance(value, float) else value
                    expression_values[f":{key}"] = cleaned_value
                    expression_names[attr_name] = key

            job_key = self._get_job_key(date)
            self.table.update_item(
                Key=job_key,
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names
            )

            # Check if all engines are complete and update job status
            self._check_job_completion(date)
            return True
        except Exception as e:
            print(f"Error completing engine {engine_name} for {date}: {e}")
            return False

    def fail_engine(self, date: str, engine_name: str, error_message: str) -> bool:
        """Mark an engine as failed"""
        now = datetime.utcnow().isoformat()

        try:
            job = self.get_job(date)
            duration = None
            if job and job.get('engines', {}).get(engine_name, {}).get('started_at'):
                start_time = datetime.fromisoformat(job['engines'][engine_name]['started_at'])
                end_time = datetime.fromisoformat(now)
                duration = int((end_time - start_time).total_seconds())

            self.table.update_item(
                Key=self._get_job_key(date),
                UpdateExpression=f"""
                    SET engines.{engine_name}.#status = :status,
                        engines.{engine_name}.completed_at = :completed_at,
                        engines.{engine_name}.#duration = :duration,
                        engines.{engine_name}.error_message = :error_message,
                        updated_at = :updated_at
                """,
                ExpressionAttributeValues={
                    ':status': EngineStatus.FAILED.value,
                    ':completed_at': now,
                    ':duration': duration,
                    ':error_message': error_message,
                    ':updated_at': now
                },
                ExpressionAttributeNames={'#status': 'status', '#duration': 'duration'}
            )

            # Add error to summary
            self._add_error_to_summary(date, engine_name, error_message)

            # Check job completion (might be partial failure)
            self._check_job_completion(date)
            return True
        except Exception as e:
            print(f"Error marking engine {engine_name} as failed for {date}: {e}")
            return False

    def _check_job_completion(self, date: str):
        """Check if all engines are complete and update job status accordingly"""
        job = self.get_job(date)
        if not job:
            return

        engines = job.get('engines', {})
        completed_engines = 0
        failed_engines = 0
        total_engines = len(engines)

        for engine_data in engines.values():
            status = engine_data.get('status')
            if status == EngineStatus.COMPLETED.value:
                completed_engines += 1
            elif status == EngineStatus.FAILED.value:
                failed_engines += 1

        # Determine final job status
        if completed_engines == total_engines:
            final_status = JobStatus.COMPLETED.value
        elif completed_engines + failed_engines == total_engines:
            if failed_engines > 0:
                final_status = JobStatus.PARTIAL.value if completed_engines > 0 else JobStatus.FAILED.value
            else:
                final_status = JobStatus.COMPLETED.value
        else:
            return  # Still running

        # Calculate total pipeline duration
        started_at = job.get('started_at')
        pipeline_duration = None
        if started_at:
            start_time = datetime.fromisoformat(started_at)
            end_time = datetime.utcnow()
            pipeline_duration = int((end_time - start_time).total_seconds())

        # Update job status
        now = datetime.utcnow().isoformat()
        self.table.update_item(
            Key=self._get_job_key(date),
            UpdateExpression="""
                SET #status = :status,
                    completed_at = :completed_at,
                    #metrics.pipeline_duration = :pipeline_duration,
                    updated_at = :updated_at
            """,
            ExpressionAttributeValues={
                ':status': final_status,
                ':completed_at': now,
                ':pipeline_duration': pipeline_duration,
                ':updated_at': now
            },
            ExpressionAttributeNames={'#status': 'status', '#metrics': 'metrics'}
        )

    def _add_error_to_summary(self, date: str, engine_name: str, error_message: str):
        """Add error to job error summary"""
        job = self.get_job(date)
        if job:
            error_summary = job.get('error_summary', [])
            error_summary.append({
                'engine': engine_name,
                'error': error_message,
                'timestamp': datetime.utcnow().isoformat()
            })

            self.table.update_item(
                Key=self._get_job_key(date),
                UpdateExpression="SET error_summary = :error_summary",
                ExpressionAttributeValues={':error_summary': error_summary}
            )

    def get_recent_jobs(self, limit: int = 7) -> List[Dict[str, Any]]:
        """Get recent jobs for monitoring dashboard"""
        try:
            response = self.table.scan(
                Limit=limit * 2  # Get more than needed to account for filtering
            )

            jobs = response.get('Items', [])
            # Sort by date descending and limit
            jobs.sort(key=lambda x: x.get('date', ''), reverse=True)
            return jobs[:limit]
        except Exception as e:
            print(f"Error fetching recent jobs: {e}")
            return []

    def get_pipeline_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get pipeline performance statistics"""
        recent_jobs = self.get_recent_jobs(days)

        stats = {
            'total_jobs': len(recent_jobs),
            'successful_jobs': len([j for j in recent_jobs if j.get('status') == JobStatus.COMPLETED.value]),
            'failed_jobs': len([j for j in recent_jobs if j.get('status') == JobStatus.FAILED.value]),
            'partial_jobs': len([j for j in recent_jobs if j.get('status') == JobStatus.PARTIAL.value]),
            'avg_pipeline_duration': 0,
            'total_articles_processed': 0,
            'total_briefs_generated': 0,
            'engine_reliability': {}
        }

        if recent_jobs:
            # Calculate averages
            durations = [j.get('metrics', {}).get('pipeline_duration', 0) for j in recent_jobs if j.get('metrics', {}).get('pipeline_duration')]
            stats['avg_pipeline_duration'] = sum(durations) / len(durations) if durations else 0

            # Sum totals
            stats['total_articles_processed'] = sum(j.get('metrics', {}).get('total_articles', 0) for j in recent_jobs)
            stats['total_briefs_generated'] = sum(j.get('metrics', {}).get('successful_briefs', 0) for j in recent_jobs)

            # Engine reliability
            engine_names = ['rss_engine', 'categorization_engine', 'ranking_engine', 'brief_engine', 'audio_engine']
            for engine in engine_names:
                successful = sum(1 for j in recent_jobs if j.get('engines', {}).get(engine, {}).get('status') == EngineStatus.COMPLETED.value)
                stats['engine_reliability'][engine] = (successful / len(recent_jobs)) * 100 if recent_jobs else 0

        return stats