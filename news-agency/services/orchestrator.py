"""
Pipeline Orchestrator

Coordinates the execution of all 5 engines in the correct sequence
Handles error recovery and pipeline monitoring
"""

import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from engines import (
    RSSEngine, CategorizationEngine, RankingEngine,
    BriefGenerationEngine, AudioGenerationEngine
)
from models import Job, JobStatus, EngineStatus
from config import PIPELINE_SCHEDULE, COST_OPTIMIZATION
from utils.logger import get_logger, log_engine_start, log_engine_complete, log_engine_error
from utils.metrics import cost_tracker, performance_tracker, time_operation

logger = get_logger(__name__)


class PipelineStage(Enum):
    RSS_COLLECTION = "rss_collection"
    CATEGORIZATION = "categorization"
    RANKING = "ranking"
    BRIEF_GENERATION = "brief_generation"
    AUDIO_GENERATION = "audio_generation"


class PipelineOrchestrator:
    """
    Pipeline Orchestrator

    Manages the execution of the entire news pipeline:
    1. RSS Collection (Engine 1)
    2. Article Categorization (Engine 2)
    3. Article Ranking (Engine 3)
    4. Brief Generation (Engine 4)
    5. Audio Generation (Engine 5)
    """

    def __init__(self):
        self.job_model = Job()

        # Initialize all engines
        self.engines = {
            PipelineStage.RSS_COLLECTION: RSSEngine(),
            PipelineStage.CATEGORIZATION: CategorizationEngine(),
            PipelineStage.RANKING: RankingEngine(),
            PipelineStage.BRIEF_GENERATION: BriefGenerationEngine(),
            PipelineStage.AUDIO_GENERATION: AudioGenerationEngine()
        }

        # Pipeline execution order
        self.pipeline_order = [
            PipelineStage.RSS_COLLECTION,
            PipelineStage.CATEGORIZATION,
            PipelineStage.RANKING,
            PipelineStage.BRIEF_GENERATION,
            PipelineStage.AUDIO_GENERATION
        ]

    def run_daily_pipeline(self, date: str = None, stages: List[str] = None) -> Dict[str, Any]:
        """
        Execute the complete daily pipeline

        Args:
            date: Date in YYYY-MM-DD format (defaults to today)
            stages: Specific stages to run (defaults to all)

        Returns:
            Pipeline execution results
        """
        if not date:
            date = datetime.utcnow().strftime('%Y-%m-%d')

        logger.info(f"Starting daily news pipeline for {date}")

        # Create or get existing job
        job = self.job_model.get_job(date) or self.job_model.create_daily_job(date)

        # Determine which stages to run
        if stages:
            stages_to_run = [PipelineStage(stage) for stage in stages if stage in [s.value for s in PipelineStage]]
        else:
            stages_to_run = self.pipeline_order

        results = {
            'date': date,
            'job_id': job['job_id'],
            'pipeline_status': 'running',
            'stages_completed': 0,
            'total_stages': len(stages_to_run),
            'start_time': datetime.utcnow().isoformat(),
            'end_time': None,
            'duration': None,
            'stages': {},
            'errors': [],
            'cost_summary': {
                'total_cost': 0.0,
                'token_usage': 0,
                'budget_remaining': COST_OPTIMIZATION['target_daily_cost']
            }
        }

        pipeline_start_time = time.time()

        try:
            # Execute each stage in order
            for stage in stages_to_run:
                if self._should_skip_stage(stage, date, results):
                    logger.info(f"Skipping {stage.value} due to previous failures or budget constraints")
                    continue

                stage_result = self._execute_stage(stage, date)
                results['stages'][stage.value] = stage_result

                if stage_result['success']:
                    results['stages_completed'] += 1
                    logger.info(f"Stage {stage.value} completed successfully")
                else:
                    results['errors'].append(f"{stage.value}: {stage_result.get('error', 'Unknown error')}")
                    logger.error(f"Stage {stage.value} failed: {stage_result.get('error')}")

                    # Check if we should continue or abort
                    if not self._should_continue_after_failure(stage, stage_result):
                        logger.error(f"Aborting pipeline after {stage.value} failure")
                        break

                # Update cost tracking
                self._update_cost_summary(results, stage_result)

                # Check budget after each stage
                if cost_tracker.is_budget_exceeded(date):
                    logger.warning("Daily budget exceeded, stopping pipeline")
                    results['errors'].append("Daily budget exceeded")
                    break

                # Brief pause between stages
                time.sleep(1)

            # Calculate final results
            pipeline_duration = time.time() - pipeline_start_time
            results['duration'] = pipeline_duration
            results['end_time'] = datetime.utcnow().isoformat()

            # Determine final pipeline status
            if results['stages_completed'] == results['total_stages']:
                results['pipeline_status'] = 'completed'
            elif results['stages_completed'] > 0:
                results['pipeline_status'] = 'partial'
            else:
                results['pipeline_status'] = 'failed'

            logger.info(f"Pipeline {results['pipeline_status']}: {results['stages_completed']}/{results['total_stages']} stages completed in {pipeline_duration:.2f}s")

            # Update final cost summary
            results['cost_summary']['budget_remaining'] = max(0,
                COST_OPTIMIZATION['target_daily_cost'] - cost_tracker.get_daily_cost(date))

            return results

        except Exception as e:
            logger.error(f"Pipeline orchestration error: {str(e)}")
            results['pipeline_status'] = 'error'
            results['errors'].append(f"Orchestration error: {str(e)}")
            results['end_time'] = datetime.utcnow().isoformat()
            results['duration'] = time.time() - pipeline_start_time
            return results

    def _execute_stage(self, stage: PipelineStage, date: str) -> Dict[str, Any]:
        """
        Execute a single pipeline stage

        Args:
            stage: Pipeline stage to execute
            date: Processing date

        Returns:
            Stage execution results
        """
        logger.info(f"Executing stage: {stage.value}")
        stage_start_time = time.time()

        try:
            engine = self.engines[stage]

            # Execute the appropriate engine method
            if stage == PipelineStage.RSS_COLLECTION:
                result = engine.collect_daily_articles(date)
            elif stage == PipelineStage.CATEGORIZATION:
                result = engine.categorize_daily_articles(date)
            elif stage == PipelineStage.RANKING:
                result = engine.rank_daily_articles(date)
            elif stage == PipelineStage.BRIEF_GENERATION:
                result = engine.generate_daily_briefs(date)
            elif stage == PipelineStage.AUDIO_GENERATION:
                result = engine.generate_daily_audio(date)
            else:
                raise ValueError(f"Unknown stage: {stage}")

            # Standardize result format
            stage_result = {
                'success': True,
                'stage': stage.value,
                'duration': time.time() - stage_start_time,
                'result': result
            }

            # Extract key metrics
            if 'errors' in result and result['errors']:
                stage_result['warnings'] = result['errors']

            return stage_result

        except Exception as e:
            logger.error(f"Stage {stage.value} execution failed: {str(e)}")
            return {
                'success': False,
                'stage': stage.value,
                'error': str(e),
                'duration': time.time() - stage_start_time
            }

    def _should_skip_stage(self, stage: PipelineStage, date: str, current_results: Dict) -> bool:
        """
        Determine if a stage should be skipped

        Args:
            stage: Pipeline stage
            date: Processing date
            current_results: Current pipeline results

        Returns:
            True if stage should be skipped
        """
        # Check if budget is already exceeded
        if cost_tracker.is_budget_exceeded(date):
            return True

        # Check if previous critical stages failed
        critical_dependencies = {
            PipelineStage.CATEGORIZATION: [PipelineStage.RSS_COLLECTION],
            PipelineStage.RANKING: [PipelineStage.RSS_COLLECTION, PipelineStage.CATEGORIZATION],
            PipelineStage.BRIEF_GENERATION: [PipelineStage.RANKING],
            PipelineStage.AUDIO_GENERATION: [PipelineStage.BRIEF_GENERATION]
        }

        if stage in critical_dependencies:
            for dependency in critical_dependencies[stage]:
                dep_result = current_results['stages'].get(dependency.value)
                if not dep_result or not dep_result.get('success'):
                    logger.warning(f"Skipping {stage.value} due to failed dependency: {dependency.value}")
                    return True

        return False

    def _should_continue_after_failure(self, failed_stage: PipelineStage, stage_result: Dict) -> bool:
        """
        Determine if pipeline should continue after a stage failure

        Args:
            failed_stage: The stage that failed
            stage_result: Results from the failed stage

        Returns:
            True if pipeline should continue
        """
        # Critical stages that should stop the pipeline
        critical_stages = [
            PipelineStage.RSS_COLLECTION,
            PipelineStage.CATEGORIZATION
        ]

        if failed_stage in critical_stages:
            return False

        # Check if it's a budget-related failure
        error_msg = stage_result.get('error', '').lower()
        if 'budget' in error_msg or 'cost' in error_msg:
            return False

        # For non-critical stages, continue with warnings
        return True

    def _update_cost_summary(self, results: Dict, stage_result: Dict):
        """Update cost tracking in results"""
        if not stage_result.get('success'):
            return

        stage_data = stage_result.get('result', {})

        # Extract cost information from different stages
        cost_usd = stage_data.get('cost_usd', 0.0)
        token_usage = stage_data.get('token_usage', 0)

        results['cost_summary']['total_cost'] += cost_usd
        results['cost_summary']['token_usage'] += token_usage

    def get_pipeline_status(self, date: str) -> Dict[str, Any]:
        """
        Get current pipeline status for a date

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Pipeline status information
        """
        job = self.job_model.get_job(date)
        if not job:
            return {
                'date': date,
                'status': 'not_started',
                'message': 'No pipeline job found for this date'
            }

        engines = job.get('engines', {})

        status_summary = {
            'date': date,
            'job_id': job['job_id'],
            'overall_status': job.get('status'),
            'created_at': job.get('created_at'),
            'started_at': job.get('started_at'),
            'completed_at': job.get('completed_at'),
            'engines': {}
        }

        # Get status of each engine
        for stage in self.pipeline_order:
            engine_name = f"{stage.value}_engine"
            engine_data = engines.get(engine_name, {})

            status_summary['engines'][stage.value] = {
                'status': engine_data.get('status', 'pending'),
                'started_at': engine_data.get('started_at'),
                'completed_at': engine_data.get('completed_at'),
                'duration': engine_data.get('duration'),
                'error_message': engine_data.get('error_message')
            }

        return status_summary

    def retry_failed_stages(self, date: str, stages: List[str] = None) -> Dict[str, Any]:
        """
        Retry failed stages of the pipeline

        Args:
            date: Date in YYYY-MM-DD format
            stages: Specific stages to retry (defaults to failed ones)

        Returns:
            Retry results
        """
        logger.info(f"Retrying failed stages for {date}")

        # Get current pipeline status
        status = self.get_pipeline_status(date)

        if not stages:
            # Identify failed stages
            failed_stages = []
            for stage_name, engine_status in status['engines'].items():
                if engine_status['status'] == 'failed':
                    failed_stages.append(stage_name)
            stages = failed_stages

        if not stages:
            return {
                'message': 'No failed stages to retry',
                'date': date
            }

        # Run pipeline with only the specified stages
        return self.run_daily_pipeline(date, stages)


def lambda_handler(event, context):
    """
    AWS Lambda handler for pipeline orchestration

    Expected event format:
    {
        "action": "run_pipeline",  # run_pipeline, get_status, retry_failed
        "date": "2024-01-15",      # optional, defaults to today
        "stages": ["rss_collection", "categorization"]  # optional, specific stages to run
    }
    """
    try:
        action = event.get('action', 'run_pipeline')
        date = event.get('date')
        stages = event.get('stages')

        orchestrator = PipelineOrchestrator()

        if action == 'run_pipeline':
            results = orchestrator.run_daily_pipeline(date, stages)
            return {
                'statusCode': 200,
                'body': results
            }
        elif action == 'get_status':
            status = orchestrator.get_pipeline_status(date or datetime.utcnow().strftime('%Y-%m-%d'))
            return {
                'statusCode': 200,
                'body': status
            }
        elif action == 'retry_failed':
            results = orchestrator.retry_failed_stages(date, stages)
            return {
                'statusCode': 200,
                'body': results
            }
        else:
            return {
                'statusCode': 400,
                'body': {'error': f'Unknown action: {action}'}
            }

    except Exception as e:
        logger.error(f"Orchestrator lambda error: {str(e)}")
        return {
            'statusCode': 500,
            'body': {'error': str(e)}
        }


if __name__ == '__main__':
    # For local testing
    orchestrator = PipelineOrchestrator()
    results = orchestrator.run_daily_pipeline()
    print(f"Pipeline completed: {results}")