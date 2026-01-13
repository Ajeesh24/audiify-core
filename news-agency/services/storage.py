"""
Storage Service

Centralized S3 operations for audio files and data archival
"""

import boto3
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from config import S3_SETTINGS, AWS_REGION, get_s3_key
from utils.logger import get_logger

logger = get_logger(__name__)


class StorageService:
    """
    Storage service for managing S3 operations
    """

    def __init__(self):
        self.s3_client = boto3.client('s3', region_name=AWS_REGION)
        self.bucket_name = S3_SETTINGS['bucket_name']

    def upload_audio_file(self,
                         audio_data: bytes,
                         filename: str,
                         category: str = None,
                         metadata: Dict[str, str] = None) -> Optional[str]:
        """
        Upload audio file to S3

        Args:
            audio_data: Audio file bytes
            filename: File name
            category: Content category
            metadata: Additional metadata

        Returns:
            S3 URL or None if failed
        """
        try:
            # Generate S3 key
            s3_key = get_s3_key('audio', filename)

            # Prepare metadata
            upload_metadata = {
                'uploaded_at': datetime.utcnow().isoformat(),
                'content_type': 'audio/mpeg',
            }
            if category:
                upload_metadata['category'] = category
            if metadata:
                upload_metadata.update(metadata)

            # Upload file
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=audio_data,
                ContentType='audio/mpeg',
                Metadata=upload_metadata,
                ACL='public-read'  # Make publicly accessible
            )

            # Generate public URL
            url = f"https://{self.bucket_name}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
            logger.info(f"Uploaded audio file: {url}")
            return url

        except Exception as e:
            logger.error(f"Error uploading audio file {filename}: {str(e)}")
            return None

    def get_audio_metadata(self, s3_key: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for an audio file

        Args:
            s3_key: S3 object key

        Returns:
            File metadata or None if not found
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )

            return {
                'size': response['ContentLength'],
                'last_modified': response['LastModified'],
                'content_type': response['ContentType'],
                'metadata': response.get('Metadata', {}),
                'url': f"https://{self.bucket_name}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
            }

        except Exception as e:
            logger.error(f"Error getting metadata for {s3_key}: {str(e)}")
            return None

    def list_audio_files(self,
                        prefix: str = None,
                        limit: int = 100) -> List[Dict[str, Any]]:
        """
        List audio files in S3

        Args:
            prefix: S3 key prefix to filter by
            limit: Maximum number of files to return

        Returns:
            List of file information
        """
        try:
            # Use audio prefix if no specific prefix provided
            if not prefix:
                prefix = S3_SETTINGS['audio_prefix']

            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=limit
            )

            files = []
            for obj in response.get('Contents', []):
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'url': f"https://{self.bucket_name}.s3.{AWS_REGION}.amazonaws.com/{obj['Key']}"
                })

            return files

        except Exception as e:
            logger.error(f"Error listing audio files: {str(e)}")
            return []

    def delete_audio_file(self, s3_key: str) -> bool:
        """
        Delete an audio file from S3

        Args:
            s3_key: S3 object key

        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            logger.info(f"Deleted audio file: {s3_key}")
            return True

        except Exception as e:
            logger.error(f"Error deleting audio file {s3_key}: {str(e)}")
            return False

    def cleanup_old_files(self, days_to_keep: int = 7) -> Dict[str, Any]:
        """
        Clean up old audio files to manage storage costs

        Args:
            days_to_keep: Number of days to keep files

        Returns:
            Cleanup results summary
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        results = {
            'files_checked': 0,
            'files_deleted': 0,
            'space_freed': 0,
            'errors': []
        }

        try:
            # List all audio files
            audio_files = self.list_audio_files()
            results['files_checked'] = len(audio_files)

            for file_info in audio_files:
                # Check if file is older than cutoff
                if file_info['last_modified'] < cutoff_date:
                    if self.delete_audio_file(file_info['key']):
                        results['files_deleted'] += 1
                        results['space_freed'] += file_info['size']
                    else:
                        results['errors'].append(f"Failed to delete {file_info['key']}")

            logger.info(f"Cleanup completed: deleted {results['files_deleted']} files, "
                       f"freed {results['space_freed']} bytes")

        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            results['errors'].append(str(e))

        return results

    def archive_old_data(self, days_to_archive: int = 30) -> Dict[str, Any]:
        """
        Move old audio files to cheaper storage class

        Args:
            days_to_archive: Age threshold for archiving

        Returns:
            Archive results summary
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_archive)

        results = {
            'files_checked': 0,
            'files_archived': 0,
            'errors': []
        }

        try:
            audio_files = self.list_audio_files()
            results['files_checked'] = len(audio_files)

            for file_info in audio_files:
                if file_info['last_modified'] < cutoff_date:
                    try:
                        # Move to IA (Infrequent Access) storage class
                        self.s3_client.copy_object(
                            Bucket=self.bucket_name,
                            CopySource={'Bucket': self.bucket_name, 'Key': file_info['key']},
                            Key=file_info['key'],
                            StorageClass='STANDARD_IA',
                            MetadataDirective='COPY'
                        )
                        results['files_archived'] += 1

                    except Exception as e:
                        results['errors'].append(f"Failed to archive {file_info['key']}: {str(e)}")

            logger.info(f"Archive completed: archived {results['files_archived']} files")

        except Exception as e:
            logger.error(f"Error during archiving: {str(e)}")
            results['errors'].append(str(e))

        return results

    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage usage statistics

        Returns:
            Storage statistics
        """
        try:
            audio_files = self.list_audio_files()

            total_size = sum(file_info['size'] for file_info in audio_files)
            total_files = len(audio_files)

            # Calculate storage by date
            daily_stats = {}
            for file_info in audio_files:
                date_key = file_info['last_modified'].strftime('%Y-%m-%d')
                if date_key not in daily_stats:
                    daily_stats[date_key] = {'files': 0, 'size': 0}

                daily_stats[date_key]['files'] += 1
                daily_stats[date_key]['size'] += file_info['size']

            return {
                'total_files': total_files,
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'daily_breakdown': daily_stats,
                'estimated_monthly_cost_usd': (total_size / (1024**3)) * 0.023  # ~$0.023 per GB/month
            }

        except Exception as e:
            logger.error(f"Error getting storage stats: {str(e)}")
            return {'error': str(e)}

    def create_presigned_url(self, s3_key: str, expiration: int = 3600) -> Optional[str]:
        """
        Create a presigned URL for temporary access to a file

        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds

        Returns:
            Presigned URL or None if failed
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return url

        except Exception as e:
            logger.error(f"Error creating presigned URL for {s3_key}: {str(e)}")
            return None


# Global storage service instance
storage_service = StorageService()