"""
DynamoDB Article Model
Stores raw article metadata for the news pipeline
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional, List
import boto3
from boto3.dynamodb.conditions import Key, Attr
import uuid


class Article:
    """
    Article model for storing news article metadata

    Optimized for cost - stores only metadata, not full content
    Content is fetched on-demand during processing
    """

    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        # Use environment variable for table name
        import os
        table_name = os.getenv('ARTICLES_TABLE', 'audifyy-news-articles-dev')
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
                cleaned[key] = [self._clean_for_dynamodb(item) if isinstance(item, dict) else
                              Decimal(str(item)) if isinstance(item, float) else item for item in value]
            else:
                cleaned[key] = value
        return cleaned

    def create_article(self,
                      url: str,
                      title: str,
                      summary: str,
                      source: str,
                      published_date: datetime,
                      category: Optional[str] = None,
                      tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Create a new article entry

        Args:
            url: Article URL (unique identifier)
            title: Article title
            summary: Brief article summary/description
            source: RSS feed source name
            published_date: When article was published
            category: Tech category (AI/ML, DevOps, General)
            tags: List of relevant tags

        Returns:
            Created article data
        """
        article_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        processing_date = datetime.utcnow().strftime('%Y-%m-%d')

        article_data = {
            'article_id': article_id,  # Hash key
            'date': processing_date,   # Range key
            'url': url,
            'title': title,
            'summary': summary,
            'source': source,
            'published_date': published_date.isoformat(),
            'category': category,
            'tags': tags or [],
            'status': 'collected',  # collected, categorized, ranked, processed
            'created_at': now,
            'updated_at': now,
            'processing_date': processing_date,  # For GSI querying
            'relevance_score': None,  # Set by ranking engine
            'content_hash': None,     # For duplicate detection
        }

        try:
            cleaned_data = self._clean_for_dynamodb(article_data)
            self.table.put_item(
                Item=cleaned_data,
                ConditionExpression='attribute_not_exists(article_id)'
            )
            return article_data
        except self.dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            # Article already exists, update it
            return self.update_article(article_id, processing_date, **{k: v for k, v in article_data.items()
                                             if k not in ['article_id', 'date', 'created_at']})

    def get_article_by_id(self, article_id: str, date: str) -> Optional[Dict[str, Any]]:
        """Get article by ID and date"""
        try:
            response = self.table.get_item(Key={'article_id': article_id, 'date': date})
            return response.get('Item')
        except Exception as e:
            print(f"Error fetching article {article_id}: {e}")
            return None

    def get_article_by_url(self, url: str, date: str) -> Optional[Dict[str, Any]]:
        """Get article by URL for a specific date"""
        try:
            # Use URL index to find article
            response = self.table.query(
                IndexName='url-index',
                KeyConditionExpression=Key('url').eq(url)
            )
            items = response.get('Items', [])
            # Filter by date if multiple articles with same URL exist
            for item in items:
                if item.get('date') == date:
                    return item
            return items[0] if items else None
        except Exception as e:
            print(f"Error fetching article by URL {url}: {e}")
            return None

    def get_articles_by_date(self, date: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get articles for a specific processing date

        Args:
            date: Processing date in YYYY-MM-DD format
            status: Filter by article status

        Returns:
            List of articles
        """
        try:
            # Query using date-index GSI
            response = self.table.query(
                IndexName='date-index',
                KeyConditionExpression=Key('processing_date').eq(date)
            )

            articles = response.get('Items', [])

            if status:
                articles = [a for a in articles if a.get('status') == status]

            return articles
        except Exception as e:
            print(f"Error fetching articles for date {date}: {e}")
            return []

    def get_articles_by_category(self, category: str, date: str) -> List[Dict[str, Any]]:
        """Get articles by category for a specific date"""
        try:
            response = self.table.query(
                IndexName='category-date-index',
                KeyConditionExpression=Key('category').eq(category) & Key('processing_date').eq(date)
            )
            return response.get('Items', [])
        except Exception as e:
            print(f"Error fetching articles for category {category}: {e}")
            return []

    def update_article(self, article_id: str, date: str, **kwargs) -> Dict[str, Any]:
        """Update article fields"""
        update_expression = "SET updated_at = :updated_at"
        expression_values = {':updated_at': datetime.utcnow().isoformat()}
        expression_names = {}

        for key, value in kwargs.items():
            if key not in ['article_id', 'date', 'created_at']:
                placeholder = f":{key}"
                if key in ['status', 'category']:  # Reserved keywords
                    name_placeholder = f"#{key}"
                    update_expression += f", {name_placeholder} = {placeholder}"
                    expression_names[name_placeholder] = key
                else:
                    update_expression += f", {key} = {placeholder}"
                expression_values[placeholder] = value

        try:
            response = self.table.update_item(
                Key={'article_id': article_id, 'date': date},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names if expression_names else None,
                ReturnValues='ALL_NEW'
            )
            return response.get('Attributes', {})
        except Exception as e:
            print(f"Error updating article {article_id}: {e}")
            return {}

    def batch_update_status(self, article_keys: List[Dict[str, str]], status: str):
        """
        Update status for multiple articles

        Args:
            article_keys: List of {'article_id': id, 'date': date} dicts
            status: New status to set
        """
        with self.table.batch_writer() as batch:
            for key in article_keys:
                batch.update_item(
                    Key=key,
                    UpdateExpression="SET #status = :status, updated_at = :updated_at",
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={
                        ':status': status,
                        ':updated_at': datetime.utcnow().isoformat()
                    }
                )

    def get_top_articles(self, category: str, date: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top-ranked articles for a category and date

        Args:
            category: Article category
            date: Processing date
            limit: Number of articles to return

        Returns:
            List of top articles sorted by relevance_score
        """
        articles = self.get_articles_by_category(category, date)

        # Filter articles with relevance scores and sort
        scored_articles = [a for a in articles if a.get('relevance_score') is not None]
        scored_articles.sort(key=lambda x: x['relevance_score'], reverse=True)

        return scored_articles[:limit]

    def cleanup_old_articles(self, days_to_keep: int = 7):
        """
        Clean up articles older than specified days
        Cost optimization - keep only recent articles
        """
        cutoff_date = datetime.utcnow().strftime('%Y-%m-%d')
        # Implementation depends on your cleanup strategy
        pass