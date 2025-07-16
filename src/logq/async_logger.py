import threading
import queue
import time
import logging
import traceback
import inspect
from typing import Optional, Dict, Any
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from .models import LogEntry, LogLevel


class AsyncLogger:
    """
    Asynchronous logger that runs in a separate thread to avoid blocking the main application.
    """
    
    def __init__(self, max_queue_size: int = None, flush_interval: float = None):
        # Get configuration from settings
        config = getattr(settings, 'ASYNC_LOGGING_CONFIG', {})
        self.max_queue_size = max_queue_size or config.get('MAX_QUEUE_SIZE', 1000)
        self.flush_interval = flush_interval or config.get('FLUSH_INTERVAL', 1.0)
        
        self.queue = queue.Queue(maxsize=self.max_queue_size)
        self.running = False
        self.thread = None
        self._lock = threading.Lock()
        self.dropped_count = 0
        self.dropped_levels = {}  # track most serious dropped level
        self._dropped_lock = threading.Lock()  # 
        
    def start(self):
        """Start the logging thread."""
        with self._lock:
            if not self.running:
                self.running = True
                self.thread = threading.Thread(target=self._worker, daemon=True)
                self.thread.start()
    
    def stop(self):
        """Stop the logging thread."""
        with self._lock:
            if self.running:
                self.running = False
                if self.thread:
                    self.thread.join(timeout=5.0)
    
    def _worker(self):
        """Worker thread that processes log entries from the queue."""
        batch = []
        last_flush = time.time()
        
        while self.running:
            try:
                # Try to get a log entry with timeout
                try:
                    entry = self.queue.get(timeout=0.1)
                    batch.append(entry)
                except queue.Empty:
                    pass
                
                # Flush batch if it's time or batch is getting large
                current_time = time.time()
                if (current_time - last_flush >= self.flush_interval or 
                    len(batch) >= 50):
                    if batch:
                        self._flush_batch(batch)
                        batch = []
                        last_flush = current_time
                        
            except Exception as e:
                # Log the error to prevent infinite loops
                print(f"Error in async logger worker: {e}")
                time.sleep(1)
        
        # Flush remaining entries
        if batch:
            self._flush_batch(batch)
    
    def _flush_batch(self, batch):
        """Flush a batch of log entries to the database."""
        try:
            with transaction.atomic():
                LogEntry.objects.bulk_create(batch, ignore_conflicts=True)

                # Log dropped messages if any
                with self._dropped_lock:
                    if self.dropped_count > 0:
                        # Find the most serious dropped level
                        level_priority = {
                            'DEBUG': 0,
                            'INFO': 1,
                            'WARNING': 2,
                            'ERROR': 3,
                            'CRITICAL': 4
                        }
                        most_serious_level = max(self.dropped_levels.keys(), 
                                               key=lambda x: level_priority.get(x, 0)) if self.dropped_levels else 'INFO'
                        
                        dropped_entry = LogEntry(
                            level='WARNING',
                            message=f"{self.dropped_count} log messages were dropped due to queue overflow",
                            module='logq.async_logger',
                            function='_flush_batch',
                            extra_data={
                                'dropped_count': self.dropped_count,
                                'most_serious_level': most_serious_level
                            }
                        )
                        dropped_entry.save()
                        
                        self.dropped_count = 0
                        self.dropped_levels = {}

        except Exception as e:
            print(f"Error flushing log batch: {e}")
    
    def log(self, level: str, message: str, **kwargs):
        """Add a log entry to the queue."""
        if not self.running:
            return
        
        # Get caller information
        frame = inspect.currentframe().f_back
        module = frame.f_globals.get('__name__', 'unknown')
        function = frame.f_code.co_name
        line_number = frame.f_lineno
        
        # Create log entry
        entry = LogEntry(
            level=level,
            message=message,
            module=module,
            function=function,
            line_number=line_number,
            user_id=kwargs.get('user_id'),
            request_id=kwargs.get('request_id'),
            extra_data=kwargs.get('extra_data', {})
        )
        
        try:
            self.queue.put_nowait(entry)
        except queue.Full:
            # If queue is full, log to console as fallback
            # print(f"Log queue full, dropping entry: [{level}] {message}")
            # Track dropped messages with counter
            with self._dropped_lock:
                self.dropped_count += 1
                # Track the most serious level dropped
                level_priority = {
                    'DEBUG': 0,
                    'INFO': 1,
                    'WARNING': 2,
                    'ERROR': 3,
                    'CRITICAL': 4
                }
                current_priority = level_priority.get(level, 0)
                if level not in self.dropped_levels or current_priority > level_priority.get(self.dropped_levels[level], 0):
                    self.dropped_levels[level] = level
                self.dropped_levels[level] = level
                    
    
    def debug(self, message: str, **kwargs):
        self.log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self.log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self.log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self.log(LogLevel.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self.log(LogLevel.CRITICAL, message, **kwargs)
    
    def exception(self, message: str, exc_info=None, **kwargs):
        """Log an exception with traceback."""
        if exc_info is None:
            exc_info = traceback.format_exc()
        
        extra_data = kwargs.get('extra_data', {})
        extra_data['traceback'] = exc_info
        
        self.log(LogLevel.ERROR, message, extra_data=extra_data, **kwargs)


# Global logger instance
_async_logger = None


def get_async_logger() -> AsyncLogger:
    """Get the global async logger instance."""
    global _async_logger
    if _async_logger is None:
        _async_logger = AsyncLogger()
        _async_logger.start()
    return _async_logger


def stop_async_logger():
    """Stop the global async logger."""
    global _async_logger
    if _async_logger:
        _async_logger.stop()
        _async_logger = None

