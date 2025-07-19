from .models import LogEntry
import sys

class LogHandler:
    """Base class for custom log handlers"""

    def handle(self, log_entry:LogEntry) -> None:
        """Handle a log entry. Overide this method to implement custom logging behavior."""
        pass

    def flush(self) -> None:
        """Flush any buffered log entries. Override this method to implement custom flushing behavior."""
        pass


class ConsoleHandler(LogHandler):

  def __init__(self):
    self.buffer = []
  
  def handle(self, log_entry):
    self.buffer.append({
      "message": log_entry.message,
      "level": log_entry.level,
      "timestamp": log_entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
    })

  def flush(self):
    if not self.buffer:
      return
    lines = []
    for entry in self.buffer:
      line = (
        f"[{entry['timestamp']}] "
        f"{entry['level']}: "
        f"{entry['message']} "
      )
      lines.append(line)
    sys.stdout.write('\n'.join(lines) + '\n')
    sys.stdout.flush()
    self.buffer.clear()