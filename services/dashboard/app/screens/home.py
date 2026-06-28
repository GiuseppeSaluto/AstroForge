import logging
from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal, Grid
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

    #header {
        dock: top;
        height: 4;
        text-align: center;
        background: $bg;
        padding: 0 2;
    }

    #clock_bar {
        dock: top;
        height: 1;
        background: $surface;
        color: $muted;
        content-align: center middle;
    }

    #footer {
        dock: bottom;
        height: 1;
        color: $muted;
        content-align: center middle;
        background: $surface;
    }

    #main_grid {
        layout: grid;
        grid-size: 2;
        grid-gutter: 1;
        height: 1fr;
        margin: 1 2 0 2;
    }

    .panel {
        border: solid $border_dim;
        padding: 1;
    }

    .panel-title {
        color: $accent;
        text-style: bold;
        margin: 0 0 1 0;
    }

    .stat-row {
        margin: 0 0 1 0;
    }

    #quick_actions {
        height: 3;
        margin: 1 2;
    }

    #quick_actions Button {
        margin: 0 1;
    }
    """)

    _countdown: int = _REFRESH_INTERVAL

    def compose(self):
        yield Static("", id="header")
        yield Static("", id="clock_bar")

        with Grid(id="main_grid"):
            with Vertical(classes="panel"):
                yield Static("", id="status_title", classes="panel-title")
                yield Static("", id="backend_status", classes="stat-row")
                yield Static("", id="mongodb_status", classes="stat-row")
                yield Static("", id="rust_status", classes="stat-row")
                yield Static("", id="scan_bar")

            with Vertical(classes="panel"):
                yield Static("", id="stats_title", classes="panel-title")
                yield Static("", id="stat_unprocessed", classes="stat-row")
                yield Static("", id="stat_analyzed", classes="stat-row")
                yield Static("", id="stat_risks", classes="stat-row")
                yield Static("", id="stat_lastrun", classes="stat-row")
                yield Static("", id="risk_bar")

        with Horizontal(id="quick_actions"):
            yield Button("▶  Run Pipeline", id="run_pipeline", variant="primary")
            yield Button("◎  Asteroids", id="asteroids")
            yield Button("≡  Pipeline", id="pipeline")
            yield Button("↗  Charts", id="charts")
            yield Button("≈  Logs", id="logs")

        yield Static(
            "h Home  ·  a Asteroids  ·  c Charts  ·  p Pipeline  ·  l Logs  ·  q Quit",
            id="footer",
        )

    def on_mount(self) -> None:
        self._render_header()
        self._render_panel_titles()
        self._update_clock_bar()
        self._update_data_age_bar()
        self.refresh_all_data()
        self.set_interval(1.0, self._tick)

    # ── Static renders ────────────────────────────────────────────────────────

    def _render_header(self) -> None:
        sep = f"[{theme.BORDER_DIM}]{'═' * 64}[/{theme.BORDER_DIM}]"
        self.query_one("#header", Static).update(
            f"{sep}\n"
            f"  [{theme.ACCENT}]◈  A S T R O F O R G E  ─  N E O   T H R E A T   T R A C K E R[/{theme.ACCENT}]\n"
            f"  [{theme.MUTED}]NASA NeoWS  ·  Python REST API  ·  Rust Risk Engine  ·  MongoDB[/{theme.MUTED}]\n"
            f"{sep}"
        )

    def _render_panel_titles(self) -> None:
        self.query_one("#status_title", Static).update(
            f"[{theme.ACCENT}]── SYSTEM STATUS[/{theme.ACCENT}]"
        )
        self.query_one("#stats_title", Static).update(
            f"[{theme.ACCENT}]── MISSION STATISTICS[/{theme.ACCENT}]"
        )

    # ── Tick: clock + data-age bar ────────────────────────────────────────────

    def _tick(self) -> None:
        self._update_clock_bar()
        self._update_data_age_bar()
        self._countdown -= 1
        if self._countdown <= 0:
            self._countdown = _REFRESH_INTERVAL
            self.refresh_all_data()

    def _update_clock_bar(self) -> None:
        now = datetime.now()
        date_str = now.strftime("%A, %d %B %Y")
        time_str = now.strftime("%H:%M:%S")
        self.query_one("#clock_bar").update(
            f"[{theme.MUTED}]{date_str}[/{theme.MUTED}]"
            f"   [{theme.ACCENT}]{time_str}[/{theme.ACCENT}]"
        )

    def _update_data_age_bar(self) -> None:
        elapsed = _REFRESH_INTERVAL - self._countdown
        ratio = elapsed / _REFRESH_INTERVAL
        bar_width = 24
        filled = round(ratio * bar_width)
        bar = (
            f"[{theme.MUTED}]{'█' * filled}[/{theme.MUTED}]"
            f"[{theme.BORDER_DIM}]{'░' * (bar_width - filled)}[/{theme.BORDER_DIM}]"
        )
        age_str = f"{elapsed}s ago" if elapsed > 0 else "just updated"
        try:
            self.query_one("#scan_bar").update(
                f"\n  [{theme.MUTED}]DATA AGE  {bar}  {age_str}[/{theme.MUTED}]"
            )
        except Exception:
            pass

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

            def _row(label: str, ok: bool, ok_text: str, err_text: str) -> str:
                dot = "●" if ok else "○"
                c = theme.LOW if ok else theme.CRITICAL
                return (
                    f"  [{c}]{dot}[/{c}]"
                    f"  [{theme.TEXT}]{label:<14}[/{theme.TEXT}]"
                    f"[{c}]{ok_text if ok else err_text}[/{c}]"
                )

            self.query_one("#backend_status").update(
                _row("Backend", backend_ok, "ONLINE", "OFFLINE")
            )
            self.query_one("#mongodb_status").update(
                _row("MongoDB", mongodb_ok, "CONNECTED", "DISCONNECTED")
            )
            self.query_one("#rust_status").update(
                _row("Rust Engine", rust_ok, "READY", "UNREACHABLE")
            )

            if backend_ok:
                stats = await loop.run_in_executor(None, get_pipeline_stats)
                if stats.get("status") != "error":
                    unprocessed = stats.get("unprocessed", 0)
                    analyzed_today = stats.get("analyzed_today", 0)
                    high_risks = stats.get("high_risks", 0)
                    last_run = stats.get("last_pipeline_run")

                    self.query_one("#stat_unprocessed").update(
                        f"  [{theme.ACCENT}]{unprocessed:>5}[/{theme.ACCENT}]"
                        f"  [{theme.MUTED}]unprocessed[/{theme.MUTED}]"
                    )
                    self.query_one("#stat_analyzed").update(
                        f"  [{theme.LOW}]{analyzed_today:>5}[/{theme.LOW}]"
                        f"  [{theme.MUTED}]analyzed today[/{theme.MUTED}]"
                    )
                    risk_color = theme.CRITICAL if high_risks > 0 else theme.LOW
                    self.query_one("#stat_risks").update(
                        f"  [{risk_color}]{high_risks:>5}[/{risk_color}]"
                        f"  [{theme.MUTED}]high / critical risks[/{theme.MUTED}]"
                    )

                    if last_run:
                        try:
                            dt = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
                            lr_str = dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
                        except Exception:
                            lr_str = last_run
                    else:
                        lr_str = "never"
                    self.query_one("#stat_lastrun").update(
                        f"  [{theme.MUTED}]last run[/{theme.MUTED}]"
                        f"  [{theme.ACCENT}]{lr_str}[/{theme.ACCENT}]"
                    )

                    ratio = min(high_risks / max(analyzed_today, 1), 1.0)
                    bar_width = 24
                    filled = round(ratio * bar_width)
                    if ratio > 0.3:
                        bar_color, threat_label = theme.CRITICAL, "CRITICAL"
                    elif ratio > 0.1:
                        bar_color, threat_label = theme.MEDIUM, "ELEVATED"
                    else:
                        bar_color, threat_label = theme.LOW, "NOMINAL"
                    bar_filled = f"[{bar_color}]{'█' * filled}[/{bar_color}]"
                    bar_empty = f"[{theme.MUTED}]{'░' * (bar_width - filled)}[/{theme.MUTED}]"
                    pct = f"{ratio * 100:.0f}%"
                    self.query_one("#risk_bar").update(
                        f"\n"
                        f"  [{theme.MUTED}]THREAT LEVEL[/{theme.MUTED}]\n"
                        f"  {bar_filled}{bar_empty}  [{bar_color}]{pct}  {threat_label}[/{bar_color}]"
                    )

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
