from django.db import models

from django.utils import timezone
import json


class LogLevel(models.TextChoices):
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    CRITICAL = 'CRITICAL'

class LogEntry(models.Model):
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)  # index for faster queries
    level = models.CharField(max_length=10, choices=LogLevel.choices)
    message = models.TextField()
    module = models.CharField(max_length=255, null=True, blank=True)
    function = models.CharField(max_length=255, null=True, blank=True)
    line_number = models.IntegerField(null=True, blank=True)
    user_id = models.IntegerField(null=True, blank=True)
    request_id = models.CharField(max_length=255, null=True, blank=True)
    extra_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        ordering = ['-timestamp']
        indexes = [  # index for faster queries
            models.Index(fields=['timestamp']),
            models.Index(fields=['level']),
            models.Index(fields=['module']),
            models.Index(fields=['function']),
            models.Index(fields=['line_number']),
            models.Index(fields=['user_id']),
            models.Index(fields=['request_id']),
        ]
        verbose_name = 'Log Entry'
        verbose_name_plural = 'Log Entries'

    def __str__(self):
        """Return a string representation of the log entry."""
        return f"[{self.level}] {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {self.message[:100]}"
  