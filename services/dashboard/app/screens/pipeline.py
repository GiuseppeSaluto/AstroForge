import logging
from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal
from textual.css.query import NoMatches
from textual import work
from datetime import datetime

from app.client.api_client import run_pipeline, get_pipeline_stats


class PipelineScreen(Screen):
    """Pipeline control and monitoring screen."""

    CSS = """
    PipelineScreen {
        layout: vertical;
    }

    #title {
        dock: top;
        height: 2;
        content-align: center middle;
        text-style: bold;
        color: $primary;
        background: $boost;
    }

    #stats_container {
        border: solid $accent;
        margin: 1 2;
        padding: 0 1;
    }

    .stat-line {
        margin: 0;
        height: 1;
    }

    #actions {
        height: auto;
        margin: 1 2;
    }

    Button {
        margin: 0 1;
    }

    #footer {
        dock: bottom;
        height: 1;
        color: $text-muted;
    }
    """

    def compose(self):
        """Compose pipeline screen layout."""
        yield Static("PIPELINE CONTROL", id="title")

        with Vertical(id="stats_container"):
            yield Static("Unprocessed asteroids: Loading...", classes="stat-line", id="unprocessed")
            yield Static("Analyzed today: Loading...", classes="stat-line", id="analyzed_today")
            yield Static("High/Critical risks: Loading...", classes="stat-line", id="high_risks")
            yield Static("Last run: --", classes="stat-line", id="last_run")
            yield Static("Status: --", classes="stat-line", id="run_status")

        with Horizontal(id="actions"):
            yield Button("▶ Run Now", id="run_pipeline", variant="primary")
            yield Button("🔄 Refresh", id="refresh_stats")
            yield Button("⬅ Back", id="back")

        yield Static(
            "Pipeline analysis takes ~30-60 seconds depending on asteroid count",
            id="footer",
        )

    def _get_status_widget(self) -> Static | None:
        """Safely retrieve the #run_status widget, returning None if not found."""
        try:
            return self.query_one("#run_status", Static)
        except NoMatches:
            return None

    def on_mount(self) -> None:
        """Initialize screen and start refreshing."""
        self.refresh_stats()
        self.set_interval(15, self.refresh_stats)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "run_pipeline":
            self.run_pipeline_action()
        elif event.button.id == "refresh_stats":
            self.refresh_stats()
        elif event.button.id == "back":
            self.app.action_show_home()

    @work(exclusive=True)
    async def refresh_stats(self) -> None:
        """Refresh pipeline statistics."""
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
                    f"Unprocessed asteroids: [cyan]{unprocessed}[/cyan]"
                )
                self.query_one("#analyzed_today").update(
                    f"Analyzed today: [cyan]{analyzed_today}[/cyan]"
                )
                self.query_one("#high_risks").update(
                    f"High/Critical risks: [yellow]{high_risks}[/yellow]" if high_risks > 0
                    else f"High/Critical risks: [green]{high_risks}[/green]"
                )

                if last_run:
                    try:
                        dt = datetime.fromisoformat(last_run.replace('Z', '+00:00'))
                        self.query_one("#last_run").update(
                            f"Last run: {dt.strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                    except Exception:
                        self.query_one("#last_run").update(f"Last run: {last_run}")
                else:
                    self.query_one("#last_run").update("Last run: Never")

                self.query_one("#run_status").update("Status: [green]Ready[/green]")
            else:
                self.query_one("#run_status").update(
                    f"Status: [red]Error - {stats.get('error', 'Unknown')}[/red]"
                )
        except Exception as e:
            status_widget = self._get_status_widget()
            if status_widget:
                status_widget.update(f"Status: [red]Error: {str(e)[:40]}[/red]")
            logging.error(f"Failed to refresh pipeline stats: {str(e)}")

    @work(exclusive=True)
    async def run_pipeline_action(self) -> None:
        """Execute pipeline run."""
        button = self.query_one("#run_pipeline", Button)
        status_widget = self._get_status_widget()

        original_label = button.label
        button.disabled = True
        button.label = "⟳ Running..."
        if status_widget:
            status_widget.update("Status: [yellow]Pipeline running...[/yellow]")

        try:
            worker = self.run_worker(lambda: run_pipeline(limit=100), thread=True)
            await worker.wait()
            result = worker.result

            if "error" not in result:
                stats = result.get("statistics", {})
                processed = stats.get("processed", 0)
                failed = stats.get("failed", 0)
                skipped = stats.get("skipped", 0)

                msg = f"✓ Processed: {processed}, Failed: {failed}, Skipped: {skipped}"
                button.label = msg[:40]
                if status_widget:
                    status_widget.update(f"Status: [green]{msg}[/green]")

                # Kick off stats refresh as a new background worker (non awaitable)
                self.refresh_stats()
            else:
                error_msg = result.get("error", "Unknown error")
                button.label = f"✗ Failed: {error_msg[:30]}"
                if status_widget:
                    status_widget.update("Status: [red]Pipeline failed[/red]")

            self.set_timer(4, lambda: self._reset_button(button, original_label))

        except Exception as e:
            button.label = f"✗ Error: {str(e)[:25]}"
            status_widget = self._get_status_widget()
            if status_widget:
                status_widget.update(f"Status: [red]Exception: {str(e)[:35]}[/red]")
            self.set_timer(4, lambda: self._reset_button(button, original_label))

    def _reset_button(self, button: Button, label: str) -> None:
        """Reset button to original state."""
        button.label = label
        button.disabled = False