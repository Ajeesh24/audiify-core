import os
import json
import boto3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class JobStorage:
    """DynamoDB-based job storage for persistent job tracking."""

    def __init__(self):
        """Initialize DynamoDB client and table."""
        self.dynamodb = boto3.resource('dynamodb')
        self.table_name = os.environ.get('DYNAMODB_TABLE_NAME')
        if not self.table_name:
            raise ValueError("DYNAMODB_TABLE_NAME environment variable not set")

        self.table = self.dynamodb.Table(self.table_name)

        # SQS client for sending background jobs
        self.sqs = boto3.client('sqs')
        self.queue_url = os.environ.get('SQS_QUEUE_URL')
        if not self.queue_url:
            raise ValueError("SQS_QUEUE_URL environment variable not set")

    def create_job(self, job_id: str, request_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Create a new job and send to SQS for background processing."""
        try:
            # Calculate TTL (jobs expire after 7 days)
            ttl = int((datetime.now() + timedelta(days=7)).timestamp())

            job_data = {
                'job_id': job_id,
                'user_id': user_id,  # Associate job with user
                'status': 'started',
                'progress': 0,
                'step': 'Queued for processing...',
                'result': None,
                'error': None,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'ttl': ttl
            }

            # Store job in DynamoDB
            self.table.put_item(Item=job_data)

            # Send job to SQS for background processing
            message_body = {
                'job_id': job_id,
                'user_id': user_id,  # Include user_id in SQS message
                'request_data': request_data
            }

            self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message_body)
            )

            logger.info(f"Created job {job_id} for user {user_id} and queued for processing")
            return job_data

        except Exception as e:
            logger.error(f"Failed to create job {job_id}: {str(e)}")
            raise

    def get_job(self, job_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get job status from DynamoDB with optional user verification."""
        try:
            response = self.table.get_item(Key={'job_id': job_id})
            job_data = response.get('Item')

            # If user_id is provided, verify the job belongs to this user
            if job_data and user_id and job_data.get('user_id') != user_id:
                logger.warning(f"User {user_id} attempted to access job {job_id} belonging to {job_data.get('user_id')}")
                return None

            return job_data
        except Exception as e:
            logger.error(f"Failed to get job {job_id}: {str(e)}")
            return None

    def get_user_jobs(self, user_id: str, limit: int = 50, last_evaluated_key: Optional[str] = None) -> Dict[str, Any]:
        """Get all jobs for a specific user, ordered by creation date (newest first)."""
        try:
            # First, query the GSI to get job IDs and pagination metadata
            query_kwargs = {
                'IndexName': 'user-created-index',
                'KeyConditionExpression': '#user_id = :user_id',
                'ExpressionAttributeNames': {'#user_id': 'user_id'},
                'ExpressionAttributeValues': {':user_id': user_id},
                'Limit': limit,
                'ScanIndexForward': False,  # Most recent first
                'ProjectionExpression': 'job_id, created_at'  # Only get what we need from GSI
            }

            # Handle pagination - DynamoDB expects full key structure
            if last_evaluated_key:
                try:
                    # Parse the last_evaluated_key if it's a string
                    if isinstance(last_evaluated_key, str):
                        query_kwargs['ExclusiveStartKey'] = {
                            'user_id': user_id,
                            'created_at': last_evaluated_key
                        }
                    elif isinstance(last_evaluated_key, dict):
                        # Use the key as-is if it's already a dict
                        query_kwargs['ExclusiveStartKey'] = last_evaluated_key
                    else:
                        logger.warning(f"Invalid last_evaluated_key format: {type(last_evaluated_key)}")
                except Exception as e:
                    logger.warning(f"Failed to parse pagination key: {str(e)}, ignoring pagination")

            gsi_response = self.table.query(**query_kwargs)
            gsi_items = gsi_response.get('Items', [])

            # If no jobs found, return empty result
            if not gsi_items:
                return {
                    'jobs': [],
                    'last_evaluated_key': None,
                    'count': 0
                }

            # Now fetch full job details from main table for each job_id
            full_jobs = []
            for gsi_item in gsi_items:
                job_id = gsi_item['job_id']
                full_job = self.get_job(job_id, user_id)  # This gets ALL attributes from main table
                if full_job:  # Only include jobs that still exist and belong to user
                    full_jobs.append(full_job)

            return {
                'jobs': full_jobs,
                'last_evaluated_key': gsi_response.get('LastEvaluatedKey'),  # Return GSI pagination key
                'count': len(full_jobs)
            }

        except Exception as e:
            logger.error(f"Failed to get jobs for user {user_id}: {str(e)}")
            return {'jobs': [], 'last_evaluated_key': None, 'count': 0}

    def get_user_job_by_url(self, user_id: str, url: str) -> Optional[Dict[str, Any]]:
        """Check if user has already processed a specific URL."""
        try:
            # Get all user jobs and filter by URL (could be optimized with GSI if needed)
            user_jobs = self.get_user_jobs(user_id, limit=100)

            for job in user_jobs['jobs']:
                if job.get('result', {}).get('article', {}).get('url') == url:
                    return job

            return None
        except Exception as e:
            logger.error(f"Failed to check URL for user {user_id}: {str(e)}")
            return None

    def update_job(self, job_id: str, **updates) -> bool:
        """Update job status in DynamoDB."""
        try:
            # Prepare update expression with attribute names for reserved keywords
            update_expression = "SET updated_at = :updated_at"
            expression_values = {':updated_at': datetime.now().isoformat()}
            expression_names = {}

            for key, value in updates.items():
                if key in ['status', 'progress', 'step', 'result', 'error']:
                    # Handle reserved keywords with expression attribute names
                    if key == 'status':
                        attr_name = '#status'
                        expression_names['#status'] = 'status'
                    elif key == 'result':
                        attr_name = '#result'
                        expression_names['#result'] = 'result'
                    elif key == 'error':
                        attr_name = '#error'
                        expression_names['#error'] = 'error'
                    else:
                        attr_name = key

                    update_expression += f", {attr_name} = :{key}"

                    # Convert complex objects to dict for DynamoDB storage
                    if hasattr(value, 'dict'):  # Pydantic model
                        expression_values[f":{key}"] = value.dict()
                    elif hasattr(value, '__dict__'):  # Other objects
                        expression_values[f":{key}"] = value.__dict__
                    else:
                        expression_values[f":{key}"] = value

            # Build the update request
            update_kwargs = {
                'Key': {'job_id': job_id},
                'UpdateExpression': update_expression,
                'ExpressionAttributeValues': expression_values
            }

            # Only add ExpressionAttributeNames if we have reserved keywords
            if expression_names:
                update_kwargs['ExpressionAttributeNames'] = expression_names

            self.table.update_item(**update_kwargs)

            logger.debug(f"Updated job {job_id}: {updates}")
            return True

        except Exception as e:
            logger.error(f"Failed to update job {job_id}: {str(e)}")
            return False

    def update_job_status(self, job_id: str, status: str, progress: int = 0,
                         step: str = None, result: Any = None, error: str = None):
        """Helper method to update job status with common parameters."""
        updates = {'status': status, 'progress': progress}

        if step is not None:
            updates['step'] = step
        if result is not None:
            updates['result'] = result
        if error is not None:
            updates['error'] = error

        return self.update_job(job_id, **updates)

    def list_jobs_by_status(self, status: str, limit: int = 100) -> list:
        """List jobs by status (useful for debugging/monitoring)."""
        try:
            response = self.table.query(
                IndexName='status-created-index',
                KeyConditionExpression='#status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':status': status},
                Limit=limit,
                ScanIndexForward=False  # Most recent first
            )
            return response.get('Items', [])
        except Exception as e:
            logger.error(f"Failed to list jobs by status {status}: {str(e)}")
            return []