import logging
from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Static
from textual.worker import WorkerCancelled
from textual import work

from app.client.api_client import get_asteroid_detail

logger = logging.getLogger(__name__)

_RISK_COLOR = {
    "Critical": "red",
    "High":     "red",
    "Medium":   "yellow",
    "Low":      "green",
}


class AsteroidDetailScreen(ModalScreen):

    CSS = """
    AsteroidDetailScreen {
        align: center middle;
    }

    #dialog {
        width: 82%;
        max-height: 90%;
        background: #1a2012;
        border: double #8f9a4d;
        padding: 0 2 1 2;
    }

    #header {
        height: 3;
        content-align: center middle;
        background: #2f341e;
        color: #f1e7af;
        text-style: bold;
        margin: 0 -2 1 -2;
    }

    .section-title {
        color: #8f9a4d;
        text-style: bold;
        margin: 1 0 0 0;
        height: 1;
    }

    #col_risk {
        width: 1fr;
        margin-right: 2;
    }

    #col_physical {
        width: 1fr;
    }

    .data-line {
        height: 1;
        color: #f1e7af;
    }

    #approaches_table {
        max-height: 10;
        border: solid #b9982f;
        margin: 0 0 0 0;
    }

    #nasa_status {
        height: 1;
        color: #b4a959;
        margin: 0 0 0 0;
    }

    #orbital_info {
        height: 1;
        color: #f1e7af;
    }

    #jpl_link {
        height: 1;
        color: #b9982f;
        margin-top: 0;
    }

    #close_btn {
        margin-top: 1;
        width: 14;
        align-horizontal: center;
    }

    #btn_row {
        height: auto;
        align-horizontal: center;
        margin-top: 1;
    }
    """

    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, asteroid: dict) -> None:
        super().__init__()
        self._asteroid = asteroid

    def compose(self) -> ComposeResult:
        a = self._asteroid
        name       = a.get("name", "Unknown")
        hazardous  = a.get("hazardous", False)
        risk_level = a.get("risk_level", "Unknown")
        risk_color = _RISK_COLOR.get(risk_level, "white")

        haz_badge = "   [red]⚠ POTENTIALLY HAZARDOUS[/red]" if hazardous else ""
        header_text = f"{name}{haz_badge}"

        analyzed_at = str(a.get("analyzed_at", "--"))[:10]

        with Vertical(id="dialog"):
            yield Static(header_text, id="header")

            with ScrollableContainer():
                with Horizontal():
                    with Vertical(id="col_risk"):
                        yield Static("── RISK ANALYSIS ──", classes="section-title")
                        yield Static(
                            f"Level:    [{risk_color}]{risk_level}[/{risk_color}]",
                            classes="data-line",
                        )
                        yield Static(f"Score:    {a.get('risk_score', 0):.1f} / 100", classes="data-line")
                        yield Static(f"Energy:   {a.get('energy_mt', 0):.3f} MT", classes="data-line")
                        yield Static(f"Analyzed: {analyzed_at}", classes="data-line")

                    with Vertical(id="col_physical"):
                        yield Static("── PHYSICAL DATA ──", classes="section-title")
                        yield Static(f"Diameter: {a.get('diameter_km', 0):.4f} km", classes="data-line")
                        yield Static(f"Distance: {a.get('distance_km', 0):,.0f} km", classes="data-line")
                        yield Static(f"Velocity: {a.get('velocity_kps', 0):.2f} km/s", classes="data-line")
                        yield Static("Loading…", id="diameter_range", classes="data-line")

                yield Static("── CLOSE APPROACHES ──", classes="section-title")
                approaches_table = DataTable(id="approaches_table")
                approaches_table.add_columns("Date", "Distance (km)", "Velocity (km/s)", "Body")
                yield approaches_table
                yield Static("[yellow]Fetching NASA data…[/yellow]", id="nasa_status")

                yield Static("── ORBITAL DATA ──", classes="section-title")
                yield Static("Loading…", id="orbital_info", classes="data-line")
                yield Static("", id="jpl_link")

            with Horizontal(id="btn_row"):
                yield Button("✕  Close", id="close_btn", variant="primary")

    def on_mount(self) -> None:
        self.load_nasa_detail()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close_btn":
            self.dismiss()

    def _safe_update(self, widget_id: str, content: str) -> None:
        """Update a widget only if the screen is still mounted."""
        try:
            self.query_one(widget_id).update(content)
        except Exception:
            pass

    @work(exclusive=True)
    async def load_nasa_detail(self) -> None:
        asteroid_id = self._asteroid.get("id", "")
        if not asteroid_id:
            self._safe_update("#nasa_status", "[red]No asteroid ID available[/red]")
            return

        try:
            worker = self.run_worker(
                lambda: get_asteroid_detail(asteroid_id),
                thread=True,
            )
            await worker.wait()
            data: dict = worker.result

            if not data:
                self._safe_update("#nasa_status", "[red]NASA data unavailable[/red]")
                self._safe_update("#diameter_range", "")
                return

            # Diameter min/max from NASA
            diam = data.get("diameter", {})
            d_min = diam.get("km_min")
            d_max = diam.get("km_max")
            if d_min is not None and d_max is not None:
                self._safe_update("#diameter_range", f"Range:    {d_min:.4f} – {d_max:.4f} km")
            else:
                self._safe_update("#diameter_range", "")

            # Close approaches — sort by date desc, show last 8
            approaches = data.get("close_approach_data", [])
            recent = sorted(approaches, key=lambda x: x.get("date", ""), reverse=True)[:8]
            try:
                table = self.query_one("#approaches_table", DataTable)
                for ca in recent:
                    table.add_row(
                        ca.get("date", "?"),
                        f"{ca.get('miss_distance_km', 0):,.0f}",
                        f"{ca.get('velocity_kps', 0):.2f}",
                        ca.get("orbiting_body", "?"),
                    )
            except Exception:
                pass

            self._safe_update(
                "#nasa_status",
                f"[green]{len(approaches)} total approaches — showing {len(recent)} most recent[/green]",
            )

            # Orbital data
            orb = data.get("orbital_data", {})
            if orb:
                parts = []
                if orb.get("orbit_class"):
                    parts.append(f"Class: {orb['orbit_class']}")
                if orb.get("orbital_period"):
                    parts.append(f"Period: {float(orb['orbital_period']):.1f} d")
                if orb.get("eccentricity"):
                    parts.append(f"Ecc: {orb['eccentricity']}")
                if orb.get("inclination"):
                    parts.append(f"Incl: {float(orb['inclination']):.2f}°")
                self._safe_update("#orbital_info", "  |  ".join(parts))
            else:
                self._safe_update("#orbital_info", "[dim]Orbital data not available[/dim]")

            jpl = data.get("nasa_jpl_url", "")
            if jpl:
                self._safe_update("#jpl_link", f"JPL: {jpl}")

        except WorkerCancelled:
            pass  # Modal dismissed before NASA data arrived — no action needed
        except Exception as e:
            logger.error(f"Detail load failed for {asteroid_id}: {e}", exc_info=True)
            self._safe_update("#nasa_status", f"[red]Error: {str(e)[:60]}[/red]")
