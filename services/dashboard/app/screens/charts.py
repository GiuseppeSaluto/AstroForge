import logging
from datetime import date, timedelta

from rich.text import Text
from textual import work
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Button, Static

from app.worker_safety import safe_worker

from app.client.api_client import get_nasa_asteroids
from app.widgets.global_status_bar import GlobalStatusBar
from app import theme

try:
    import plotext as _plt
    _PLOTEXT = True
except ImportError:
    _PLOTEXT = False

logger = logging.getLogger(__name__)

_DIAMETER_BUCKETS = [
    ("<0.1 km",  0.0,  0.1),
    ("0.1-0.5",  0.1,  0.5),
    ("0.5-1 km", 0.5,  1.0),
    ("1-5 km",   1.0,  5.0),
    (">5 km",    5.0,  float("inf")),
]

_VELOCITY_BUCKETS = [
    ("<5 km/s",   0.0,  5.0),
    ("5-10",      5.0,  10.0),
    ("10-15",     10.0, 15.0),
    ("15-20",     15.0, 20.0),
    ("20-30",     20.0, 30.0),
    (">30 km/s",  30.0, float("inf")),
]


def _stats_bar(asteroids: list) -> str:
    total = len(asteroids)
    hazardous = sum(1 for a in asteroids if a.get("is_potentially_hazardous"))
    haz_pct = round(hazardous / total * 100) if total else 0

    closest = min(asteroids, key=lambda a: a.get("miss_distance_km", float("inf")))
    closest_km = closest.get("miss_distance_km", 0)
    closest_name = (closest.get("name") or "?").strip("()")

    fastest = max(asteroids, key=lambda a: a.get("velocity_kps", 0))
    fastest_kps = fastest.get("velocity_kps", 0)

    avg_diam = sum(a.get("diameter_km_avg", 0) for a in asteroids) / total

    return (
        f"[{theme.TEXT}]Total:[/{theme.TEXT}] {total}  "
        f"[{theme.CRITICAL}]Hazardous:[/{theme.CRITICAL}] {hazardous} ({haz_pct}%)  "
        f"[{theme.MEDIUM}]Closest:[/{theme.MEDIUM}] {closest_name} @ {closest_km:,.0f} km  "
        f"[{theme.HIGH}]Fastest:[/{theme.HIGH}] {fastest_kps:.1f} km/s  "
        f"[{theme.LOW}]Avg ⌀:[/{theme.LOW}] {avg_diam:.3f} km"
    )


def _y_ticks(values: list[float], n_ticks: int = 5) -> tuple[list, list[str]]:
    """Generate at most n_ticks evenly spaced y-axis ticks with clean labels."""
    y_max = max(values) if values else 1.0
    if y_max == 0:
        y_max = 1.0
    step = y_max / n_ticks
    ticks = [round(step * i, 3) for i in range(n_ticks + 1)]
    return ticks, [f"{v:.2f}".rstrip("0").rstrip(".") for v in ticks]


def _count_ticks(max_count: int, n_ticks: int = 5) -> tuple[list, list[str]]:
    """Integer y-axis ticks for count-based charts."""
    step = max(1, max_count // n_ticks)
    ticks = list(range(0, max_count + step + 1, step))
    return ticks, [str(v) for v in ticks]


def _distance_chart(asteroids: list, width: int, height: int) -> Text:
    sorted_asts = sorted(asteroids, key=lambda a: a.get("close_approach_date", ""))

    _plt.clear_figure()
    _plt.plotsize(width, height)
    _plt.title("Miss Distance over Time (Mkm = million km)")
    _plt.theme("dark")

    if not sorted_asts:
        _plt.scatter([0], [0], label="No data")
        return Text.from_ansi(_plt.build())

    x_all = list(range(len(sorted_asts)))
    safe_x = [i for i, a in enumerate(sorted_asts) if not a.get("is_potentially_hazardous")]
    safe_y = [sorted_asts[i]["miss_distance_km"] / 1_000_000 for i in safe_x]
    haz_x  = [i for i, a in enumerate(sorted_asts) if a.get("is_potentially_hazardous")]
    haz_y  = [sorted_asts[i]["miss_distance_km"] / 1_000_000 for i in haz_x]

    if safe_x:
        _plt.scatter(safe_x, safe_y, label="Safe", marker="dot", color=theme.CHART_SAFE)
    if haz_x:
        _plt.scatter(haz_x, haz_y, label="Hazardous", marker="dot", color=theme.CHART_HAZARDOUS)

    step = max(1, len(x_all) // 7)
    _plt.xticks(x_all[::step], [sorted_asts[i]["close_approach_date"][-5:] for i in x_all[::step]])

    all_y = safe_y + haz_y
    if all_y:
        ticks, labels = _y_ticks(all_y)
        labels = [f"{t:.1f}M" for t in ticks]
        _plt.yticks(ticks, labels)

    return Text.from_ansi(_plt.build())


def _diameter_chart(asteroids: list, width: int, height: int) -> Text:
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
    _plt.title("Size Distribution")
    _plt.theme("dark")
    _plt.bar(labels, counts, color=theme.CHART_BAR)

    y_max = max(counts) if max(counts) > 0 else 1
    ticks, tick_labels = _count_ticks(y_max)
    _plt.yticks(ticks, tick_labels)

    return Text.from_ansi(_plt.build())


def _velocity_chart(asteroids: list, width: int, height: int) -> Text:
    labels = [b[0] for b in _VELOCITY_BUCKETS]
    counts = [0] * len(_VELOCITY_BUCKETS)

    for a in asteroids:
        v = a.get("velocity_kps", 0.0)
        for i, (_, lo, hi) in enumerate(_VELOCITY_BUCKETS):
            if lo <= v < hi:
                counts[i] += 1
                break

    _plt.clear_figure()
    _plt.plotsize(width, height)
    _plt.title("Velocity Distribution")
    _plt.theme("dark")
    _plt.bar(labels, counts, color=theme.CHART_BAR)

    y_max = max(counts) if max(counts) > 0 else 1
    ticks, tick_labels = _count_ticks(y_max)
    _plt.yticks(ticks, tick_labels)

    return Text.from_ansi(_plt.build())


class ChartsScreen(Screen):

    CSS = theme.apply("""
    ChartsScreen {
        layout: vertical;
    }

    #title {
        height: 2;
        content-align: center middle;
        text-style: bold;
        color: $accent;
        background: $surface;
    }

    #controls {
        height: auto;
        margin: 0 2;
        padding: 0;
    }

    #date_range {
        width: 1fr;
        height: 1;
        color: $muted;
        content-align: left middle;
        margin: 0 1;
    }

    #stats_bar {
        height: 1;
        margin: 0 3;
        color: $text;
        content-align: left middle;
    }

    #chart_distance {
        border: solid $border_dim;
        margin: 1 2 0 2;
        height: 1fr;
    }

    #bottom_charts {
        height: 1fr;
        margin: 0 2 0 2;
    }

    #chart_diameter {
        border: solid $border_dim;
        margin: 1 1 0 0;
        width: 1fr;
    }

    #chart_velocity {
        border: solid $border_dim;
        margin: 1 0 0 1;
        width: 1fr;
    }

    #status {
        height: 1;
        color: $muted;
        margin: 0 2;
    }

    #footer {
        dock: bottom;
        height: 1;
        color: $muted;
        text-align: center;
    }
    """)

    def __init__(self) -> None:
        super().__init__()
        self._end: date = date.today()
        self._start: date = self._end - timedelta(days=7)

    def compose(self):
        yield GlobalStatusBar()
        yield Static("NEO CHARTS", id="title")

        with Horizontal(id="controls"):
            yield Static("", id="date_range")
            yield Button("◀ Prev", id="prev_week")
            yield Button("Next ▶", id="next_week")
            yield Button("🔄 Refresh", id="refresh", variant="primary")
            yield Button("⬅ Back", id="back")

        yield Static("Loading stats…", id="stats_bar")
        yield Static("Loading…", id="chart_distance")

        with Horizontal(id="bottom_charts"):
            yield Static("Loading…", id="chart_diameter")
            yield Static("Loading…", id="chart_velocity")

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
        self.query_one("#date_range").update(f"Range: {self._start} → {self._end}")

    @work(exclusive=True)
    @safe_worker
    async def load_charts(self) -> None:
        if not _PLOTEXT:
            self.query_one("#status").update(
                "[red]plotext not installed — run: pip install plotext[/red]"
            )
            return

        self.query_one("#status").update("[yellow]Loading…[/yellow]")
        self.query_one("#stats_bar").update("Fetching data…")
        self.query_one("#chart_distance").update("Fetching data from API…")
        self.query_one("#chart_diameter").update("")
        self.query_one("#chart_velocity").update("")

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
                self.query_one("#stats_bar").update("[yellow]No data[/yellow]")
                self.query_one("#chart_distance").update("No asteroids found for this range.")
                self.query_one("#chart_diameter").update("")
                self.query_one("#chart_velocity").update("")
                self.query_one("#status").update("[yellow]No data returned[/yellow]")
                return

            w_full = max(40, self.app.size.width - 8)
            w_half = max(20, (self.app.size.width - 12) // 2)
            h_top  = max(8,  (self.app.size.height - 18) // 2)
            h_bot  = max(6,  (self.app.size.height - 18) // 2)

            self.query_one("#stats_bar").update(_stats_bar(asteroids))
            self.query_one("#chart_distance").update(_distance_chart(asteroids, w_full, h_top))
            self.query_one("#chart_diameter").update(_diameter_chart(asteroids, w_half, h_bot))
            self.query_one("#chart_velocity").update(_velocity_chart(asteroids, w_half, h_bot))
            self.query_one("#status").update(
                f"[{theme.LOW}]{len(asteroids)} asteroids — {start_str} → {end_str}[/{theme.LOW}]"
            )

        except Exception as e:
            logger.error(f"Chart load error: {e}", exc_info=True)
            self.query_one("#status").update(f"[{theme.CRITICAL}]Error: {str(e)[:80]}[/{theme.CRITICAL}]")
