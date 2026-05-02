from textual.screen import Screen
from textual.widgets import Static, Button, RichLog
from textual.containers import Vertical, Horizontal
from textual import work

from app.client.api_client import get_logs


class LogsScreen(Screen):
    """Display recent logs from Python API."""

    CSS = """
    LogsScreen {
        layout: vertical;
    }

    #title {
        dock: top;
        height: 2;
        content-align: center middle;
        text-style: bold;
        color: #8f9a4d;
        background: #2f341e;
    }

    #logs_container {
        border: solid #b9982f;
        margin: 1 0;
    }

    #controls {
        height: auto;
        dock: bottom;
        margin: 0 2;
    }

    #controls Button {
        margin: 0 1;
    }
    """

    def compose(self):
        """Compose logs screen layout."""
        yield Static("RECENT LOGS", id="title")

        self.log_display = RichLog(
            highlight=True,
            markup=True,
            id="logs_container"
        )
        yield self.log_display

        with Horizontal(id="controls"):
            yield Button("🔄 Refresh", id="refresh", variant="primary")
            yield Button("🗑️  Clear", id="clear")
            yield Button("⬅ Back", id="back")

    def on_mount(self):
        """Initialize and load logs."""
        self.load_logs()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "refresh":
            self.load_logs()
        elif event.button.id == "clear":
            self.log_display.clear()
        elif event.button.id == "back":
            self.app.action_show_home()

    @work(exclusive=True)
    async def load_logs(self) -> None:
        """Load and display logs."""
        self.log_display.clear()
        
        try:
            worker = self.run_worker(lambda: get_logs(limit=100), thread=True)
            await worker.wait()
            logs = worker.result

            if not logs:
                self.log_display.write("[yellow]No logs available[/yellow]")
                return

            # Display logs in reverse order (most recent first)
            for log_entry in reversed(logs):
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
                self.log_display.write(log_line)

        except Exception as e:
            self.log_display.write(
                f"[red]Failed to load logs: {str(e)[:80]}[/red]"
            )
