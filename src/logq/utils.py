from .async_logger import get_async_logger
from functools import wraps
import time


def log_function_call(func=None, *, level='INFO'):
    """
    Decorator to automatically log function calls.
    
    Usage:
        @log_function_call
        def my_function():
            pass
        
        @log_function_call(level='DEBUG')
        def my_debug_function():
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_async_logger()
            
            # Log function entry
            logger.log(
                level,
                f"Entering function: {func.__name__}",
                extra_data={
                    'args_count': len(args),
                    'kwargs_keys': list(kwargs.keys()),
                    'module': func.__module__,
                }
            )
            
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                execution_time = time.perf_counter() - start_time
                
                # Log successful completion
                logger.log(
                    level,
                    f"Function completed: {func.__name__} (took {execution_time:.3f}s)",
                    extra_data={'execution_time': execution_time}
                )
                
                return result
            
            except Exception as e:
                execution_time = time.perf_counter() - start_time
                
                # Log exception
                logger.exception(
                    f"Function failed: {func.__name__} (took {execution_time:.3f}s)",
                    exc_info=str(e),
                    extra_data={'execution_time': execution_time}
                )
                raise
        
        return wrapper
    
    if func is None:
        return decorator
    return decorator(func)


def log_performance(threshold_seconds=1.0, always_log=False):
    """
    Decorator to log function performance metrics.
    
    Args:
        threshold_seconds: Log warning when execution exceeds this threshold
        always_log: If True, log every function call for analytics (like Sentry spans)
    
    Usage:
        @log_performance(threshold_seconds=0.5)
        def my_slow_function():
            pass
        
        @log_performance(always_log=True)
        def my_analytics_function():
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            execution_time = time.perf_counter() - start_time
            
            logger = get_async_logger()
            
            # Always log for analytics if requested
            if always_log:
                logger.info(
                    f"Function performance: {func.__name__}",
                    extra_data={
                        'execution_time': execution_time,
                        'function_name': func.__name__,
                        'module': func.__module__,
                        'performance_metric': True,  # Tag for easy filtering
                    }
                )
            
            # Log warning if threshold exceeded
            if execution_time > threshold_seconds:
                logger.warning(
                    f"Slow function detected: {func.__name__} took {execution_time:.3f}s",
                    extra_data={
                        'execution_time': execution_time,
                        'threshold': threshold_seconds,
                        'module': func.__module__,
                        'function_name': func.__name__,
                        'performance_metric': True,
                    }
                )
            
            return result
        return wrapper
    return decorator


class LogContext:
    """
    Context manager for logging operations with automatic timing.
    
    Usage:
        with LogContext("Processing data", level='INFO'):
            # do some work
            pass
    """
    
    def __init__(self, message, level='INFO', **kwargs):
        self.message = message
        self.level = level
        self.kwargs = kwargs
        self.logger = get_async_logger()
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        self.logger.log(
            self.level,
            f"Starting: {self.message}",
            **self.kwargs
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        execution_time = time.perf_counter() - self.start_time
        
        if exc_type is None:
            self.logger.log(
                self.level,
                f"Completed: {self.message} (took {execution_time:.3f}s)",
                extra_data={'execution_time': execution_time},
                **self.kwargs
            )
        else:
            self.logger.exception(
                f"Failed: {self.message} (took {execution_time:.3f}s)",
                exc_info=str(exc_val),
                extra_data={'execution_time': execution_time},
                **self.kwargs
            )