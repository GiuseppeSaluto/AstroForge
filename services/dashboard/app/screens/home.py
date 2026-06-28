import logging
from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal, Grid
from textual import work
from datetime import date, datetime
import asyncio

from app.client.api_client import (
    get_system_status,
    get_pipeline_stats,
    run_pipeline,
    get_nasa_asteroids,
)
from app import theme

logger = logging.getLogger(__name__)

_REFRESH_INTERVAL = 10
_WIDE_THRESHOLD = 90  # columns: below this, switch to single-column layout
_BAR_LABEL_W = 12     # fixed label width so both bars align visually


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
        color: $muted;
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

    .panel {
        border: solid $border_dim;
        padding: 1;
    }

    .panel-title {
        color: $accent;
        text-style: bold;
        margin: 0 0 1 0;
    }

    #quick_actions {
        height: 3;
        margin: 1 2;
    }

    #quick_actions Button {
        margin: 0 1;
    }
    """)

    _countdown: int = _REFRESH_INTERVAL
    _terminal_width: int = 80
    _system_status: tuple[bool, bool, bool] | None = None

    def compose(self):
        yield Static("", id="header")
        yield Static("", id="clock_bar")

        with Grid(id="main_grid"):
            # Left: system status + mission stats + bars
            with Vertical(classes="panel"):
                yield Static("", id="status_title", classes="panel-title")
                yield Static("", id="backend_status")
                yield Static("", id="mongodb_status")
                yield Static("", id="rust_status")
                yield Static("", id="stats_separator")
                yield Static("", id="stat_unprocessed")
                yield Static("", id="stat_analyzed")
                yield Static("", id="stat_risks")
                yield Static("", id="stat_lastrun")
                yield Static("", id="risk_bar")
                yield Static("", id="scan_bar")

            # Right: today's incoming NEOs from NASA
            with Vertical(classes="panel"):
                yield Static("", id="neo_title", classes="panel-title")
                yield Static("", id="neo_date")
                yield Static("", id="neo_list")

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
        self._render_panel_titles()
        self._update_data_age_bar()
        self.refresh_all_data()
        self.set_interval(1.0, self._tick)

    def on_resize(self, event) -> None:
        self._terminal_width = event.size.width
        self._apply_layout(event.size.width)

    # ── Layout adaptation ─────────────────────────────────────────────────────

    def _apply_layout(self, width: int) -> None:
        is_wide = width >= _WIDE_THRESHOLD
        self.query_one("#main_grid").styles.grid_size_columns = 2 if is_wide else 1
        self._render_header(width)
        self._update_clock_bar(width)

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

    def _render_panel_titles(self) -> None:
        self.query_one("#status_title", Static).update(
            f"[{theme.ACCENT}]── SYSTEM STATUS  /  MISSION STATS[/{theme.ACCENT}]"
        )
        self.query_one("#stats_separator", Static).update(
            f"[{theme.BORDER_DIM}]  {'─' * 28}[/{theme.BORDER_DIM}]"
        )
        self.query_one("#neo_title", Static).update(
            f"[{theme.ACCENT}]── TODAY'S INCOMING NEOs[/{theme.ACCENT}]"
        )

    # ── Tick ──────────────────────────────────────────────────────────────────

    def _tick(self) -> None:
        self._update_clock_bar()
        self._update_data_age_bar()
        self._countdown -= 1
        if self._countdown <= 0:
            self._countdown = _REFRESH_INTERVAL
            self.refresh_all_data()

    def _update_clock_bar(self, width: int | None = None) -> None:
        if width is None:
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

    def _bar_width(self) -> int:
        """Consistent bar width for both threat and data-age bars."""
        is_wide = self._terminal_width >= _WIDE_THRESHOLD
        panel = (self._terminal_width // 2 - 6) if is_wide else (self._terminal_width - 8)
        # reserve: 2 indent + label + 2 gap + bar + 2 gap + ~12 value text
        return max(8, min(panel - _BAR_LABEL_W - 18, 28))

    def _render_bar(self, ratio: float, color: str) -> str:
        """Render a filled/empty progress bar string at the standard width."""
        bw = self._bar_width()
        filled = round(ratio * bw)
        return (
            f"[{color}]{'█' * filled}[/{color}]"
            f"[{theme.BORDER_DIM}]{'░' * (bw - filled)}[/{theme.BORDER_DIM}]"
        )

    def _update_data_age_bar(self) -> None:
        elapsed = _REFRESH_INTERVAL - self._countdown
        ratio = elapsed / _REFRESH_INTERVAL
        bar = self._render_bar(ratio, theme.MUTED)
        age_str = f"{elapsed}s ago" if elapsed > 0 else "just updated"
        label = f"{'DATA AGE':<{_BAR_LABEL_W}}"
        try:
            self.query_one("#scan_bar").update(
                f"\n  [{theme.MUTED}]{label}[/{theme.MUTED}]  {bar}  [{theme.MUTED}]{age_str}[/{theme.MUTED}]"
            )
        except Exception:
            pass

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

    # ── Data refresh ──────────────────────────────────────────────────────────

    @work(exclusive=True)
    async def refresh_all_data(self) -> None:
        self._countdown = _REFRESH_INTERVAL
        today = date.today().strftime("%Y-%m-%d")
        try:
            loop = asyncio.get_event_loop()
            status, stats, neos = await asyncio.gather(
                loop.run_in_executor(None, get_system_status),
                loop.run_in_executor(None, get_pipeline_stats),
                loop.run_in_executor(None, lambda: get_nasa_asteroids(
                    start_date=today, end_date=today
                )),
            )

            backend = status.get("backend", {})
            rust = status.get("rust_engine", {})
            backend_ok = backend.get("status") == "healthy"
            mongodb_ok = backend.get("components", {}).get("mongodb") == "connected"
            rust_ok = rust.get("status") == "ok"

            self._system_status = (backend_ok, mongodb_ok, rust_ok)
            self._update_clock_bar()

            # ── Service status rows ────────────────────────────────────────
            def _row(label: str, ok: bool, ok_text: str, err_text: str) -> str:
                dot = "●" if ok else "○"
                c = theme.LOW if ok else theme.CRITICAL
                return (
                    f"  [{c}]{dot}[/{c}]"
                    f"  [{theme.TEXT}]{label:<14}[/{theme.TEXT}]"
                    f"[{c}]{ok_text if ok else err_text}[/{c}]"
                )

            self.query_one("#backend_status").update(
                _row("Backend", backend_ok, "ONLINE", "OFFLINE")
            )
            self.query_one("#mongodb_status").update(
                _row("MongoDB", mongodb_ok, "CONNECTED", "DISCONNECTED")
            )
            self.query_one("#rust_status").update(
                _row("Rust Engine", rust_ok, "READY", "UNREACHABLE")
            )

            # ── Mission stats ──────────────────────────────────────────────
            if stats.get("status") != "error":
                unprocessed = stats.get("unprocessed", 0)
                analyzed_today = stats.get("analyzed_today", 0)
                high_risks = stats.get("high_risks", 0)
                last_run = stats.get("last_pipeline_run")

                self.query_one("#stat_unprocessed").update(
                    f"  [{theme.ACCENT}]{unprocessed:>5}[/{theme.ACCENT}]"
                    f"  [{theme.MUTED}]unprocessed[/{theme.MUTED}]"
                )
                self.query_one("#stat_analyzed").update(
                    f"  [{theme.LOW}]{analyzed_today:>5}[/{theme.LOW}]"
                    f"  [{theme.MUTED}]analyzed today[/{theme.MUTED}]"
                )
                risk_color = theme.CRITICAL if high_risks > 0 else theme.LOW
                self.query_one("#stat_risks").update(
                    f"  [{risk_color}]{high_risks:>5}[/{risk_color}]"
                    f"  [{theme.MUTED}]high / critical risks[/{theme.MUTED}]"
                )

                if last_run:
                    try:
                        dt = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
                        lr_str = dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        lr_str = last_run
                else:
                    lr_str = "never"
                self.query_one("#stat_lastrun").update(
                    f"  [{theme.MUTED}]last run[/{theme.MUTED}]"
                    f"  [{theme.ACCENT}]{lr_str}[/{theme.ACCENT}]"
                )

                # ── Threat level bar ───────────────────────────────────────
                ratio = min(high_risks / max(analyzed_today, 1), 1.0)
                if ratio > 0.3:
                    bar_color, threat_label = theme.CRITICAL, "CRITICAL"
                elif ratio > 0.1:
                    bar_color, threat_label = theme.MEDIUM, "ELEVATED"
                else:
                    bar_color, threat_label = theme.LOW, "NOMINAL"
                bar = self._render_bar(ratio, bar_color)
                label = f"{'THREAT LVL':<{_BAR_LABEL_W}}"
                self.query_one("#risk_bar").update(
                    f"\n  [{theme.MUTED}]{label}[/{theme.MUTED}]"
                    f"  {bar}"
                    f"  [{bar_color}]{ratio * 100:.0f}%  {threat_label}[/{bar_color}]"
                )

            # ── Today's incoming NEOs (right panel) ───────────────────────
            self._render_neo_panel(neos, today)

        except Exception as e:
            logger.error(f"Failed to refresh home data: {e}")

    def _render_neo_panel(self, neos: list, today: str) -> None:
        self.query_one("#neo_date").update(
            f"  [{theme.MUTED}]{today}  ·  {len(neos)} objects tracked[/{theme.MUTED}]"
        )
        if not neos:
            self.query_one("#neo_list").update(
                f"[{theme.MUTED}]  No close approaches recorded for today.[/{theme.MUTED}]"
            )
            return

        sorted_neos = sorted(neos, key=lambda a: a.get("miss_distance_km", float("inf")))
        lines = []
        for neo in sorted_neos[:10]:
            name = (neo.get("name") or "?").strip("()")[:20]
            dist_km = neo.get("miss_distance_km", 0)
            vel = neo.get("velocity_kps", 0)
            hazardous = neo.get("is_potentially_hazardous", False)

            if dist_km >= 1_000_000:
                dist_str = f"{dist_km / 1_000_000:>6.2f}M km"
            else:
                dist_str = f"{dist_km:>9,.0f} km"

            flag = f"[{theme.CRITICAL}]⚠[/{theme.CRITICAL}]" if hazardous else f"[{theme.MUTED}] [/{theme.MUTED}]"
            lines.append(
                f"  {flag}  [{theme.TEXT}]{name:<20}[/{theme.TEXT}]"
                f"  [{theme.ACCENT}]{dist_str}[/{theme.ACCENT}]"
                f"  [{theme.MUTED}]{vel:>5.1f} km/s[/{theme.MUTED}]"
            )

        self.query_one("#neo_list").update("\n".join(lines))

    # ── Pipeline quick-run ────────────────────────────────────────────────────

    @work(exclusive=True)
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
                self.refresh_all_data()
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
