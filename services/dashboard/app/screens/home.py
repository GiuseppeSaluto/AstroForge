from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal
from textual import work
from app.client.api_client import get_status


class HomeScreen(Screen):
    
    def compose(self):
        yield Static("AstroForge", id="title")
        yield Static("Backend: checking...", id="status")

        # System Status
        with Vertical(id="system_status"):
            yield Static("SYSTEM STATUS", classes="section-title")
            yield Static("─────────────", classes="section-title")
            yield Static("MongoDB: ● Checking", id="mongodb_status")
            yield Static("Rust Engine: ● Checking", id="rust_status")
            yield Static("Last Pipeline: Loading...", id="last_pipeline")

        # Pipeline Overview
        with Vertical(id="pipeline_overview"):
            yield Static("PIPELINE OVERVIEW", classes="section-title")
            yield Static("─────────────────", classes="section-title")
            yield Static("Unprocessed asteroids: Loading...", id="unprocessed")
            yield Static("Analyzed today: Loading...", id="analyzed_today")
            yield Static("High / Critical risks: Loading...", id="high_risks")

        # Quick Actions
        with Vertical(id="quick_actions"):
            yield Static("QUICK ACTIONS", classes="section-title")
            yield Static("─────────────", classes="section-title")
            with Horizontal():
                yield Button("Run Pipeline", id="run_pipeline")
                yield Button("View Logs", id="view_logs")
                yield Button("Asteroids", id="asteroids")

        yield Static("Hints: q - Quit, h - Home, p - Pipeline, a - Asteroids, l - Logs", id="hints")

    def on_mount(self):
        """Called when the screen is mounted."""
        self.update_status()
        self.set_interval(30, self.update_status)

    @work
    async def update_status(self):
        status = get_status()
        backend_status = status.get("backend", "unknown")
        rust_status = status.get("rust_engine", "unknown")

        self.query_one("#status").update(f"Backend: {backend_status}")
        self.query_one("#mongodb_status").update(f"MongoDB: ● {'Connected' if backend_status == 'connected' else 'Disconnected'}")
        self.query_one("#rust_status").update(f"Rust Engine: ● {'Reachable' if rust_status == 'reachable' else 'Unreachable'}")

        # Placeholder per altri dati (da implementare con endpoint reali)
        self.query_one("#last_pipeline").update("Last Pipeline: 2025-12-20 10:00")
        self.query_one("#unprocessed").update("Unprocessed asteroids: 128")
        self.query_one("#analyzed_today").update("Analyzed today: 42")
        self.query_one("#high_risks").update("High / Critical risks: 3")
        
    