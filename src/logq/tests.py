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
        self.assertLessEqual(entries, 100)  # max_queue_size


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


class LoggingAPITestCase(TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username='testuser', password='testpass')
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
    
    def test_log_endpoint(self):
        """Test the log API endpoint."""
        # Verify we start with no logs
        self.assertEqual(LogEntry.objects.count(), 0)
        
        data = {
            'level': 'INFO',
            'message': 'Test API log',
            'extra_data': {'source': 'api'}
        }
        
        response = self.client.post(
            reverse('logq:log_endpoint'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        
        # Wait for async processing
        time.sleep(0.5)
        
        # Verify we have exactly one log entry
        self.assertEqual(LogEntry.objects.count(), 1)
        
        entry = LogEntry.objects.first()
        self.assertEqual(entry.message, 'Test API log')
        self.assertEqual(entry.extra_data, {'source': 'api'})
    
    def test_log_api_view(self):
        """Test the class-based log API view."""
        # Verify we start with no logs
        self.assertEqual(LogEntry.objects.count(), 0)
        
        data = {
            'level': 'WARNING',
            'message': 'Test warning',
            'user_id': self.user.id,
            'request_id': 'test-123'
        }
        
        response = self.client.post(
            reverse('logq:log_api'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        time.sleep(0.5)
        
        # Verify we have exactly one log entry
        self.assertEqual(LogEntry.objects.count(), 1)
        
        entry = LogEntry.objects.first()
        self.assertEqual(entry.level, LogLevel.WARNING)
        self.assertEqual(entry.user_id, self.user.id)
        self.assertEqual(entry.request_id, 'test-123')
    
    def test_get_logs_api(self):
        """Test retrieving logs via API."""
        # Verify we start with no logs
        self.assertEqual(LogEntry.objects.count(), 0)
        
        # Create some test logs directly
        LogEntry.objects.create(level=LogLevel.INFO, message="Test 1")
        LogEntry.objects.create(level=LogLevel.ERROR, message="Test 2")
        LogEntry.objects.create(level=LogLevel.DEBUG, message="Test 3")
        
        # Verify we have exactly 3 logs
        self.assertEqual(LogEntry.objects.count(), 3)
        
        response = self.client.get(reverse('logq:log_api'))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(len(data['logs']), 3)
        self.assertEqual(data['logs'][0]['message'], "Test 1")
    
    def test_invalid_log_level(self):
        """Test API with invalid log level."""
        data = {
            'level': 'INVALID',
            'message': 'Test message'
        }
        
        response = self.client.post(
            reverse('logq:log_endpoint'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid log level', response.json()['error'])


@override_settings(ASYNC_LOGGING_CONFIG={'MAX_QUEUE_SIZE': 500, 'FLUSH_INTERVAL': 0.5})
class ConfigurationTestCase(TransactionTestCase):
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
    
    def test_custom_configuration(self):
        """Test that custom configuration is respected."""
        logger = AsyncLogger()
        self.assertEqual(logger.queue.maxsize, 500)
        self.assertEqual(logger.flush_interval, 0.5)


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
    
    def test_middleware_request_logging(self):
        """Test that middleware logs requests."""
        # Verify we start with no logs
        self.assertEqual(LogEntry.objects.count(), 0)
        
        response = self.client.get('/admin/')
        
        time.sleep(0.5)
        
        entries = LogEntry.objects.all()
        self.assertGreater(entries.count(), 0)
        
        # Should have request start and completion logs
        start_logs = entries.filter(message__contains="Request started")
        complete_logs = entries.filter(message__contains="Request completed")
        
        self.assertGreater(start_logs.count(), 0)
        self.assertGreater(complete_logs.count(), 0)
