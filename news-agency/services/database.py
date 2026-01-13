"""
Database Service

Centralized database operations and connection management
"""

import boto3
from typing import Dict, Any, Optional
from config import DYNAMODB_TABLES, AWS_REGION, get_db_table_name
from utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseService:
    """
    Database service for managing DynamoDB connections and operations
    """

    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
        self._tables = {}

    def get_table(self, table_type: str):
        """
        Get DynamoDB table instance

        Args:
            table_type: Type of table (articles, briefs, jobs)

        Returns:
            DynamoDB table resource
        """
        if table_type not in self._tables:
            table_name = get_db_table_name(table_type)
            self._tables[table_type] = self.dynamodb.Table(table_name)

        return self._tables[table_type]

    def create_tables_if_not_exist(self):
        """
        Create DynamoDB tables if they don't exist (for local development)
        """
        try:
            # Articles table
            self._create_articles_table()
            # Briefs table
            self._create_briefs_table()
            # Jobs table
            self._create_jobs_table()
        except Exception as e:
            logger.error(f"Error creating tables: {str(e)}")

    def _create_articles_table(self):
        """Create articles table schema"""
        table_name = get_db_table_name('articles')

        try:
            table = self.dynamodb.create_table(
                TableName=table_name,
                KeySchema=[
                    {
                        'AttributeName': 'url',
                        'KeyType': 'HASH'  # Partition key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'url',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'processing_date',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'category',
                        'AttributeType': 'S'
                    }
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'processing_date-index',
                        'KeySchema': [
                            {
                                'AttributeName': 'processing_date',
                                'KeyType': 'HASH'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        },
                        'BillingMode': 'PAY_PER_REQUEST'
                    },
                    {
                        'IndexName': 'category-date-index',
                        'KeySchema': [
                            {
                                'AttributeName': 'category',
                                'KeyType': 'HASH'
                            },
                            {
                                'AttributeName': 'processing_date',
                                'KeyType': 'RANGE'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        },
                        'BillingMode': 'PAY_PER_REQUEST'
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )

            # Wait for table to be created
            table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
            logger.info(f"Created articles table: {table_name}")

        except self.dynamodb.meta.client.exceptions.ResourceInUseException:
            logger.info(f"Articles table {table_name} already exists")

    def _create_briefs_table(self):
        """Create briefs table schema"""
        table_name = get_db_table_name('briefs')

        try:
            table = self.dynamodb.create_table(
                TableName=table_name,
                KeySchema=[
                    {
                        'AttributeName': 'composite_key',  # category#date
                        'KeyType': 'HASH'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'composite_key',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'brief_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'date',
                        'AttributeType': 'S'
                    }
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'brief_id-index',
                        'KeySchema': [
                            {
                                'AttributeName': 'brief_id',
                                'KeyType': 'HASH'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        },
                        'BillingMode': 'PAY_PER_REQUEST'
                    },
                    {
                        'IndexName': 'date-index',
                        'KeySchema': [
                            {
                                'AttributeName': 'date',
                                'KeyType': 'HASH'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        },
                        'BillingMode': 'PAY_PER_REQUEST'
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )

            table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
            logger.info(f"Created briefs table: {table_name}")

        except self.dynamodb.meta.client.exceptions.ResourceInUseException:
            logger.info(f"Briefs table {table_name} already exists")

    def _create_jobs_table(self):
        """Create jobs table schema"""
        table_name = get_db_table_name('jobs')

        try:
            table = self.dynamodb.create_table(
                TableName=table_name,
                KeySchema=[
                    {
                        'AttributeName': 'date',
                        'KeyType': 'HASH'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'date',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'job_id',
                        'AttributeType': 'S'
                    }
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'job_id-index',
                        'KeySchema': [
                            {
                                'AttributeName': 'job_id',
                                'KeyType': 'HASH'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        },
                        'BillingMode': 'PAY_PER_REQUEST'
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )

            table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
            logger.info(f"Created jobs table: {table_name}")

        except self.dynamodb.meta.client.exceptions.ResourceInUseException:
            logger.info(f"Jobs table {table_name} already exists")


# Global database service instance
db_service = DatabaseService()