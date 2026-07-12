import logging
from textual.screen import Screen
from textual.widgets import Static, Button, RichLog, LoadingIndicator
from textual.containers import Vertical, Horizontal
from textual.css.query import NoMatches
from textual import work
from datetime import datetime

from app.client.api_client import run_pipeline, get_pipeline_stats
from app.widgets.global_status_bar import GlobalStatusBar
from app import theme
from app.worker_safety import safe_worker


class PipelineScreen(Screen):

    CSS = theme.apply("""
    PipelineScreen {
        layout: vertical;
    }

    #title {
        height: 2;
        content-align: center middle;
        text-style: bold;
        color: $accent;
        background: $surface;
    }

    #stats_container {
        border: solid $border_dim;
        margin: 1 2 0 2;
        padding: 0 1;
        height: auto;
    }

    .stat-line {
        margin: 0;
        height: 1;
    }

    #actions {
        height: auto;
        margin: 1 2 0 2;
    }

    Button {
        margin: 0 1;
    }

    #run_status {
        height: 1;
        margin: 0 2;
        color: $muted;
    }

    #loading {
        height: 1;
        margin: 0 2;
    }

    #activity_log {
        border: solid $border_dim;
        margin: 1 2;
    }

    #footer {
        dock: bottom;
        height: 1;
        color: $muted;
    }
    """)

    _elapsed_seconds: int = 0
    _pipeline_running: bool = False

    def compose(self):
        yield GlobalStatusBar()
        yield Static("PIPELINE CONTROL", id="title")

        with Vertical(id="stats_container"):
            yield Static("Unprocessed asteroids: Loading...", classes="stat-line", id="unprocessed")
            yield Static("Analyzed today: Loading...", classes="stat-line", id="analyzed_today")
            yield Static("High/Critical risks: Loading...", classes="stat-line", id="high_risks")
            yield Static("Last run: --", classes="stat-line", id="last_run")

        with Horizontal(id="actions"):
            yield Button("▶ Run Now", id="run_pipeline", variant="primary")
            yield Button("🔄 Refresh", id="refresh_stats")
            yield Button("⬅ Back", id="back")

        yield Static("", id="run_status")
        yield LoadingIndicator(id="loading")
        yield RichLog(id="activity_log", highlight=False, markup=True, wrap=False)

        yield Static(
            "Pipeline analysis takes ~30-60 seconds depending on asteroid count",
            id="footer",
        )

    def on_mount(self) -> None:
        self.query_one("#loading").display = False
        self._log("System ready. Press [Run Now] to start analysis.")
        self.refresh_stats()
        self.set_interval(15, self.refresh_stats)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _log(self, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        try:
            self.query_one("#activity_log", RichLog).write(
                f"[{theme.MUTED}]{ts}[/{theme.MUTED}]  {message}"
            )
        except NoMatches:
            pass

    def _get_status_widget(self) -> Static | None:
        try:
            return self.query_one("#run_status", Static)
        except NoMatches:
            return None

    # ── Events ────────────────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "run_pipeline":
            self.run_pipeline_action()
        elif event.button.id == "refresh_stats":
            self.refresh_stats()
        elif event.button.id == "back":
            self.app.action_show_home()

    # ── Stats refresh ─────────────────────────────────────────────────────────

    @work(exclusive=True)
    @safe_worker
    async def refresh_stats(self) -> None:
        try:
            worker = self.run_worker(get_pipeline_stats, thread=True)
            await worker.wait()
            stats = worker.result

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
                    f"High/Critical risks: [{theme.CRITICAL}]{high_risks}[/{theme.CRITICAL}]"
                    if high_risks > 0
                    else f"High/Critical risks: [{theme.LOW}]{high_risks}[/{theme.LOW}]"
                )

                if last_run:
                    try:
                        dt = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
                        self.query_one("#last_run").update(
                            f"Last run: {dt.astimezone().strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                    except Exception:
                        self.query_one("#last_run").update(f"Last run: {last_run}")
                else:
                    self.query_one("#last_run").update("Last run: Never")
            else:
                status = self._get_status_widget()
                if status:
                    status.update(
                        f"[{theme.CRITICAL}]Stats error: {stats.get('error', '?')}[/{theme.CRITICAL}]"
                    )
        except Exception as e:
            logging.error(f"Failed to refresh pipeline stats: {e}")

    # ── Pipeline run ──────────────────────────────────────────────────────────

    @work(exclusive=True)
    @safe_worker
    async def run_pipeline_action(self) -> None:
        button = self.query_one("#run_pipeline", Button)
        loading = self.query_one("#loading", LoadingIndicator)
        status = self._get_status_widget()

        # — enter running state —
        self._pipeline_running = True
        self._elapsed_seconds = 0
        button.disabled = True
        button.label = "Running..."
        loading.display = True
        if status:
            status.update(f"[{theme.MUTED}]Elapsed: 0s[/{theme.MUTED}]")

        self._log(f"[{theme.ACCENT}]▶ Pipeline started[/{theme.ACCENT}]")

        # elapsed timer: ticks every second
        def _tick():
            self._elapsed_seconds += 1
            if status:
                status.update(
                    f"[{theme.MUTED}]Elapsed: {self._elapsed_seconds}s[/{theme.MUTED}]"
                )

        elapsed_timer = self.set_interval(1.0, _tick)

        # timed phase messages — based on actual pipeline steps
        def _phase(msg: str):
            if self._pipeline_running:
                self._log(msg)

        self.set_timer(1.5, lambda: _phase("Querying MongoDB for unprocessed asteroids..."))
        self.set_timer(4.0, lambda: _phase(f"Dispatching batch to Rust Engine [{theme.ACCENT}]:8080[/{theme.ACCENT}]..."))
        self.set_timer(7.0, lambda: _phase("Computing impact energy and risk scores..."))
        self.set_timer(12.0, lambda: _phase("Persisting analysis results to MongoDB..."))

        try:
            worker = self.run_worker(lambda: run_pipeline(limit=100), thread=True)
            await worker.wait()
            result = worker.result

            self._pipeline_running = False
            elapsed_timer.stop()
            loading.display = False

            if "error" not in result:
                stats = result.get("statistics", {})
                processed = stats.get("processed", 0)
                failed = stats.get("failed", 0)
                skipped = stats.get("skipped", 0)
                elapsed = self._elapsed_seconds

                self._log(
                    f"[{theme.LOW}]✓ Done in {elapsed}s — "
                    f"processed: {processed}  "
                    f"skipped: {skipped}  "
                    f"failed: [{theme.CRITICAL if failed > 0 else theme.LOW}]{failed}[/{theme.CRITICAL if failed > 0 else theme.LOW}]"
                    f"[/{theme.LOW}]"
                )

                if status:
                    status.update(
                        f"[{theme.LOW}]Last run: {processed} analyzed in {elapsed}s[/{theme.LOW}]"
                    )

                button.label = "▶ Run Now"
                button.disabled = False
                self.refresh_stats()

            else:
                error_msg = result.get("error", "Unknown error")
                self._log(f"[{theme.CRITICAL}]✗ Pipeline failed: {error_msg}[/{theme.CRITICAL}]")
                if status:
                    status.update(f"[{theme.CRITICAL}]Failed — see log above[/{theme.CRITICAL}]")
                button.label = "▶ Run Now"
                button.disabled = False

        except Exception as e:
            self._pipeline_running = False
            elapsed_timer.stop()
            loading.display = False
            self._log(f"[{theme.CRITICAL}]✗ Exception: {str(e)}[/{theme.CRITICAL}]")
            if status:
                status.update(f"[{theme.CRITICAL}]Error[/{theme.CRITICAL}]")
            button.label = "▶ Run Now"
            button.disabled = False
