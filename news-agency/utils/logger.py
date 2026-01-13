"""
Logging utility for the news agency system

Provides structured logging with CloudWatch integration
"""

import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict
from config import LOGGING, ENVIRONMENT, is_production


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter for structured logging
    Outputs JSON format in production, human-readable in development
    """

    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        # Add extra fields if present
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'exc_info', 'exc_text', 'stack_info']:
                log_entry[key] = value

        if is_production():
            return json.dumps(log_entry)
        else:
            # Human readable format for development
            timestamp = log_entry['timestamp']
            level = log_entry['level']
            logger_name = log_entry['logger']
            message = log_entry['message']
            location = f"{log_entry['module']}:{log_entry['function']}:{log_entry['line']}"

            formatted = f"{timestamp} - {level} - {logger_name} - {message} ({location})"

            if 'exception' in log_entry:
                formatted += f"\n{log_entry['exception']}"

            return formatted


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Set level
    level = getattr(logging, LOGGING['level'].upper(), logging.INFO)
    logger.setLevel(level)

    # Create handler
    if is_production() and LOGGING['enable_cloudwatch_logs']:
        # In production with CloudWatch, Lambda runtime will handle the output
        handler = logging.StreamHandler(sys.stdout)
    else:
        # Development or non-CloudWatch production
        handler = logging.StreamHandler(sys.stderr)

    # Set formatter
    if LOGGING['enable_structured_logging']:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(LOGGING['format'])

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def log_performance(func):
    """
    Decorator to log function performance metrics

    Usage:
        @log_performance
        def my_function():
            pass
    """
    import time
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            logger.info(
                f"Function completed successfully",
                extra={
                    'function': func.__name__,
                    'execution_time_seconds': round(execution_time, 3),
                    'success': True
                }
            )

            return result

        except Exception as e:
            execution_time = time.time() - start_time

            logger.error(
                f"Function failed with error: {str(e)}",
                extra={
                    'function': func.__name__,
                    'execution_time_seconds': round(execution_time, 3),
                    'success': False,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                },
                exc_info=True
            )

            raise

    return wrapper


def log_engine_start(engine_name: str, date: str, logger: logging.Logger):
    """Log engine start with structured data"""
    logger.info(
        f"Starting {engine_name} engine",
        extra={
            'engine': engine_name,
            'processing_date': date,
            'event': 'engine_start'
        }
    )


def log_engine_complete(engine_name: str, date: str, metrics: Dict[str, Any], logger: logging.Logger):
    """Log engine completion with metrics"""
    logger.info(
        f"Completed {engine_name} engine",
        extra={
            'engine': engine_name,
            'processing_date': date,
            'event': 'engine_complete',
            'metrics': metrics
        }
    )


def log_engine_error(engine_name: str, date: str, error: str, logger: logging.Logger):
    """Log engine error"""
    logger.error(
        f"Failed {engine_name} engine: {error}",
        extra={
            'engine': engine_name,
            'processing_date': date,
            'event': 'engine_error',
            'error_message': error
        }
    )


def log_cost_metrics(operation: str, cost: float, tokens: int, logger: logging.Logger):
    """Log cost and token usage metrics"""
    logger.info(
        f"Cost metrics for {operation}",
        extra={
            'operation': operation,
            'cost_usd': cost,
            'tokens_used': tokens,
            'event': 'cost_tracking'
        }
    )


def log_api_request(endpoint: str, method: str, status_code: int, duration: float, logger: logging.Logger):
    """Log API request metrics"""
    logger.info(
        f"API request completed",
        extra={
            'endpoint': endpoint,
            'method': method,
            'status_code': status_code,
            'duration_seconds': round(duration, 3),
            'event': 'api_request'
        }
    )