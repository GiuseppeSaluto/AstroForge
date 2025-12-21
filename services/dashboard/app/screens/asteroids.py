from textual.screen import Screen
from textual.widgets import DataTable, Static
from textual.containers import Vertical
from textual import work

from app.client.api_client import get_analyzed_asteroids

class AsteroidsScreen(Screen):

    def compose(self):
        yield Static("ANALYZED ASTEROIDS", id="title")

        with Vertical():
            table = DataTable(id="asteroids_table")
            table.add_columns(
                "ID",
                "Name",
                "Risk",
                "Score",
                "Energy (MT)",
                "Distance (km)",
                "Diameter (km)",
                "Velocity (km/s)",
            )
            yield table

    def on_mount(self):
        self.load_asteroids()

    @work
    async def load_asteroids(self):
        table = self.query_one("#asteroids_table", DataTable)
        table.clear()

        asteroids = get_analyzed_asteroids()

        for a in asteroids:
            table.add_row(
                a["id"],
                a["name"],
                a["risk_level"],
                f"{a['risk_score']:.1f}",
                f"{a['energy_mt']:.2f}",
                f"{a['distance_km']:.0f}",
                f"{a['diameter_km']:.3f}",
                f"{a['velocity_kps']:.2f}",
            )
