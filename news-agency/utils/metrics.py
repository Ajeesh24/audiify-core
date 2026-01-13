"""
Metrics utility for tracking cost, performance, and usage
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional
from config import COST_OPTIMIZATION, OPENAI_SETTINGS
from utils.logger import get_logger, log_cost_metrics

logger = get_logger(__name__)


class CostTracker:
    """
    Track costs for the news agency pipeline
    Helps stay within the $0.50/day budget
    """

    # OpenAI pricing (as of 2024)
    OPENAI_PRICING = {
        'gpt-4o-mini': {
            'input': 0.000150 / 1000,   # $0.000150 per 1K input tokens
            'output': 0.000600 / 1000   # $0.000600 per 1K output tokens
        },
        'gpt-3.5-turbo': {
            'input': 0.0005 / 1000,     # $0.0005 per 1K input tokens
            'output': 0.0015 / 1000     # $0.0015 per 1K output tokens
        }
    }

    # ElevenLabs pricing (approximate)
    ELEVENLABS_PRICING = {
        'characters': 0.00003  # ~$0.03 per 1000 characters
    }

    def __init__(self):
        self.daily_costs = {}
        self.token_usage = {}

    def track_llm_usage(self, operation: str, model: str, input_tokens: int, output_tokens: int) -> float:
        """
        Track LLM token usage and calculate cost

        Args:
            operation: Operation name (categorization, brief_generation, etc.)
            model: Model used (gpt-4o-mini, etc.)
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        date = datetime.utcnow().strftime('%Y-%m-%d')

        if date not in self.daily_costs:
            self.daily_costs[date] = {}
        if date not in self.token_usage:
            self.token_usage[date] = {}

        if operation not in self.daily_costs[date]:
            self.daily_costs[date][operation] = 0
        if operation not in self.token_usage[date]:
            self.token_usage[date][operation] = {'input': 0, 'output': 0}

        # Calculate cost
        pricing = self.OPENAI_PRICING.get(model, self.OPENAI_PRICING['gpt-4o-mini'])
        cost = (input_tokens * pricing['input']) + (output_tokens * pricing['output'])

        # Track totals
        self.daily_costs[date][operation] += cost
        self.token_usage[date][operation]['input'] += input_tokens
        self.token_usage[date][operation]['output'] += output_tokens

        # Log for monitoring
        log_cost_metrics(operation, cost, input_tokens + output_tokens, logger)

        return cost

    def track_audio_usage(self, operation: str, characters: int) -> float:
        """
        Track audio generation usage and cost

        Args:
            operation: Operation name
            characters: Number of characters processed

        Returns:
            Cost in USD
        """
        date = datetime.utcnow().strftime('%Y-%m-%d')

        if date not in self.daily_costs:
            self.daily_costs[date] = {}

        if operation not in self.daily_costs[date]:
            self.daily_costs[date][operation] = 0

        cost = characters * self.ELEVENLABS_PRICING['characters']
        self.daily_costs[date][operation] += cost

        return cost

    def get_daily_cost(self, date: Optional[str] = None) -> float:
        """Get total daily cost"""
        if not date:
            date = datetime.utcnow().strftime('%Y-%m-%d')

        return sum(self.daily_costs.get(date, {}).values())

    def get_daily_tokens(self, date: Optional[str] = None) -> Dict[str, int]:
        """Get total daily token usage"""
        if not date:
            date = datetime.utcnow().strftime('%Y-%m-%d')

        daily_usage = self.token_usage.get(date, {})
        total_input = sum(op['input'] for op in daily_usage.values())
        total_output = sum(op['output'] for op in daily_usage.values())

        return {
            'input_tokens': total_input,
            'output_tokens': total_output,
            'total_tokens': total_input + total_output
        }

    def is_budget_exceeded(self, date: Optional[str] = None) -> bool:
        """Check if daily budget is exceeded"""
        daily_cost = self.get_daily_cost(date)
        return daily_cost >= COST_OPTIMIZATION['target_daily_cost']

    def get_remaining_budget(self, date: Optional[str] = None) -> float:
        """Get remaining daily budget"""
        daily_cost = self.get_daily_cost(date)
        return max(0, COST_OPTIMIZATION['target_daily_cost'] - daily_cost)


class PerformanceTracker:
    """
    Track performance metrics for the pipeline
    """

    def __init__(self):
        self.timings = {}
        self.metrics = {}

    def start_timer(self, operation: str) -> str:
        """Start timing an operation"""
        timer_id = f"{operation}_{int(time.time() * 1000)}"
        self.timings[timer_id] = {
            'operation': operation,
            'start_time': time.time(),
            'end_time': None,
            'duration': None
        }
        return timer_id

    def end_timer(self, timer_id: str) -> float:
        """End timing and return duration"""
        if timer_id not in self.timings:
            return 0

        self.timings[timer_id]['end_time'] = time.time()
        duration = self.timings[timer_id]['end_time'] - self.timings[timer_id]['start_time']
        self.timings[timer_id]['duration'] = duration

        return duration

    def record_metric(self, metric_name: str, value: Any):
        """Record a custom metric"""
        date = datetime.utcnow().strftime('%Y-%m-%d')

        if date not in self.metrics:
            self.metrics[date] = {}

        self.metrics[date][metric_name] = value

    def get_average_duration(self, operation: str, days: int = 7) -> float:
        """Get average duration for an operation over recent days"""
        durations = []
        for timing in self.timings.values():
            if timing['operation'] == operation and timing['duration'] is not None:
                durations.append(timing['duration'])

        return sum(durations) / len(durations) if durations else 0


# Global instances
cost_tracker = CostTracker()
performance_tracker = PerformanceTracker()


def time_operation(operation_name: str):
    """
    Decorator to time operations

    Usage:
        @time_operation('rss_collection')
        def collect_articles():
            pass
    """
    def decorator(func):
        from functools import wraps

        @wraps(func)
        def wrapper(*args, **kwargs):
            timer_id = performance_tracker.start_timer(operation_name)

            try:
                result = func(*args, **kwargs)
                duration = performance_tracker.end_timer(timer_id)

                logger.info(
                    f"Operation completed",
                    extra={
                        'operation': operation_name,
                        'duration_seconds': round(duration, 3),
                        'success': True
                    }
                )

                return result

            except Exception as e:
                duration = performance_tracker.end_timer(timer_id)

                logger.error(
                    f"Operation failed",
                    extra={
                        'operation': operation_name,
                        'duration_seconds': round(duration, 3),
                        'success': False,
                        'error': str(e)
                    }
                )

                raise

        return wrapper
    return decorator


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text
    Rough approximation: ~4 characters per token for English text
    """
    return len(text) // 4


def calculate_llm_cost(text: str, model: str = None, response_length: int = None) -> float:
    """
    Calculate estimated LLM cost for processing text

    Args:
        text: Input text
        model: Model name (defaults to configured model)
        response_length: Expected response length in tokens

    Returns:
        Estimated cost in USD
    """
    if not model:
        model = OPENAI_SETTINGS['model']

    input_tokens = estimate_tokens(text)
    output_tokens = response_length or OPENAI_SETTINGS['max_tokens']

    pricing = CostTracker.OPENAI_PRICING.get(model, CostTracker.OPENAI_PRICING['gpt-4o-mini'])
    cost = (input_tokens * pricing['input']) + (output_tokens * pricing['output'])

    return cost