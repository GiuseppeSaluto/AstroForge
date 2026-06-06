import logging
from datetime import date, timedelta

from rich.text import Text
from textual import work
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Static

from app.client.api_client import get_nasa_asteroids

try:
    import plotext as _plt
    _PLOTEXT = True
except ImportError:
    _PLOTEXT = False

logger = logging.getLogger(__name__)

_DIAMETER_BUCKETS = [
    ("<0.1 km",  0.0,         0.1),
    ("0.1-0.5",  0.1,         0.5),
    ("0.5-1 km", 0.5,         1.0),
    ("1-5 km",   1.0,         5.0),
    (">5 km",    5.0,         float("inf")),
]


def _distance_chart(asteroids: list, width: int, height: int) -> Text:
    """Scatter plot: miss distance (million km) per asteroid, grouped by date."""
    sorted_asts = sorted(asteroids, key=lambda a: a.get("close_approach_date", ""))

    _plt.clear_figure()
    _plt.plotsize(width, height)
    _plt.title("Miss Distance over Time")
    _plt.ylabel("Distance (million km)")
    _plt.theme("dark")

    if not sorted_asts:
        _plt.scatter([0], [0], label="No data")
        return Text.from_ansi(_plt.build())

    x_all = list(range(len(sorted_asts)))
    safe_x  = [i for i, a in enumerate(sorted_asts) if not a.get("is_potentially_hazardous")]
    safe_y  = [sorted_asts[i]["miss_distance_km"] / 1_000_000 for i in safe_x]
    haz_x   = [i for i, a in enumerate(sorted_asts) if a.get("is_potentially_hazardous")]
    haz_y   = [sorted_asts[i]["miss_distance_km"] / 1_000_000 for i in haz_x]

    if safe_x:
        _plt.scatter(safe_x, safe_y, label="Safe", marker="dot", color="green")
    if haz_x:
        _plt.scatter(haz_x, haz_y, label="Hazardous", marker="dot", color="red")

    # x-axis: show at most 7 date labels to avoid crowding
    step = max(1, len(x_all) // 7)
    ticks  = x_all[::step]
    labels = [sorted_asts[i]["close_approach_date"][-5:] for i in ticks]
    _plt.xticks(ticks, labels)

    return Text.from_ansi(_plt.build())


def _diameter_chart(asteroids: list, width: int, height: int) -> Text:
    """Bar chart: asteroid count per diameter bucket."""
    labels = [b[0] for b in _DIAMETER_BUCKETS]
    counts = [0] * len(_DIAMETER_BUCKETS)

    for a in asteroids:
        d = a.get("diameter_km_avg", 0.0)
        for i, (_, lo, hi) in enumerate(_DIAMETER_BUCKETS):
            if lo <= d < hi:
                counts[i] += 1
                break

    _plt.clear_figure()
    _plt.plotsize(width, height)
    _plt.title("Size Distribution (avg diameter)")
    _plt.ylabel("Count")
    _plt.xlabel("Diameter range (km)")
    _plt.theme("dark")
    _plt.bar(labels, counts, color="olive")

    return Text.from_ansi(_plt.build())


class ChartsScreen(Screen):
    """Visualization screen — distance/time scatter and size distribution bar chart."""

    CSS = """
    ChartsScreen {
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

    #controls {
        height: auto;
        margin: 0 2;
        padding: 0;
    }

    #date_range {
        width: 1fr;
        height: 1;
        color: #b9982f;
        content-align: left middle;
        margin: 0 1;
    }

    #chart_distance {
        border: solid #8f9a4d;
        margin: 1 2 0 2;
        height: 1fr;
    }

    #chart_diameter {
        border: solid #b9982f;
        margin: 1 2 0 2;
        height: 1fr;
    }

    #status {
        height: 1;
        color: #b4a959;
        margin: 0 2;
    }

    #footer {
        dock: bottom;
        height: 1;
        color: #b4a959;
        text-align: center;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._end: date = date.today()
        self._start: date = self._end - timedelta(days=7)

    def compose(self):
        yield Static("NEO CHARTS", id="title")

        with Horizontal(id="controls"):
            yield Static("", id="date_range")
            yield Button("◀ Prev", id="prev_week")
            yield Button("Next ▶", id="next_week")
            yield Button("🔄 Refresh", id="refresh", variant="primary")
            yield Button("⬅ Back", id="back")

        yield Static("Loading…", id="chart_distance")
        yield Static("Loading…", id="chart_diameter")
        yield Static("", id="status")

        yield Static(
            "h Home • a Asteroids • c Charts • p Pipeline • l Logs • q Quit",
            id="footer",
        )

    def on_mount(self) -> None:
        self._update_range_label()
        self.load_charts()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "prev_week":
            self._start -= timedelta(days=7)
            self._end   -= timedelta(days=7)
            self._update_range_label()
            self.load_charts()
        elif event.button.id == "next_week":
            self._start += timedelta(days=7)
            self._end   += timedelta(days=7)
            self._update_range_label()
            self.load_charts()
        elif event.button.id == "refresh":
            self.load_charts()
        elif event.button.id == "back":
            self.app.action_show_home()

    def _update_range_label(self) -> None:
        self.query_one("#date_range").update(
            f"Range: {self._start} → {self._end}"
        )

    @work(exclusive=True)
    async def load_charts(self) -> None:
        if not _PLOTEXT:
            self.query_one("#status").update(
                "[red]plotext not installed — run: pip install plotext[/red]"
            )
            return

        self.query_one("#status").update("[yellow]Loading…[/yellow]")
        self.query_one("#chart_distance").update("Fetching data from API…")
        self.query_one("#chart_diameter").update("")

        start_str = self._start.strftime("%Y-%m-%d")
        end_str   = self._end.strftime("%Y-%m-%d")

        try:
            worker = self.run_worker(
                lambda: get_nasa_asteroids(start_date=start_str, end_date=end_str),
                thread=True,
            )
            await worker.wait()
            asteroids: list = worker.result

            if not asteroids:
                self.query_one("#chart_distance").update("No asteroids found for this range.")
                self.query_one("#chart_diameter").update("")
                self.query_one("#status").update("[yellow]No data returned[/yellow]")
                return

            # Terminal dimensions minus borders/padding
            w = max(40, self.app.size.width - 8)
            h = max(8,  (self.app.size.height - 14) // 2)

            dist = _distance_chart(asteroids, w, h)
            diam = _diameter_chart(asteroids, w, h)

            self.query_one("#chart_distance").update(dist)
            self.query_one("#chart_diameter").update(diam)
            self.query_one("#status").update(
                f"[green]{len(asteroids)} asteroids — {start_str} → {end_str}[/green]"
            )

        except Exception as e:
            logger.error(f"Chart load error: {e}", exc_info=True)
            self.query_one("#status").update(f"[red]Error: {str(e)[:80]}[/red]")
