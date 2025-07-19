import threading
import time
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.core.management import call_command
from typing import List
from .models import LogEntry
from .async_logger import get_async_logger


class CleanupPolicy:
  """Define cleanup policy for log entries."""

  def __init__(self, days:int, level:str=None, enabled:bool=True):
    self.days = days
    self.level = level
    self.enabled = enabled

  def __str__(self):
    level_str = f"level={self.level}" if self.level else "all levels"
    return f"Delete logs older than {self.days} days {level_str}"
  

class PeriodicCleanupService:
  """Service that periodically cleans up old log entries.
  Runs in a separate thread to avoid blocking the main application.
  """

  def __init__(self, policies:List[CleanupPolicy], check_interval:int=None):
    """Initialize the cleanup service:
    Args:
      policies: List of cleanup policies to apply.
      check_interval: Interval in seconds between cleanup runs.
    """
    self.policies = policies
    self.check_interval = check_interval or self._get_check_interval()

    self.running = False
    self.thread = None
    self._lock = threading.Lock()
    self.logger = get_async_logger()
    
    # Track last cleanup times for each policy
    self.last_cleanup = {}
    for policy in policies:
      self.last_cleanup[policy] = None

  def _get_check_interval(self) -> int:
    """Get the check interval from settings."""
    config = getattr(settings, 'ASYNC_LOGGING_CONFIG', {})
    return config.get('AUTO_CLEANUP_INTERVAL', 3600)
  
  def start(self):
    """Start the cleanup service."""
    with self._lock:  # Ensure thread safety
      if not self.running:  # Only start if not already running
        self.running = True
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()
        self.logger.info(f"Cleanup service started...")
      else:
        self.logger.info("Cleanup service already running")
    
  
  def stop(self):
    """Stop the cleanup service."""
    with self._lock:
      if self.running:
        self.running = False
        if self.thread:
          self.thread.join(timeout=10.0)  # Wait for thread to finish
        self.thread = None
        self.logger.info("Cleanup service stopped")
  
  def _worker(self):
    """Main worker thread that runs cleanup checks."""
    while self.running:
      try:
        self._check_cleanup()
        time.sleep(self.check_interval)
      except Exception as e:
        self.logger.error(f"Cleanup service has stopped: {e}")
        time.sleep(60)  # Wait for 1 minute before retrying
  
  def _check_cleanup(self):
    """Check if any cleanup policies should be applied."""
    with self._lock:
      now = timezone.now()
      for policy in self.policies:
        if not policy.enabled:
          self.logger.info(f"Cleanup policy {policy} is disabled")
          continue
        
        # Check if it's time to run this policy
        if self._should_run_policy(policy):
          self._run_cleanup_policy(policy)

  def _should_run_policy(self, policy:CleanupPolicy) -> bool:
    """Check if it's time to run this policy."""
    last_cleanup = self.last_cleanup.get(policy)
    if last_cleanup is None:
      return True
    
    # Check if the policy has been run in the last check interval
    return timezone.now() - last_cleanup > timedelta(seconds=self.check_interval)
  
  def _run_cleanup_policy(self, policy:CleanupPolicy):
    """Run the cleanup policy."""
    try:
      self.logger.info(f"Running cleanup policy: {policy}")
      args = [
        '--days', str(policy.days),
      ]
      if policy.level:
        args.extend(['--level', policy.level])
      
      # Run the cleanup command
      call_command('clean_logs', *args, verbosity=0)
      # Update the last cleanup time for this policy
      self.last_cleanup[policy] = timezone.now()
    except Exception as e:
      self.logger.error(f"Cleanup policy {policy} has failed: {e}")
  
_cleanup_service = None


def get_cleanup_service() -> PeriodicCleanupService:
  """
  Retrieve the singleton instance of the PeriodicCleanupService.

  This function ensures that only one instance of the PeriodicCleanupService exists
  throughout the application's lifecycle. If the service has not yet been created,
  it reads the cleanup policies from the Django settings (specifically from
  ASYNC_LOGGING_CONFIG['CLEANUP_POLICIES']), constructs CleanupPolicy objects for each
  policy, and initializes the PeriodicCleanupService with these policies and a default
  check interval of 10 seconds.

  Returns:
      PeriodicCleanupService: The singleton instance of the cleanup service, which
      periodically checks and applies log cleanup policies as configured.

  Notes:
      - The cleanup policies should be defined in Django settings under
        ASYNC_LOGGING_CONFIG['CLEANUP_POLICIES'] as a list of dictionaries, each
        representing a policy's parameters.
      - The service is thread-safe and intended to be started and stopped via
        start_cleanup_service() and stop_cleanup_service().

  Example:
      service = get_cleanup_service()
      service.start()
  """
  global _cleanup_service
  if _cleanup_service is None:
    # read the policies from the config
    policies = getattr(settings, 'ASYNC_LOGGING_CONFIG', {}).get('CLEANUP_POLICIES', [])
    policies = [CleanupPolicy(**policy) for policy in policies]
    _cleanup_service = PeriodicCleanupService(
      policies=policies,
      check_interval=10
    )
  return _cleanup_service


def start_cleanup_service():
  """
  Start the periodic log cleanup service.

  This function retrieves the singleton instance of the PeriodicCleanupService
  (which is responsible for periodically applying log cleanup policies as defined
  in the Django settings) and starts its background thread. If the service is
  already running, calling this function has no effect.

  Usage:
      start_cleanup_service()

  Notes:
      - The cleanup service will run in the background, periodically checking and
        applying the configured cleanup policies.
      - To stop the service, use stop_cleanup_service().
      - This function is thread-safe and can be called multiple times safely.

  See Also:
      - get_cleanup_service(): Retrieves the singleton cleanup service instance.
      - stop_cleanup_service(): Stops the running cleanup service.
  """
  service = get_cleanup_service()
  service.start()


def stop_cleanup_service():
  """
  Stop the periodic log cleanup service.

  This function retrieves the singleton instance of the PeriodicCleanupService
  (which is responsible for periodically applying log cleanup policies as defined
  in the Django settings) and stops its background thread. If the service is
  not running, calling this function has no effect.

  Usage:
      stop_cleanup_service()

  Notes:
      - This function is thread-safe and can be called multiple times safely.
      - The service will stop running after the current cleanup cycle completes.
  """
  global _cleanup_service
  if _cleanup_service:
    _cleanup_service.stop()
    _cleanup_service = None
