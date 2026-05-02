from textual.widgets import DataTable
from typing import List, Dict, Any


class AsteroidTable(DataTable):
    """A custom data table widget for displaying asteroids."""

    DEFAULT_CSS = """
    AsteroidTable {
        border: solid #b9982f;
        margin: 1 0;
        height: 1fr;
    }
    """

    def __init__(self):
        super().__init__()
        self._setup_columns()

    def _setup_columns(self) -> None:
        """Setup table columns."""
        self.add_columns(
            "ID",
            "Name",
            "Risk Level",
            "Score",
            "Energy (MT)",
            "Distance (km)",
            "Diameter (km)",
            "Velocity (km/s)",
        )

    def load_asteroids(self, asteroids: List[Dict[str, Any]]) -> None:
        """Load asteroids data into the table."""
        self.clear()

        if not asteroids:
            self.add_row(
                "No data",
                "--",
                "--",
                "--",
                "--",
                "--",
                "--",
                "--",
            )
            return

        for asteroid in asteroids:
            risk_level = asteroid.get("risk_level", "Unknown")

            # Color code the risk level
            if risk_level in ["Critical", "High"]:
                risk_display = f"[red]{risk_level}[/red]"
            elif risk_level == "Medium":
                risk_display = f"[yellow]{risk_level}[/yellow]"
            else:
                risk_display = f"[olive]{risk_level}[/olive]"

            self.add_row(
                asteroid.get("id", "?")[:8],
                asteroid.get("name", "?")[:20],
                risk_display,
                f"{asteroid.get('risk_score', 0):.1f}",
                f"{asteroid.get('energy_mt', 0):.2f}",
                f"{asteroid.get('distance_km', 0):.0f}",
                f"{asteroid.get('diameter_km', 0):.3f}",
                f"{asteroid.get('velocity_kps', 0):.2f}",
            )
