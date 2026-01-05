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

    def create_job(self, job_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new job and send to SQS for background processing."""
        try:
            # Calculate TTL (jobs expire after 7 days)
            ttl = int((datetime.now() + timedelta(days=7)).timestamp())

            job_data = {
                'job_id': job_id,
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
                'request_data': request_data
            }

            self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message_body)
            )

            logger.info(f"Created job {job_id} and queued for processing")
            return job_data

        except Exception as e:
            logger.error(f"Failed to create job {job_id}: {str(e)}")
            raise

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status from DynamoDB."""
        try:
            response = self.table.get_item(Key={'job_id': job_id})
            return response.get('Item')
        except Exception as e:
            logger.error(f"Failed to get job {job_id}: {str(e)}")
            return None

    def update_job(self, job_id: str, **updates) -> bool:
        """Update job status in DynamoDB."""
        try:
            # Prepare update expression
            update_expression = "SET updated_at = :updated_at"
            expression_values = {':updated_at': datetime.now().isoformat()}

            for key, value in updates.items():
                if key in ['status', 'progress', 'step', 'result', 'error']:
                    update_expression += f", {key} = :{key}"
                    expression_values[f":{key}"] = value

            self.table.update_item(
                Key={'job_id': job_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )

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