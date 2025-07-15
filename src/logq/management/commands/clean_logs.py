
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from logq.models import LogEntry


class Command(BaseCommand):
    help = 'Clean old log entries from the database'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=None,
            help='Delete logs older than this many days (default: from ASYNC_LOGGING_CONFIG)'
        )
        parser.add_argument(
            '--level',
            type=str,
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            help='Only delete logs of this level or lower'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
    
    def handle(self, *args, **options):
        # Get default days from settings
        config = getattr(settings, 'ASYNC_LOGGING_CONFIG', {})
        default_days = config.get('AUTO_CLEANUP_DAYS', 30)
        
        days = options['days'] if options['days'] is not None else default_days
        level = options['level']
        dry_run = options['dry_run']
        
        # Calculate cutoff date
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Build query
        query = LogEntry.objects.filter(timestamp__lt=cutoff_date)
        
        if level:
            # Get level hierarchy
            level_order = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            level_index = level_order.index(level)
            levels_to_delete = level_order[:level_index + 1]
            query = query.filter(level__in=levels_to_delete)
        
        count = query.count()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'Would delete {count} log entries older than {days} days'
                    + (f' with level {level} or lower' if level else '')
                )
            )
        else:
            deleted_count = query.delete()[0]
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully deleted {deleted_count} log entries older than {days} days'
                    + (f' with level {level} or lower' if level else '')
                )
            )