"""
News Agency API

This package contains API endpoints for the news agency system.
"""

from .briefings import BriefingsAPI
from .internal import InternalAPI

__all__ = [
    'BriefingsAPI',
    'InternalAPI'
]