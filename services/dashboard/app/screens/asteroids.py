from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Static
from textual import work

from app.client.api_client import get_analyzed_asteroids
from app.screens.asteroid_detail import AsteroidDetailScreen
from app import theme

_RISK_COLOR = theme.RISK_COLOR

_FILTERS = ["All", "Low", "Medium", "High", "Critical"]


class AsteroidsScreen(Screen):

    CSS = theme.apply("""
    AsteroidsScreen {
        layout: vertical;
    }

    #title {
        dock: top;
        height: 2;
        content-align: center middle;
        text-style: bold;
        color: $accent;
        background: $surface;
    }

    #filter_row {
        height: 3;
        margin: 0 2;
        align-vertical: middle;
    }

    #filter_label {
        width: auto;
        color: $muted;
        content-align: left middle;
        margin-right: 1;
    }

    .filter-btn {
        margin: 0 1;
        min-width: 10;
    }

    .filter-btn.active {
        background: $accent;
        color: $bg;
        text-style: bold;
        border-top: tall $accent;
        border-bottom: tall $border_dim;
    }

    #asteroids_table {
        border: solid $border;
        margin: 0 2;
    }

    #status_bar {
        height: 1;
        margin: 0 2;
        color: $muted;
        content-align: left middle;
    }

    #controls {
        height: auto;
        dock: bottom;
        margin: 0 2 1 2;
    }

    #controls Button {
        margin: 0 1;
    }
    """)

    def __init__(self) -> None:
        super().__init__()
        self._all_asteroids: list = []
        self._asteroid_data: dict[str, dict] = {}
        self._active_filter: str = "All"

    def compose(self) -> ComposeResult:
        yield Static("ANALYZED ASTEROIDS", id="title")

        with Horizontal(id="filter_row"):
            yield Static("Risk filter:", id="filter_label")
            for f in _FILTERS:
                classes = "filter-btn active" if f == "All" else "filter-btn"
                yield Button(f, id=f"filter_{f.lower()}", classes=classes)

        table = DataTable(id="asteroids_table", cursor_type="row")
        table.add_columns(
            "Name",
            "Risk Level",
            "Score",
            "Energy (MT)",
            "Distance (km)",
            "Diameter (km)",
            "Velocity (km/s)",
            "⚠",
        )
        yield table

        yield Static("Loading…", id="status_bar")

        with Horizontal(id="controls"):
            yield Button("🔄 Refresh", id="refresh", variant="primary")
            yield Button("⬅ Back", id="back")

    def on_mount(self) -> None:
        self.load_asteroids()

    # ── Events ────────────────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id

        if btn_id and btn_id.startswith("filter_"):
            label = btn_id.replace("filter_", "").capitalize()
            # "all" → "All", "critical" → "Critical", etc.
            label = next((f for f in _FILTERS if f.lower() == label.lower()), "All")
            self._set_filter(label)
            return

        if btn_id == "refresh":
            self.load_asteroids()
        elif btn_id == "back":
            self.app.action_show_home()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        asteroid_id = str(event.row_key.value)
        asteroid = self._asteroid_data.get(asteroid_id)
        if asteroid:
            self.app.push_screen(AsteroidDetailScreen(asteroid))

    # ── Filter helpers ────────────────────────────────────────────────────────

    def _set_filter(self, label: str) -> None:
        self._active_filter = label
        for f in _FILTERS:
            btn = self.query_one(f"#filter_{f.lower()}", Button)
            if f == label:
                btn.add_class("active")
            else:
                btn.remove_class("active")
        self._render_table()

    def _filtered(self) -> list:
        if self._active_filter == "All":
            return self._all_asteroids
        return [a for a in self._all_asteroids if a.get("risk_level") == self._active_filter]

    # ── Table rendering ───────────────────────────────────────────────────────

    def _render_table(self) -> None:
        table = self.query_one("#asteroids_table", DataTable)
        table.clear()

        asteroids = self._filtered()

        if not asteroids:
            table.add_row("No results for this filter", "--", "--", "--", "--", "--", "--", "--")
            self.query_one("#status_bar").update(
                f"[{theme.MEDIUM}]0 asteroids ({self._active_filter} filter)[/{theme.MEDIUM}]"
            )
            return

        for a in asteroids:
            risk_level = a.get("risk_level", "Unknown")
            color = _RISK_COLOR.get(risk_level, "white")

            table.add_row(
                a.get("name", "?")[:28],
                f"[{color}]{risk_level}[/{color}]",
                f"{a.get('risk_score', 0):.1f}",
                f"{a.get('energy_mt', 0):.3f}",
                f"{a.get('distance_km', 0):,.0f}",
                f"{a.get('diameter_km', 0):.4f}",
                f"{a.get('velocity_kps', 0):.2f}",
                "[red]●[/red]" if a.get("hazardous") else "[green]○[/green]",
                key=a.get("id", ""),
            )

        total = len(self._all_asteroids)
        shown = len(asteroids)
        filter_note = f" — filter: {self._active_filter}" if self._active_filter != "All" else ""
        self.query_one("#status_bar").update(
            f"[{theme.LOW}]{shown} asteroids{filter_note}[/{theme.LOW}]  "
            f"[{theme.MUTED}]({total} total)  ↑↓ navigate  Enter / click to view detail[/{theme.MUTED}]"
        )

    # ── Data loading ──────────────────────────────────────────────────────────

    @work(exclusive=True)
    async def load_asteroids(self) -> None:
        self.query_one("#status_bar").update("[yellow]Loading…[/yellow]")
        table = self.query_one("#asteroids_table", DataTable)
        table.clear()

        try:
            worker = self.run_worker(
                lambda: get_analyzed_asteroids(limit=200),
                thread=True,
            )
            await worker.wait()
            asteroids: list = worker.result

            self._all_asteroids = asteroids
            self._asteroid_data = {a.get("id", ""): a for a in asteroids}
            self._render_table()

        except Exception as e:
            table.add_row(
                f"Error: {str(e)[:50]}", "--", "--", "--", "--", "--", "--", "--"
            )
            self.query_one("#status_bar").update(f"[{theme.CRITICAL}]Load failed: {str(e)[:60]}[/{theme.CRITICAL}]")
