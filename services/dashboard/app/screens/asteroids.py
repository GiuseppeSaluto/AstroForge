from textual.screen import Screen
from textual.widgets import DataTable, Static, Button
from textual.containers import Vertical
from textual import work

from app.client.api_client import get_analyzed_asteroids


class AsteroidsScreen(Screen):
    """Display analyzed asteroids in a data table."""

    CSS = """
    AsteroidsScreen {
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

    #asteroids_table {
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
        """Compose asteroids screen layout."""
        yield Static("ANALYZED ASTEROIDS", id="title")

        self.table = DataTable(id="asteroids_table")

        self.table.add_columns(
            "ID",
            "Name",
            "Risk Level",
            "Score",
            "Energy (MT)",
            "Distance (km)",
            "Diameter (km)",
            "Velocity (km/s)",
        )

        yield self.table

        with Vertical(id="controls"):
            yield Button("🔄 Refresh", id="refresh", variant="primary")
            yield Button("⬅ Back", id="back")

    def on_mount(self):
        """Initialize and load asteroids data."""
        self.load_asteroids()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "refresh":
            self.load_asteroids()
        elif event.button.id == "back":
            self.app.action_show_home()

    @work(exclusive=True)
    async def load_asteroids(self):
        """Load and display analyzed asteroids."""
        self.table.clear()
        
        try:
            worker = self.run_worker(lambda: get_analyzed_asteroids(limit=200), thread=True)
            await worker.wait()
            asteroids = worker.result

            if not asteroids:
                self.table.add_row("No data", "--", "--", "--", "--", "--", "--", "--")
                return

            for a in asteroids:
                risk_level = a.get("risk_level", "Unknown")
                
                # Color code the risk level
                if risk_level in ["Critical", "High"]:
                    risk_display = f"[red]{risk_level}[/red]"
                elif risk_level == "Medium":
                    risk_display = f"[yellow]{risk_level}[/yellow]"
                else:
                    risk_display = f"[green]{risk_level}[/green]"

                self.table.add_row(
                    a.get("id", "?")[:8],
                    a.get("name", "?")[:20],
                    risk_display,
                    f"{a.get('risk_score', 0):.1f}",
                    f"{a.get('energy_mt', 0):.2f}",
                    f"{a.get('distance_km', 0):.0f}",
                    f"{a.get('diameter_km', 0):.3f}",
                    f"{a.get('velocity_kps', 0):.2f}",
                )
        except Exception as e:
            self.table.add_row(f"Error: {str(e)[:50]}", "--", "--", "--", "--", "--", "--", "--")
