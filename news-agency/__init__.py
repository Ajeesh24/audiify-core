"""
Audifyy News Agency

Automated Daily Tech News Briefing System

A sophisticated 5-engine pipeline that automatically generates three daily tech audio briefs:
- 🌐 General Tech - Consumer tech, business, startups (7-10 min)
- 🤖 AI/ML - Research, model releases, applications (7-10 min)
- 💻 DevOps/Platform - Cloud, infrastructure, dev tools (7-10 min)

Architecture:
RSS Engine → Categorization Engine → Ranking Engine → Brief Engine → Audio Engine

Cost Optimized: <$0.50/day with 10K tokens/day budget
"""

__version__ = "1.0.0"
__author__ = "Audifyy Team"
__email__ = "team@audifyy.com"

from .models import Article, Brief, Job, EngineStatus, JobStatus
from .engines import (
    RSSEngine, CategorizationEngine, RankingEngine,
    BriefGenerationEngine, AudioGenerationEngine
)
from .services import PipelineOrchestrator, DatabaseService, StorageService
from .api import BriefingsAPI, InternalAPI
from .utils import get_logger, cost_tracker, performance_tracker

__all__ = [
    # Core Models
    'Article',
    'Brief',
    'Job',
    'EngineStatus',
    'JobStatus',

    # Processing Engines
    'RSSEngine',
    'CategorizationEngine',
    'RankingEngine',
    'BriefGenerationEngine',
    'AudioGenerationEngine',

    # Services
    'PipelineOrchestrator',
    'DatabaseService',
    'StorageService',

    # APIs
    'BriefingsAPI',
    'InternalAPI',

    # Utilities
    'get_logger',
    'cost_tracker',
    'performance_tracker',
]