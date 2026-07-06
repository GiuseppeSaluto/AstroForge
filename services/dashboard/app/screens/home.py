import logging
from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Horizontal, Grid, Vertical
from textual import work
from datetime import datetime
import asyncio

from app.client.api_client import run_pipeline
from app.widgets.status_panel import StatusPanel
from app.widgets.threats_panel import TopThreatsPanel
from app.widgets.close_approaches_panel import CloseApproachesPanel
from app import theme
from app.worker_safety import safe_worker

logger = logging.getLogger(__name__)

_WIDE_THRESHOLD = 90


class HomeScreen(Screen):

    CSS = theme.apply("""
    HomeScreen {
        layout: vertical;
        background: $bg;
    }

    #header {
        dock: top;
        height: 2;
        text-align: center;
        background: $bg;
        padding: 0 2;
    }

    #clock_bar {
        dock: top;
        height: 1;
        background: $surface;
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

    #right_column {
        layout: vertical;
        height: 1fr;
        grid-gutter: 1;
    }

    #right_column TopThreatsPanel {
        height: 1fr;
    }

    #right_column CloseApproachesPanel {
        height: 1fr;
    }

    #quick_actions {
        height: 3;
        margin: 1 2;
    }

    #quick_actions Button {
        margin: 0 1;
    }
    """)

    _terminal_width: int = 80
    _system_status: tuple[bool, bool, bool] | None = None

    def compose(self):
        yield Static("", id="header")
        yield Static("", id="clock_bar")

        with Grid(id="main_grid"):
            yield StatusPanel(id="status_panel")
            with Vertical(id="right_column"):
                yield TopThreatsPanel(id="threats_panel")
                yield CloseApproachesPanel(id="close_approaches_panel")

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
        width = self.app.size.width
        self._terminal_width = width
        self._apply_layout(width)
        self.set_interval(1.0, self._update_clock_bar)

    def on_resize(self, event) -> None:
        self._terminal_width = event.size.width
        self._apply_layout(event.size.width)

    # ── StatusPanel posts this when service health is fetched ─────────────────

    def on_status_panel_status_changed(self, event: StatusPanel.StatusChanged) -> None:
        self._system_status = (event.backend_ok, event.mongodb_ok, event.rust_ok)
        self._update_clock_bar()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _apply_layout(self, width: int) -> None:
        is_wide = width >= _WIDE_THRESHOLD
        self.query_one("#main_grid").styles.grid_size_columns = 2 if is_wide else 1
        self._render_header(width)
        self._update_clock_bar()

    def _render_header(self, width: int) -> None:
        title = (
            f"[{theme.ACCENT}]◈  A S T R O F O R G E"
            f"  ─  N E O   T H R E A T   T R A C K E R[/{theme.ACCENT}]"
        )
        if width >= 80:
            subtitle = (
                f"[{theme.MUTED}]NASA NeoWS  ·  Python REST API"
                f"  ·  Rust Risk Engine  ·  MongoDB[/{theme.MUTED}]"
            )
            self.query_one("#header", Static).update(f"{title}\n{subtitle}")
        else:
            self.query_one("#header", Static).update(title)

    def _update_clock_bar(self) -> None:
        width = self._terminal_width
        now = datetime.now()
        date_str = now.strftime("%A, %d %B %Y") if width >= 80 else now.strftime("%d/%m/%Y")
        time_str = now.strftime("%H:%M:%S")

        if self._system_status is not None:
            backend_ok, mongodb_ok, rust_ok = self._system_status

            def _dot(ok: bool) -> str:
                c = theme.LOW if ok else theme.CRITICAL
                return f"[{c}]●[/{c}]"

            dots = (
                f"{_dot(backend_ok)} [{theme.MUTED}]Backend[/{theme.MUTED}]  "
                f"{_dot(mongodb_ok)} [{theme.MUTED}]MongoDB[/{theme.MUTED}]  "
                f"{_dot(rust_ok)} [{theme.MUTED}]Rust Engine[/{theme.MUTED}]"
            )
            self.query_one("#clock_bar").update(
                f"[{theme.MUTED}]{date_str}[/{theme.MUTED}]"
                f"   [{theme.ACCENT}]{time_str}[/{theme.ACCENT}]"
                f"   {dots}"
            )
        else:
            self.query_one("#clock_bar").update(
                f"[{theme.MUTED}]{date_str}[/{theme.MUTED}]"
                f"   [{theme.ACCENT}]{time_str}[/{theme.ACCENT}]"
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

    # ── Pipeline quick-run ────────────────────────────────────────────────────

    @work(exclusive=True)
    @safe_worker
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
                self.query_one(StatusPanel).refresh_data()
                self.query_one(TopThreatsPanel).refresh_data()
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
