from django.apps import AppConfig


class LogqConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'logq'
    verbose_name = 'LogQ'

    def ready(self):
        """Initialize the async logger when the app is ready."""
        from .async_logger import get_async_logger
        get_async_logger()