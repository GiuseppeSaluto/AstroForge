import logging
from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal
from textual import work
from datetime import datetime
import asyncio

from app.client.api_client import get_system_status, get_pipeline_stats, run_pipeline
from app import theme

logger = logging.getLogger(__name__)

_REFRESH_INTERVAL = 10


class HomeScreen(Screen):

    CSS = theme.apply("""
    HomeScreen {
        layout: vertical;
        background: $bg;
    }

    #title {
        dock: top;
        height: 2;
        content-align: center middle;
        color: $accent;
        background: $surface;
        text-style: bold;
    }

    #clock_bar {
        dock: top;
        height: 1;
        background: $surface;
        color: $muted;
        content-align: center middle;
    }

    .section-title {
        color: $accent;
        text-style: bold;
        margin: 1 0 0 0;
    }

    #system_status {
        height: auto;
        border: solid $border_dim;
        margin: 1 2;
    }

    #pipeline_stats {
        height: auto;
        border: solid $border_dim;
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
        color: $muted;
        text-align: center;
    }
    """)

    _countdown: int = _REFRESH_INTERVAL

    def compose(self):
        yield Static("ASTROFORGE DASHBOARD", id="title")
        yield Static("", id="clock_bar")

        with Vertical(id="system_status"):
            yield Static("SYSTEM STATUS", classes="section-title")
            yield Static("Backend:     ", id="backend_status")
            yield Static("MongoDB:     ", id="mongodb_status")
            yield Static("Rust Engine: ", id="rust_status")

        with Vertical(id="pipeline_stats"):
            yield Static("PIPELINE STATISTICS", classes="section-title")
            yield Static("Unprocessed asteroids: Loading...", id="unprocessed")
            yield Static("Analyzed today: Loading...", id="analyzed_today")
            yield Static("High/Critical risks: Loading...", id="high_risks")
            yield Static("Last pipeline run: --", id="last_run")

        with Vertical(id="quick_actions"):
            yield Static("QUICK ACTIONS", classes="section-title")
            with Horizontal():
                yield Button("▶ Run Pipeline", id="run_pipeline", variant="primary")
                yield Button("📊 Asteroids", id="asteroids")
                yield Button("📋 Pipeline", id="pipeline")
                yield Button("📈 Charts", id="charts")
                yield Button("📝 Logs", id="logs")

        yield Static(
            "Shortcuts: q Quit  •  h Home  •  a Asteroids  •  c Charts  •  p Pipeline  •  l Logs",
            id="footer",
        )

    def on_mount(self) -> None:
        self._update_clock_bar()
        self.refresh_all_data()
        self.set_interval(1.0, self._tick)

    # ── Clock & countdown ─────────────────────────────────────────────────────

    def _tick(self) -> None:
        self._update_clock_bar()
        self._countdown -= 1
        if self._countdown <= 0:
            self._countdown = _REFRESH_INTERVAL
            self.refresh_all_data()

    def _update_clock_bar(self) -> None:
        now = datetime.now()
        date_str = now.strftime("%A %d %B %Y")
        time_str = now.strftime("%H:%M:%S")
        refresh_str = f"↻ {self._countdown}s"
        self.query_one("#clock_bar").update(
            f"[{theme.MUTED}]{date_str}[/{theme.MUTED}]"
            f"   [{theme.ACCENT}]{time_str}[/{theme.ACCENT}]"
            f"   [{theme.MUTED}]{refresh_str}[/{theme.MUTED}]"
        )

    # ── Events ────────────────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "run_pipeline":
            self.run_pipeline_action()
        elif event.button.id == "asteroids":
            self.app.action_show_asteroids()
        elif event.button.id == "pipeline":
            self.app.action_show_pipeline()
        elif event.button.id == "charts":
            self.app.action_show_charts()
        elif event.button.id == "logs":
            self.app.action_show_logs()

    # ── Data refresh ──────────────────────────────────────────────────────────

    @work(exclusive=True)
    async def refresh_all_data(self) -> None:
        self._countdown = _REFRESH_INTERVAL
        try:
            loop = asyncio.get_event_loop()
            status = await loop.run_in_executor(None, get_system_status)
            backend = status.get("backend", {})
            rust = status.get("rust_engine", {})

            backend_ok = backend.get("status") == "healthy"
            mongodb_ok = backend.get("components", {}).get("mongodb") == "connected"
            rust_ok = rust.get("status") == "ok"

            def _badge(ok: bool, yes: str, no: str) -> str:
                c = theme.LOW if ok else theme.CRITICAL
                icon = "✓" if ok else "✗"
                return f"[{c}]{icon} {yes if ok else no}[/{c}]"

            self.query_one("#backend_status").update(
                f"Backend:     {_badge(backend_ok, 'Connected', 'Unavailable')}"
            )
            self.query_one("#mongodb_status").update(
                f"MongoDB:     {_badge(mongodb_ok, 'Connected', 'Disconnected')}"
            )
            self.query_one("#rust_status").update(
                f"Rust Engine: {_badge(rust_ok, 'Ready', 'Unreachable')}"
            )

            if backend_ok:
                stats = await loop.run_in_executor(None, get_pipeline_stats)
                if stats.get("status") != "error":
                    unprocessed = stats.get("unprocessed", 0)
                    analyzed_today = stats.get("analyzed_today", 0)
                    high_risks = stats.get("high_risks", 0)
                    last_run = stats.get("last_pipeline_run")

                    self.query_one("#unprocessed").update(
                        f"Unprocessed asteroids: [{theme.ACCENT}]{unprocessed}[/{theme.ACCENT}]"
                    )
                    self.query_one("#analyzed_today").update(
                        f"Analyzed today: [{theme.ACCENT}]{analyzed_today}[/{theme.ACCENT}]"
                    )
                    self.query_one("#high_risks").update(
                        f"High/Critical risks: "
                        + (f"[{theme.CRITICAL}]{high_risks}[/{theme.CRITICAL}]" if high_risks > 0
                           else f"[{theme.LOW}]{high_risks}[/{theme.LOW}]")
                    )
                    if last_run:
                        try:
                            dt = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
                            self.query_one("#last_run").update(
                                f"Last pipeline run: {dt.astimezone().strftime('%Y-%m-%d %H:%M:%S')}"
                            )
                        except Exception:
                            self.query_one("#last_run").update(f"Last pipeline run: {last_run}")

        except Exception as e:
            logger.error(f"Failed to refresh system status: {e}")

    # ── Pipeline quick-run ────────────────────────────────────────────────────

    @work(exclusive=True)
    async def run_pipeline_action(self) -> None:
        button = self.query_one("#run_pipeline", Button)
        original_label = button.label

        try:
            button.label = "⟳ Running..."
            button.disabled = True

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: run_pipeline(limit=100))

            if result.get("status") == "success":
                processed = result.get("statistics", {}).get("processed", 0)
                button.label = f"✓ {processed} processed"
                self.refresh_all_data()
            else:
                button.label = "✗ Failed"

            self.set_timer(3, lambda: self._reset_button(button, original_label))

        except Exception as e:
            logger.error(f"Pipeline execution error: {e}", exc_info=True)
            button.label = f"✗ Error: {str(e)[:20]}"
            self.set_timer(3, lambda: self._reset_button(button, original_label))

    def _reset_button(self, button: Button, label: str) -> None:
        button.label = label
        button.disabled = False
