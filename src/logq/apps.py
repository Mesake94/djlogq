from django.apps import AppConfig
from django.conf import settings
import os


class LogqConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'logq'
    verbose_name = 'LogQ'

    def ready(self):
        """Initialize the async logger when the app is ready."""
        # Prevent multiple initializations during development server reload
        # RUN_MAIN is set to 'true' only in the child process that actually runs the app
        if os.environ.get('RUN_MAIN') != 'true':
            return
            
        from .async_logger import get_async_logger
        from .cleanup_service import start_cleanup_service

        get_async_logger()
        # dont start the cleanup service in test mode
        start_cleanup_service()