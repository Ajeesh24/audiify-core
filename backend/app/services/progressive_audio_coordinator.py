import os
import json
import boto3
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class ProgressiveAudioCoordinator:
    """Coordinates sequential processing of progressive audio chunks to prevent race conditions."""

    def __init__(self):
        """Initialize DynamoDB client and table."""
        self.dynamodb = boto3.resource('dynamodb')
        self.table_name = os.environ.get('DYNAMODB_TABLE_NAME')
        if not self.table_name:
            raise ValueError("DYNAMODB_TABLE_NAME environment variable not set")

        self.table = self.dynamodb.Table(self.table_name)

    def initialize_audio_coordination(self, audio_id: str, user_id: str, total_chunks: int, s3_key: str) -> bool:
        """Initialize coordination record for progressive audio processing."""
        try:
            coordination_id = f"coord_{audio_id}"

            coordination_data = {
                'job_id': coordination_id,
                'audio_id': audio_id,
                'user_id': user_id,
                'total_chunks': total_chunks,
                's3_key': s3_key,
                'next_expected_chunk': 2,  # Chunk 1 is processed immediately
                'completed_chunks': 1,     # Chunk 1 already done
                'pending_chunks': {},      # Store out-of-order chunks
                'status': 'processing',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }

            self.table.put_item(Item=coordination_data)
            logger.info(f"Initialized audio coordination for {audio_id}: expecting chunks 2-{total_chunks}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize audio coordination for {audio_id}: {str(e)}")
            return False

    def try_process_chunk(self, audio_id: str, chunk_index: int, chunk_data: bytes) -> Dict[str, Any]:
        """
        Try to process a chunk. Returns processing instructions.

        Returns:
            {
                'should_process': bool,     # Whether to process this chunk now
                'is_next_in_sequence': bool,# Whether this is the expected next chunk
                'coordination_data': dict,  # Current coordination state
                'pending_chunks': list      # List of chunks ready to process after this one
            }
        """
        try:
            coordination_id = f"coord_{audio_id}"

            # Get current coordination state with strong consistency
            response = self.table.get_item(
                Key={'job_id': coordination_id},
                ConsistentRead=True
            )

            if 'Item' not in response:
                logger.warning(f"No coordination data found for {audio_id}")
                return {
                    'should_process': False,
                    'is_next_in_sequence': False,
                    'coordination_data': None,
                    'pending_chunks': []
                }

            coord_data = response['Item']
            next_expected = coord_data.get('next_expected_chunk', 2)

            logger.info(f"Chunk {chunk_index} arrived for {audio_id} (expecting chunk {next_expected})")

            if chunk_index == next_expected:
                # This is the next chunk we're waiting for - process immediately
                return {
                    'should_process': True,
                    'is_next_in_sequence': True,
                    'coordination_data': coord_data,
                    'pending_chunks': []
                }
            elif chunk_index > next_expected:
                # Future chunk - store it for later processing
                self._store_pending_chunk(coordination_id, chunk_index, chunk_data)
                logger.info(f"Stored chunk {chunk_index} for later processing (waiting for chunk {next_expected})")
                return {
                    'should_process': False,
                    'is_next_in_sequence': False,
                    'coordination_data': coord_data,
                    'pending_chunks': []
                }
            else:
                # Already processed chunk - ignore
                logger.info(f"Ignoring already processed chunk {chunk_index} (expecting chunk {next_expected})")
                return {
                    'should_process': False,
                    'is_next_in_sequence': False,
                    'coordination_data': coord_data,
                    'pending_chunks': []
                }

        except Exception as e:
            logger.error(f"Failed to check chunk processing for {audio_id} chunk {chunk_index}: {str(e)}")
            return {
                'should_process': False,
                'is_next_in_sequence': False,
                'coordination_data': None,
                'pending_chunks': []
            }

    def mark_chunk_completed(self, audio_id: str, chunk_index: int) -> List[Dict[str, Any]]:
        """
        Mark a chunk as completed and return any pending chunks that can now be processed.

        Returns:
            List of pending chunks ready for processing: [{'index': int, 'data': bytes}, ...]
        """
        try:
            coordination_id = f"coord_{audio_id}"

            # Update coordination state atomically
            response = self.table.update_item(
                Key={'job_id': coordination_id},
                UpdateExpression='SET next_expected_chunk = next_expected_chunk + :inc, completed_chunks = completed_chunks + :inc, updated_at = :updated',
                ExpressionAttributeValues={
                    ':inc': 1,
                    ':updated': datetime.now().isoformat()
                },
                ReturnValues='ALL_NEW'
            )

            updated_data = response['Attributes']
            new_next_expected = updated_data.get('next_expected_chunk')
            total_chunks = updated_data.get('total_chunks')
            pending_chunks = updated_data.get('pending_chunks', {})

            logger.info(f"Marked chunk {chunk_index} completed for {audio_id}. Now expecting chunk {new_next_expected}")

            # Check if we're done
            if updated_data.get('completed_chunks', 0) >= total_chunks:
                self._mark_audio_complete(coordination_id)
                logger.info(f"All chunks completed for {audio_id}")
                return []

            # Check if next expected chunk is available in pending
            ready_chunks = []
            current_expected = new_next_expected

            while str(current_expected) in pending_chunks and current_expected <= total_chunks:
                chunk_data = pending_chunks[str(current_expected)]
                ready_chunks.append({
                    'index': current_expected,
                    'data': chunk_data.encode('latin1') if isinstance(chunk_data, str) else chunk_data
                })

                # Remove from pending and increment expected
                self._remove_pending_chunk(coordination_id, current_expected)
                current_expected += 1

                logger.info(f"Found ready pending chunk {current_expected - 1} for {audio_id}")

            return ready_chunks

        except Exception as e:
            logger.error(f"Failed to mark chunk {chunk_index} completed for {audio_id}: {str(e)}")
            return []

    def _store_pending_chunk(self, coordination_id: str, chunk_index: int, chunk_data: bytes):
        """Store a chunk that arrived out of order."""
        try:
            # Convert bytes to base64 string for DynamoDB storage
            import base64
            chunk_data_str = base64.b64encode(chunk_data).decode('utf-8')

            self.table.update_item(
                Key={'job_id': coordination_id},
                UpdateExpression='SET pending_chunks.#chunk_idx = :chunk_data, updated_at = :updated',
                ExpressionAttributeNames={'#chunk_idx': str(chunk_index)},
                ExpressionAttributeValues={
                    ':chunk_data': chunk_data_str,
                    ':updated': datetime.now().isoformat()
                }
            )
            logger.info(f"Stored pending chunk {chunk_index} in DynamoDB")

        except Exception as e:
            logger.error(f"Failed to store pending chunk {chunk_index}: {str(e)}")

    def _remove_pending_chunk(self, coordination_id: str, chunk_index: int):
        """Remove a chunk from pending storage."""
        try:
            self.table.update_item(
                Key={'job_id': coordination_id},
                UpdateExpression='REMOVE pending_chunks.#chunk_idx SET updated_at = :updated',
                ExpressionAttributeNames={'#chunk_idx': str(chunk_index)},
                ExpressionAttributeValues={
                    ':updated': datetime.now().isoformat()
                }
            )
            logger.info(f"Removed pending chunk {chunk_index} from DynamoDB")

        except Exception as e:
            logger.error(f"Failed to remove pending chunk {chunk_index}: {str(e)}")

    def _mark_audio_complete(self, coordination_id: str):
        """Mark the progressive audio as complete."""
        try:
            self.table.update_item(
                Key={'job_id': coordination_id},
                UpdateExpression='SET #status = :status, updated_at = :updated',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'complete',
                    ':updated': datetime.now().isoformat()
                }
            )
            logger.info(f"Marked audio coordination as complete: {coordination_id}")

        except Exception as e:
            logger.error(f"Failed to mark audio complete {coordination_id}: {str(e)}")

    def get_coordination_status(self, audio_id: str) -> Optional[Dict[str, Any]]:
        """Get current coordination status for an audio."""
        try:
            coordination_id = f"coord_{audio_id}"

            response = self.table.get_item(
                Key={'job_id': coordination_id},
                ConsistentRead=True
            )

            if 'Item' not in response:
                return None

            return response['Item']

        except Exception as e:
            logger.error(f"Failed to get coordination status for {audio_id}: {str(e)}")
            return None