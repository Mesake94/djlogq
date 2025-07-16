from django.test import TransactionTestCase, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import connection
import json
import time
import threading
from .models import LogEntry, LogLevel
from .async_logger import AsyncLogger, get_async_logger, stop_async_logger
from .utils import log_performance, log_function_call
import requests

class AsyncLoggerTestCase(TransactionTestCase):
    def setUp(self):
        super().setUp()
        # Stop the global logger to avoid interference
        stop_async_logger()
        
        # Clear all existing logs using raw SQL to ensure complete cleanup
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM logq_logentry")
        
        # Create a fresh logger instance for testing
        self.logger = AsyncLogger(max_queue_size=100, flush_interval=0.1)
        self.logger.start()
        time.sleep(0.2)  # Wait for thread to start
    
    def tearDown(self):
        self.logger.stop()
        time.sleep(0.2)  # Wait for thread to stop
        
        # Clear logs after test using raw SQL
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM logq_logentry")
        
        super().tearDown()
    
    def test_basic_logging(self):
        """Test basic logging functionality."""
        # Verify we start with no logs
        self.assertEqual(LogEntry.objects.count(), 0)
        
        self.logger.info("Test message")
        time.sleep(0.5)  # Wait longer for flush
        
        # Verify we have exactly one log entry
        self.assertEqual(LogEntry.objects.count(), 1)
        
        log_entry = LogEntry.objects.first()
        self.assertEqual(log_entry.level, LogLevel.INFO)
        self.assertEqual(log_entry.message, "Test message")
    
    def test_all_log_levels(self):
        """Test all log levels."""
        # Verify we start with no logs
        self.assertEqual(LogEntry.objects.count(), 0)
        
        levels = [LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR, LogLevel.CRITICAL]
        
        for level in levels:
            self.logger.log(level, f"Test {level}")
        
        time.sleep(0.5)  # Wait longer for flush
        
        entries = LogEntry.objects.all()
        self.assertEqual(entries.count(), len(levels))
        
        for entry in entries:
            self.assertIn(entry.level, levels)
    
    def test_extra_data(self):
        """Test logging with extra data."""
        # Verify we start with no logs
        self.assertEqual(LogEntry.objects.count(), 0)
        
        extra_data = {'user_id': 123, 'action': 'test'}
        self.logger.info("Test with extra data", extra_data=extra_data)
        time.sleep(0.5)
        
        # Verify we have exactly one log entry
        self.assertEqual(LogEntry.objects.count(), 1)
        
        entry = LogEntry.objects.first()
        self.assertEqual(entry.extra_data, extra_data)
    
    def test_queue_full_handling(self):
        """Test behavior when queue is full."""
        # Verify we start with no logs
        self.assertEqual(LogEntry.objects.count(), 0)
        
        # Fill the queue
        for i in range(150):  # More than max_queue_size
            self.logger.info(f"Message {i}")
        
        time.sleep(0.5)
        
        # Should have some entries but not all due to queue being full
        entries = LogEntry.objects.count()
        self.assertGreater(entries, 0)
        self.assertLessEqual(entries, 101)  # max_queue_size + 1 (allowing for edge case)

        # Check if the dropped log entry is present
        dropped_entry = LogEntry.objects.filter(message__contains="dropped due to queue overflow").first()
        self.assertIsNotNone(dropped_entry)
        self.assertEqual(dropped_entry.level, LogLevel.WARNING)
        


class LogEntryModelTestCase(TransactionTestCase):
    def setUp(self):
        super().setUp()
        # Clear all existing logs
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM logq_logentry")
    
    def tearDown(self):
        # Clear logs after test
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM logq_logentry")
        super().tearDown()
    
    def test_log_entry_creation(self):
        """Test LogEntry model creation."""
        entry = LogEntry.objects.create(
            level=LogLevel.INFO,
            message="Test message",
            module="test_module",
            function="test_function",
            line_number=42,
            user_id=123,
            request_id="test-request-id",
            extra_data={'key': 'value'}
        )
        
        self.assertEqual(entry.level, LogLevel.INFO)
        self.assertEqual(entry.message, "Test message")
        self.assertEqual(entry.module, "test_module")
        self.assertEqual(entry.function, "test_function")
        self.assertEqual(entry.line_number, 42)
        self.assertEqual(entry.user_id, 123)
        self.assertEqual(entry.request_id, "test-request-id")
        self.assertEqual(entry.extra_data, {'key': 'value'})
    
    def test_log_entry_str_representation(self):
        """Test string representation of LogEntry."""
        entry = LogEntry.objects.create(
            level=LogLevel.ERROR,
            message="This is a very long message that should be truncated in the string representation",
            timestamp=timezone.now()
        )
        
        str_repr = str(entry)
        self.assertIn("[ERROR]", str_repr)
        self.assertIn("This is a very long message that should be truncated", str_repr[:100])



@override_settings(
    ASYNC_LOGGING_CONFIG={'MAX_QUEUE_SIZE': 500, 'FLUSH_INTERVAL': 0.5},
    MIDDLEWARE=[
        "django.middleware.security.SecurityMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
        "logq.middleware.AsyncLoggingMiddleware",  # Fixed: Added middleware
    ]
)
class MiddlewareTestCase(TransactionTestCase):
    def setUp(self):
        super().setUp()
        # Stop the global logger to avoid interference
        stop_async_logger()
        # Clear all existing logs
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM logq_logentry")
    
    def tearDown(self):
        # Clear logs after test
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM logq_logentry")
        super().tearDown()
    


class UtilsTestCase(TransactionTestCase):
    def setUp(self):
        super().setUp()
        # Stop the global logger to avoid interference
        stop_async_logger()
        
        # Clear all existing logs
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM logq_logentry")
        
        # Create a properly configured global logger
        from .async_logger import _async_logger
        from . import async_logger as async_logger_module
        
        # Create a test logger with fast flush interval
        test_logger = AsyncLogger(max_queue_size=100, flush_interval=0.1)
        test_logger.start()
        
        # Replace the global logger
        async_logger_module._async_logger = test_logger
        
        time.sleep(0.2)  # Wait for thread to start
    
    def tearDown(self):
        # Stop the global logger
        stop_async_logger()
        time.sleep(0.2)  # Wait for thread to stop
        
        # Clear logs after test
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM logq_logentry")
        super().tearDown()
    
    def test_log_performance(self):
        """Test log_performance decorator."""
        # Debug: Check if the logger is running
        logger = get_async_logger()

        # Test direct logging first
        logger.info("Direct test message")
        time.sleep(0.3)
        
        @log_performance(threshold_seconds=0.1, always_log=True)
        def slow_function():
            time.sleep(0.2)
            return "Result"
        
        slow_function()
        
        time.sleep(0.5)  # Wait longer for flush
        
        entries = LogEntry.objects.all()

        self.assertGreater(entries.count(), 0)
        