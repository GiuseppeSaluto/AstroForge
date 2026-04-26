from textual.screen import Screen
from textual.widgets import Static, Button, Label
from textual.containers import Vertical, Horizontal, Container
from textual import work
from datetime import datetime
import asyncio
import logging

from app.client.api_client import get_system_status, get_pipeline_stats, run_pipeline

logger = logging.getLogger(__name__)


class StatusBadge(Static):
    """Display a colored status badge."""
    
    def __init__(self, label: str, status: bool = False):
        super().__init__()
        self.label = label
        self.status = status
    
    def render(self) -> str:
        indicator = "● " if self.status else "○ "
        color = "green" if self.status else "red"
        return f"[{color}]{indicator}{self.label}[/{color}]"


class HomeScreen(Screen):
    """Main dashboard home screen with system status and quick stats."""

    CSS = """
    HomeScreen {
        layout: vertical;
        background: $surface;
    }

    #title {
        dock: top;
        height: 3;
        content-align: center middle;
        color: $primary;
        background: $boost;
        text-style: bold;
    }

    #system_status {
        height: auto;
        border: solid $primary;
        margin: 1 2;
    }

    .section-title {
        color: $primary;
        text-style: bold;
        margin: 1 0 0 0;
    }

    #pipeline_stats {
        height: auto;
        border: solid $accent;
        margin: 1 2;
    }

    #quick_actions {
        height: auto;
        margin: 1 2;
    }

    #quick_actions Button {
        margin: 0 1;
    }

    #footer {
        dock: bottom;
        height: 1;
        color: $text-muted;
        text-align: center;
    }
    """

    def compose(self):
        """Compose the home screen layout."""
        yield Static("AstroForge Dashboard", id="title")

        # System Status Section
        with Vertical(id="system_status"):
            yield Static("SYSTEM STATUS", classes="section-title")
            yield Static("Backend: ", id="backend_status")
            yield Static("MongoDB: ", id="mongodb_status")
            yield Static("Rust Engine: ", id="rust_status")

        # Pipeline Stats Section
        with Vertical(id="pipeline_stats"):
            yield Static("PIPELINE STATISTICS", classes="section-title")
            yield Static("Unprocessed asteroids: Loading...", id="unprocessed")
            yield Static("Analyzed today: Loading...", id="analyzed_today")
            yield Static("High/Critical risks: Loading...", id="high_risks")
            yield Static("Last pipeline run: --", id="last_run")

        # Quick Actions
        with Vertical(id="quick_actions"):
            yield Static("QUICK ACTIONS", classes="section-title")
            with Horizontal():
                yield Button("▶ Run Pipeline", id="run_pipeline", variant="primary")
                yield Button("📊 Asteroids", id="asteroids")
                yield Button("📋 Pipeline", id="pipeline")
                yield Button("📝 Logs", id="logs")

        yield Static(
            "Shortcuts: q Quit • h Home • a Asteroids • p Pipeline • l Logs",
            id="footer",
        )

    def on_mount(self) -> None:
        """Initialize and start refreshing data."""
        self.refresh_all_data()
        self.set_interval(10, self.refresh_all_data)  # Refresh every 10 seconds

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "run_pipeline":
            self.run_pipeline_action()
        elif event.button.id == "asteroids":
            self.app.action_show_asteroids()
        elif event.button.id == "pipeline":
            self.app.action_show_pipeline()
        elif event.button.id == "logs":
            self.app.action_show_logs()

    @work(exclusive=True)
    async def refresh_all_data(self) -> None:
        """Refresh system status and pipeline stats."""
        try:
            # Get system status
            loop = asyncio.get_event_loop()
            status = await loop.run_in_executor(None, get_system_status)
            backend = status.get("backend", {})
            rust = status.get("rust_engine", {})

            backend_ok = backend.get("status") == "healthy"
            mongodb_ok = backend.get("components", {}).get("mongodb") == "connected"
            rust_ok = rust.get("status") == "ok"

            # Update status widgets
            self.query_one("#backend_status").update(
                f"Backend: {'✓ Connected' if backend_ok else '✗ Unavailable'}"
            )
            self.query_one("#mongodb_status").update(
                f"MongoDB: {'✓ Connected' if mongodb_ok else '✗ Disconnected'}"
            )
            self.query_one("#rust_status").update(
                f"Rust Engine: {'✓ Ready' if rust_ok else '✗ Unreachable'}"
            )

            # Get pipeline stats if backend is healthy
            if backend_ok:
                stats = await loop.run_in_executor(None, get_pipeline_stats)
                if stats.get("status") != "error":
                    unprocessed = stats.get("unprocessed", 0)
                    analyzed_today = stats.get("analyzed_today", 0)
                    high_risks = stats.get("high_risks", 0)
                    last_run = stats.get("last_pipeline_run")

                    self.query_one("#unprocessed").update(
                        f"Unprocessed asteroids: {unprocessed}"
                    )
                    self.query_one("#analyzed_today").update(
                        f"Analyzed today: {analyzed_today}"
                    )
                    self.query_one("#high_risks").update(
                        f"High/Critical risks: {high_risks}"
                    )
                    
                    if last_run:
                        try:
                            dt = datetime.fromisoformat(last_run.replace('Z', '+00:00'))
                            self.query_one("#last_run").update(
                                f"Last pipeline run: {dt.strftime('%Y-%m-%d %H:%M:%S')}"
                            )
                        except:
                            self.query_one("#last_run").update(f"Last pipeline run: {last_run}")

        except Exception as e:
            backend_status = self.query_one("#backend_status", expect_none=True)
            if backend_status:
                backend_status.update(f"Backend: ✗ Error ({str(e)[:30]})")
            logger.error(f"Failed to refresh system status: {str(e)}")

    @work(exclusive=True)
    async def run_pipeline_action(self) -> None:
        """Execute pipeline run."""
        button = self.query_one("#run_pipeline", Button)
        original_label = button.label
        
        try:
            button.label = "⟳ Running..."
            button.disabled = True
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: run_pipeline(limit=100))
            
            if result.get("status") == "success":
                stats = result.get("statistics", {})
                processed = stats.get("processed", 0)
                button.label = f"✓ {processed} processed"
                # Refresh data after pipeline completes
                self.refresh_all_data()
            else:
                button.label = "✗ Pipeline failed"
            
            # Reset after 3 seconds
            self.set_timer(3, lambda: self._reset_button(button, original_label))
            
        except Exception as e:
            logger.error(f"Pipeline execution error: {e}", exc_info=True)
            button.label = f"✗ Error: {str(e)[:20]}"
            self.set_timer(3, lambda: self._reset_button(button, original_label))

    def _reset_button(self, button: Button, label: str) -> None:
        """Reset button to original state."""
        button.label = label
        button.disabled = False