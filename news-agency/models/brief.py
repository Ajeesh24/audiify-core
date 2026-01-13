"""
DynamoDB Brief Model
Stores generated audio briefings and metadata
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional, List
import boto3
from boto3.dynamodb.conditions import Key, Attr
import uuid


class Brief:
    """
    Brief model for storing generated audio briefings

    Manages the daily tech briefings across different categories
    """

    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        # Use environment variable for table name
        import os
        table_name = os.getenv('BRIEFS_TABLE', 'audifyy-briefs-dev')
        self.table = self.dynamodb.Table(table_name)

    def _clean_for_dynamodb(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert all float values to Decimal for DynamoDB"""
        cleaned = {}
        for key, value in data.items():
            if isinstance(value, float):
                cleaned[key] = Decimal(str(value))
            elif isinstance(value, dict):
                cleaned[key] = self._clean_for_dynamodb(value)
            elif isinstance(value, list):
                cleaned[key] = [Decimal(str(item)) if isinstance(item, float) else item for item in value]
            else:
                cleaned[key] = value
        return cleaned

    def create_brief(self,
                    category: str,
                    date: str,
                    content: str,
                    articles_used: List[str],
                    word_count: int,
                    estimated_duration: int) -> Dict[str, Any]:
        """
        Create a new brief entry

        Args:
            category: Brief category (general-tech, ai-ml, devops-platform)
            date: Brief date in YYYY-MM-DD format
            content: Generated brief text content
            articles_used: List of article URLs used in the brief
            word_count: Number of words in the brief
            estimated_duration: Estimated audio duration in seconds

        Returns:
            Created brief data
        """
        brief_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        brief_data = {
            'brief_id': brief_id,
            'category': category,
            'date': date,
            'content': content,
            'articles_used': articles_used,
            'word_count': word_count,
            'estimated_duration': estimated_duration,
            'actual_duration': None,  # Set after audio generation
            'status': 'generated',    # generated, audio_processing, ready, error
            'audio_url': None,        # S3 URL for the audio file
            'audio_size': None,       # Audio file size in bytes
            'created_at': now,
            'updated_at': now,
            'generation_stats': {
                'articles_processed': len(articles_used),
                'generation_time': None,
                'audio_generation_time': None,
                'token_usage': None
            }
        }

        try:
            # Use category#date as composite key to ensure one brief per category per day
            composite_key = f"{category}#{date}"
            brief_data['composite_key'] = composite_key

            cleaned_data = self._clean_for_dynamodb(brief_data)
            self.table.put_item(
                Item=cleaned_data,
                ConditionExpression='attribute_not_exists(composite_key)'
            )
            return brief_data
        except self.dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            # Brief already exists for this category and date, update it
            return self.update_brief(category, date, **{k: v for k, v in brief_data.items()
                                                      if k not in ['brief_id', 'created_at', 'composite_key']})

    def get_brief(self, category: str, date: str) -> Optional[Dict[str, Any]]:
        """Get brief by category and date"""
        try:
            composite_key = f"{category}#{date}"
            response = self.table.get_item(Key={'composite_key': composite_key})
            return response.get('Item')
        except Exception as e:
            print(f"Error fetching brief {category} for {date}: {e}")
            return None

    def get_brief_by_id(self, brief_id: str) -> Optional[Dict[str, Any]]:
        """Get brief by ID"""
        try:
            response = self.table.query(
                IndexName='brief_id-index',
                KeyConditionExpression=Key('brief_id').eq(brief_id)
            )
            items = response.get('Items', [])
            return items[0] if items else None
        except Exception as e:
            print(f"Error fetching brief {brief_id}: {e}")
            return None

    def get_briefs_by_date(self, date: str) -> List[Dict[str, Any]]:
        """Get all briefs for a specific date"""
        try:
            response = self.table.query(
                IndexName='date-index',
                KeyConditionExpression=Key('date').eq(date)
            )
            return response.get('Items', [])
        except Exception as e:
            print(f"Error fetching briefs for date {date}: {e}")
            return []

    def get_latest_briefs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent briefs across all categories"""
        try:
            response = self.table.scan(
                FilterExpression=Attr('status').eq('ready'),
                Limit=limit
            )

            briefs = response.get('Items', [])
            # Sort by creation date, most recent first
            briefs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            return briefs[:limit]
        except Exception as e:
            print(f"Error fetching latest briefs: {e}")
            return []

    def update_brief(self, category: str, date: str, **kwargs) -> Dict[str, Any]:
        """Update brief fields"""
        composite_key = f"{category}#{date}"

        update_expression = "SET updated_at = :updated_at"
        expression_values = {':updated_at': datetime.utcnow().isoformat()}
        expression_names = {}

        for key, value in kwargs.items():
            if key not in ['composite_key', 'brief_id', 'created_at', 'category', 'date']:
                placeholder = f":{key}"
                if key in ['status']:  # Reserved keywords
                    name_placeholder = f"#{key}"
                    update_expression += f", {name_placeholder} = {placeholder}"
                    expression_names[name_placeholder] = key
                else:
                    update_expression += f", {key} = {placeholder}"
                expression_values[placeholder] = value

        try:
            response = self.table.update_item(
                Key={'composite_key': composite_key},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names if expression_names else None,
                ReturnValues='ALL_NEW'
            )
            return response.get('Attributes', {})
        except Exception as e:
            print(f"Error updating brief {category}#{date}: {e}")
            return {}

    def update_audio_info(self, category: str, date: str,
                         audio_url: str,
                         actual_duration: int,
                         audio_size: int):
        """Update brief with audio file information"""
        return self.update_brief(
            category,
            date,
            audio_url=audio_url,
            actual_duration=actual_duration,
            audio_size=audio_size,
            status='ready'
        )

    def update_generation_stats(self, category: str, date: str, stats: Dict[str, Any]):
        """Update brief generation statistics"""
        current_brief = self.get_brief(category, date)
        if current_brief:
            current_stats = current_brief.get('generation_stats', {})
            current_stats.update(stats)
            return self.update_brief(category, date, generation_stats=current_stats)
        return {}

    def get_daily_briefing_summary(self, date: str) -> Dict[str, Any]:
        """
        Get summary of all briefings for a specific date
        Useful for API endpoints and monitoring
        """
        briefs = self.get_briefs_by_date(date)

        summary = {
            'date': date,
            'total_briefs': len(briefs),
            'ready_briefs': len([b for b in briefs if b.get('status') == 'ready']),
            'processing_briefs': len([b for b in briefs if b.get('status') in ['generated', 'audio_processing']]),
            'error_briefs': len([b for b in briefs if b.get('status') == 'error']),
            'categories': {},
            'total_duration': 0,
            'total_articles_used': 0
        }

        for brief in briefs:
            category = brief.get('category', 'unknown')
            summary['categories'][category] = {
                'status': brief.get('status'),
                'duration': brief.get('actual_duration', 0),
                'word_count': brief.get('word_count', 0),
                'articles_count': len(brief.get('articles_used', [])),
                'audio_url': brief.get('audio_url'),
                'brief_id': brief.get('brief_id')
            }

            if brief.get('actual_duration'):
                summary['total_duration'] += brief['actual_duration']

            summary['total_articles_used'] += len(brief.get('articles_used', []))

        return summary

    def get_category_history(self, category: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get brief history for a specific category"""
        try:
            response = self.table.query(
                IndexName='category-date-index',
                KeyConditionExpression=Key('category').eq(category),
                ScanIndexForward=False,  # Sort by date descending
                Limit=days
            )
            return response.get('Items', [])
        except Exception as e:
            print(f"Error fetching category history for {category}: {e}")
            return []

    def cleanup_old_briefs(self, days_to_keep: int = 30):
        """
        Clean up old briefs and associated audio files
        Cost optimization strategy
        """
        # Implementation would involve:
        # 1. Query briefs older than days_to_keep
        # 2. Delete audio files from S3
        # 3. Delete brief records from DynamoDB
        pass