import os
import boto3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class AudioMetadataStorage:
    """DynamoDB-based storage for progressive audio metadata."""

    def __init__(self):
        """Initialize DynamoDB client and table."""
        self.dynamodb = boto3.resource('dynamodb')
        # Use the same table as jobs but with different partition key pattern
        self.table_name = os.environ.get('DYNAMODB_TABLE_NAME')
        if not self.table_name:
            raise ValueError("DYNAMODB_TABLE_NAME environment variable not set")

        self.table = self.dynamodb.Table(self.table_name)

    def create_audio_metadata(self, audio_id: str, user_id: str, total_chunks: int,
                            s3_key: str, initial_file_size: int = 0) -> Dict[str, Any]:
        """Create initial audio metadata record."""
        try:
            # Calculate TTL (audio metadata expires after 3 days)
            ttl = int((datetime.now() + timedelta(days=3)).timestamp())

            metadata = {
                'job_id': f'audio_{audio_id}',  # Use audio_ prefix to distinguish from jobs
                'audio_id': audio_id,
                'user_id': user_id,
                'file_size': initial_file_size,
                'chunks_completed': 1 if initial_file_size > 0 else 0,
                'total_chunks': total_chunks,
                's3_key': s3_key,
                'status': 'growing',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'ttl': ttl
            }

            self.table.put_item(Item=metadata)
            logger.info(f"Created audio metadata for {audio_id}: {metadata['chunks_completed']}/{total_chunks} chunks")
            return metadata

        except Exception as e:
            logger.error(f"Failed to create audio metadata for {audio_id}: {str(e)}")
            raise

    def update_audio_metadata(self, audio_id: str, file_size: int, chunks_completed: int):
        """Update audio metadata when a chunk is completed with atomic operations."""
        try:
            job_id = f'audio_{audio_id}'

            # First, get current state to determine total chunks
            response = self.table.get_item(Key={'job_id': job_id})
            if 'Item' not in response:
                logger.warning(f"Audio metadata not found for {audio_id}")
                return False

            item = response['Item']
            total_chunks = item.get('total_chunks', 1)
            current_chunks = item.get('chunks_completed', 0)

            # Only update if this chunk is actually newer (prevents out-of-order updates)
            if chunks_completed <= current_chunks:
                logger.info(f"Skipping update for {audio_id}: chunk {chunks_completed} <= current {current_chunks}")
                return True

            status = 'complete' if chunks_completed >= total_chunks else 'growing'

            # Use conditional update to prevent race conditions
            try:
                self.table.update_item(
                    Key={'job_id': job_id},
                    UpdateExpression='SET file_size = :size, chunks_completed = :completed, #status = :status, updated_at = :updated',
                    ConditionExpression='chunks_completed < :completed',  # Only update if we're actually progressing
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={
                        ':size': file_size,
                        ':completed': chunks_completed,
                        ':status': status,
                        ':updated': datetime.now().isoformat()
                    }
                )

                logger.info(f"Updated audio metadata for {audio_id}: {file_size} bytes, {chunks_completed}/{total_chunks} chunks, status: {status}")
                return True

            except self.dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
                # Race condition - another process already updated with higher chunk count
                logger.info(f"Skipping outdated update for {audio_id}: chunk {chunks_completed} (race condition)")
                return True

        except Exception as e:
            logger.error(f"Failed to update audio metadata for {audio_id}: {str(e)}")
            return False

    def get_audio_metadata(self, audio_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get audio metadata for progress tracking with strong consistency for completion checks."""
        try:
            job_id = f'audio_{audio_id}'

            # Use strongly consistent read to avoid eventual consistency issues during completion
            response = self.table.get_item(
                Key={'job_id': job_id},
                ConsistentRead=True  # Force strongly consistent read
            )

            if 'Item' not in response:
                return None

            item = response['Item']

            # Verify user access
            if item.get('user_id') != user_id:
                logger.warning(f"User {user_id} attempted to access audio {audio_id} owned by {item.get('user_id')}")
                return None

            return {
                'audio_id': item.get('audio_id'),
                'file_size': item.get('file_size', 0),
                'chunks_completed': item.get('chunks_completed', 0),
                'total_chunks': item.get('total_chunks', 1),
                's3_key': item.get('s3_key'),
                'status': item.get('status', 'unknown'),
                'created_at': item.get('created_at'),
                'updated_at': item.get('updated_at')
            }

        except Exception as e:
            logger.error(f"Failed to get audio metadata for {audio_id}: {str(e)}")
            return None

    def delete_audio_metadata(self, audio_id: str, user_id: str) -> bool:
        """Delete audio metadata (for cleanup)."""
        try:
            job_id = f'audio_{audio_id}'

            # Verify ownership before deletion
            metadata = self.get_audio_metadata(audio_id, user_id)
            if not metadata:
                return False

            self.table.delete_item(Key={'job_id': job_id})
            logger.info(f"Deleted audio metadata for {audio_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete audio metadata for {audio_id}: {str(e)}")
            return False

    def cleanup_old_metadata(self, days_old: int = 3):
        """Clean up old audio metadata records."""
        try:
            # This would use a GSI or scan - simplified for now
            logger.info(f"Audio metadata cleanup not implemented - relies on DynamoDB TTL")
            return True

        except Exception as e:
            logger.error(f"Failed to cleanup old audio metadata: {str(e)}")
            return False