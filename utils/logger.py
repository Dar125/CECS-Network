"""
Structured Logging and Performance Monitoring for Multi-Agent Code Review System

Provides comprehensive logging with performance metrics, error tracking, and monitoring.
"""

import logging
import time
import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from functools import wraps
from contextlib import contextmanager
import threading

class PerformanceMonitor:
    """Tracks performance metrics for various operations"""
    
    def __init__(self):
        self.metrics = {}
        self._lock = threading.Lock()
    
    def record_metric(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a performance metric"""
        with self._lock:
            if metric_name not in self.metrics:
                self.metrics[metric_name] = []
            
            entry = {
                "value": value,
                "timestamp": time.time(),
                "tags": tags or {}
            }
            self.metrics[metric_name].append(entry)
    
    def get_stats(self, metric_name: str) -> Dict[str, float]:
        """Get statistics for a specific metric"""
        with self._lock:
            if metric_name not in self.metrics:
                return {}
            
            values = [m["value"] for m in self.metrics[metric_name]]
            if not values:
                return {}
            
            return {
                "count": len(values),
                "mean": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
                "latest": values[-1] if values else 0
            }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all metrics"""
        return {name: self.get_stats(name) for name in self.metrics.keys()}

# Global performance monitor instance
perf_monitor = PerformanceMonitor()

class StructuredLogger:
    """Enhanced logger with structured output and performance tracking"""
    
    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Remove default handlers
        self.logger.handlers = []
        
        # Create structured formatter
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(handler)
        
        self.context = {}
    
    def add_context(self, **kwargs):
        """Add persistent context to all log messages"""
        self.context.update(kwargs)
    
    def _log_with_context(self, level: int, message: str, **kwargs):
        """Log with additional context"""
        extra = {
            "context": {**self.context, **kwargs},
            "timestamp": datetime.utcnow().isoformat()
        }
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        if exception:
            kwargs["exception_type"] = type(exception).__name__
            kwargs["exception_message"] = str(exception)
            kwargs["traceback"] = traceback.format_exc()
        self._log_with_context(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log_with_context(logging.CRITICAL, message, **kwargs)

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": getattr(record, "timestamp", datetime.utcnow().isoformat()),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add context if available
        if hasattr(record, "context"):
            log_data["context"] = record.context
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        return json.dumps(log_data, default=str)

def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance"""
    return StructuredLogger(name)

@contextmanager
def log_performance(operation_name: str, logger: Optional[StructuredLogger] = None, **tags):
    """Context manager for logging operation performance"""
    start_time = time.time()
    
    if logger:
        logger.info(f"Starting {operation_name}", operation=operation_name, status="started")
    
    try:
        yield
        duration = time.time() - start_time
        
        # Record metric
        perf_monitor.record_metric(f"{operation_name}_duration", duration, tags)
        
        if logger:
            logger.info(
                f"Completed {operation_name}",
                operation=operation_name,
                status="completed",
                duration_seconds=duration
            )
    except Exception as e:
        duration = time.time() - start_time
        
        if logger:
            logger.error(
                f"Failed {operation_name}",
                exception=e,
                operation=operation_name,
                status="failed",
                duration_seconds=duration
            )
        raise

def track_performance(operation_name: Optional[str] = None):
    """Decorator for tracking function performance"""
    def decorator(func: Callable) -> Callable:
        nonlocal operation_name
        if operation_name is None:
            operation_name = func.__name__
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            with log_performance(operation_name):
                return func(*args, **kwargs)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with log_performance(operation_name):
                return await func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    
    return decorator

class APICallTracker:
    """Tracks API calls for cost monitoring"""
    
    def __init__(self):
        self.calls = []
        self._lock = threading.Lock()
    
    def track_call(self, 
                   api_name: str,
                   model: str,
                   input_tokens: int,
                   output_tokens: int,
                   duration: float,
                   cost: Optional[float] = None):
        """Track an API call"""
        with self._lock:
            call_data = {
                "api_name": api_name,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "duration": duration,
                "cost": cost or self._estimate_cost(model, input_tokens, output_tokens),
                "timestamp": time.time()
            }
            self.calls.append(call_data)
    
    def _estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost based on model and tokens"""
        # Pricing as of early 2025 (example rates)
        pricing = {
            "gpt-4o": {"input": 0.0025, "output": 0.01},  # per 1k tokens
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015}
        }
        
        if model not in pricing:
            return 0.0
        
        rates = pricing[model]
        cost = (input_tokens * rates["input"] / 1000) + (output_tokens * rates["output"] / 1000)
        return round(cost, 6)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of API usage"""
        with self._lock:
            if not self.calls:
                return {
                    "total_calls": 0,
                    "total_cost": 0.0,
                    "total_tokens": 0
                }
            
            total_calls = len(self.calls)
            total_cost = sum(call["cost"] for call in self.calls)
            total_input_tokens = sum(call["input_tokens"] for call in self.calls)
            total_output_tokens = sum(call["output_tokens"] for call in self.calls)
            
            by_model = {}
            for call in self.calls:
                model = call["model"]
                if model not in by_model:
                    by_model[model] = {
                        "calls": 0,
                        "cost": 0.0,
                        "input_tokens": 0,
                        "output_tokens": 0
                    }
                by_model[model]["calls"] += 1
                by_model[model]["cost"] += call["cost"]
                by_model[model]["input_tokens"] += call["input_tokens"]
                by_model[model]["output_tokens"] += call["output_tokens"]
            
            return {
                "total_calls": total_calls,
                "total_cost": round(total_cost, 4),
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_tokens": total_input_tokens + total_output_tokens,
                "by_model": by_model,
                "average_cost_per_call": round(total_cost / total_calls, 6) if total_calls > 0 else 0
            }

# Global API tracker instance
api_tracker = APICallTracker()

# Convenience function for quick setup
def setup_logging(level: str = "INFO", add_file_handler: bool = False, log_file: str = "app.log"):
    """Set up logging configuration for the entire application"""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(message)s',  # Let our formatter handle the format
        handlers=[]
    )
    
    # Add structured console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(StructuredFormatter())
    logging.root.addHandler(console_handler)
    
    # Add file handler if requested
    if add_file_handler:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(StructuredFormatter())
        logging.root.addHandler(file_handler)