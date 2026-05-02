from textual.widgets import RichLog
from typing import List, Dict, Any


class LogViewer(RichLog):
    """A custom widget for displaying logs with color coding."""

    DEFAULT_CSS = """
    LogViewer {
        border: solid #b9982f;
        margin: 1 0;
        height: 1fr;
    }
    """

    def __init__(self):
        super().__init__(
            highlight=True,
            markup=True,
        )

    def load_logs(self, logs: List[Dict[str, Any]]) -> None:
        """Load logs into the viewer."""
        self.clear()

        if not logs:
            self.write("[yellow]No logs available[/yellow]")
            return

        # Display logs in reverse order (most recent first)
        for log_entry in reversed(logs):
            self._write_log_entry(log_entry)

    def _write_log_entry(self, log_entry: Dict[str, Any]) -> None:
        """Write a single log entry with proper formatting and color coding."""
        level = log_entry.get("level", "INFO").upper()
        message = log_entry.get("message", "")
        timestamp = log_entry.get("timestamp", "")

        # Color code by log level
        if level == "ERROR":
            color = "red"
        elif level == "WARNING":
            color = "yellow"
        elif level == "DEBUG":
            color = "blue"
        else:
            color = "green"

        # Format: [timestamp] LEVEL: message
        log_line = f"[{color}][{timestamp}] {level}:[/{color}] {message}"
        self.write(log_line)

    def add_log(self, level: str, message: str, timestamp: str) -> None:
        """Add a single log entry."""
        self._write_log_entry({
            "level": level,
            "message": message,
            "timestamp": timestamp
        })
