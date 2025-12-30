from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal
from textual import work

from app.client.api_client import get_system_status

class HomeScreen(Screen):

    def compose(self):
        yield Static("AstroForge", id="title")
        yield Static("Backend: checking...", id="status")

        # System Status
        with Vertical(id="system_status"):
            yield Static("SYSTEM STATUS", classes="section-title")
            yield Static("─────────────", classes="section-title")
            yield Static("MongoDB: Checking...", id="mongodb_status")
            yield Static("Rust Engine: Checking...", id="rust_status")

        # Pipeline Overview (placeholder)
        with Vertical(id="pipeline_overview"):
            yield Static("PIPELINE OVERVIEW", classes="section-title")
            yield Static("─────────────────", classes="section-title")
            yield Static("Unprocessed asteroids: --", id="unprocessed")
            yield Static("Analyzed today: --", id="analyzed_today")
            yield Static("High / Critical risks: --", id="high_risks")

        # Quick Actions
        with Vertical(id="quick_actions"):
            yield Static("QUICK ACTIONS", classes="section-title")
            yield Static("─────────────", classes="section-title")
            with Horizontal():
                yield Button("Run Pipeline", id="run_pipeline")
                yield Button("Asteroids", id="asteroids")
                yield Button("Logs", id="logs")

        yield Static(
            "Hints: q Quit • h Home • p Pipeline • a Asteroids • l Logs",
            id="hints",
        )

    def on_mount(self):
        self.refresh_status()
        self.set_interval(30, self.refresh_status)

    @work
    async def refresh_status(self):
        status = get_system_status()

        backend = status.get("backend", {})
        rust = status.get("rust_engine", {})

        backend_status = backend.get("status", "unknown")
        mongodb_status = backend.get("components", {}).get("mongodb", "unknown")

        rust_status = rust.get("status", "unknown")

        backend_ok = backend_status == "healthy"
        mongodb_ok = mongodb_status == "connected"
        rust_ok = rust_status == "ok"

        self.query_one("#status").update(
            f"Backend: {'Connected' if backend_ok else 'Unavailable'}"
        )

        self.query_one("#mongodb_status").update(
            f"MongoDB: ● {'Connected' if mongodb_ok else 'Disconnected'}"
        )

        self.query_one("#rust_status").update(
            f"Rust Engine: ● {'Reachable' if rust_ok else 'Unreachable'}"
        )
        self.query_one("#unprocessed").update("Unprocessed asteroids: --")
        self.query_one("#analyzed_today").update("Analyzed today: --")
        self.query_one("#high_risks").update("High / Critical risks: --")