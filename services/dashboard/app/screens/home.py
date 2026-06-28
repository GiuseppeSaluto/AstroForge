import logging
from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal, Grid
from textual import work
from datetime import datetime
import asyncio

from app.client.api_client import (
    get_system_status,
    get_pipeline_stats,
    get_analyzed_asteroids,
    run_pipeline,
)
from app import theme

logger = logging.getLogger(__name__)

_REFRESH_INTERVAL = 10
_WIDE_THRESHOLD = 90


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
            # Left: system status + mission stats
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

            # Right: top threats from the Rust risk engine
            with Vertical(classes="panel"):
                yield Static("", id="threats_title", classes="panel-title")
                yield Static("", id="top_threats")

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
        self.query_one("#threats_title", Static).update(
            f"[{theme.ACCENT}]── TOP THREATS  /  RISK DISTRIBUTION[/{theme.ACCENT}]"
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

    def _update_data_age_bar(self) -> None:
        elapsed = _REFRESH_INTERVAL - self._countdown
        ratio = elapsed / _REFRESH_INTERVAL
        bar_width = self._bar_width(reserve=24)
        filled = round(ratio * bar_width)
        bar = (
            f"[{theme.MUTED}]{'█' * filled}[/{theme.MUTED}]"
            f"[{theme.BORDER_DIM}]{'░' * (bar_width - filled)}[/{theme.BORDER_DIM}]"
        )
        age_str = f"{elapsed}s ago" if elapsed > 0 else "just updated"
        try:
            self.query_one("#scan_bar").update(
                f"  [{theme.MUTED}]DATA AGE  {bar}  {age_str}[/{theme.MUTED}]"
            )
        except Exception:
            pass

    def _bar_width(self, reserve: int) -> int:
        is_wide = self._terminal_width >= _WIDE_THRESHOLD
        panel = (self._terminal_width // 2 - 6) if is_wide else (self._terminal_width - 8)
        return max(8, min(panel - reserve, 28))

    # ── Top threats renderer ──────────────────────────────────────────────────

    def _render_top_threats(self, asteroids: list) -> None:
        widget = self.query_one("#top_threats", Static)

        if not asteroids:
            widget.update(f"[{theme.MUTED}]No analyzed asteroids yet. Run the pipeline.[/{theme.MUTED}]")
            return

        sorted_asts = sorted(asteroids, key=lambda a: a.get("risk_score", 0), reverse=True)
        lines = []

        for a in sorted_asts[:5]:
            name = (a.get("name") or "?").strip("()")[:20]
            score = a.get("risk_score", 0)
            risk_level = a.get("risk_level", "?")
            hazardous = a.get("hazardous", False)
            color = theme.RISK_COLOR.get(risk_level, theme.TEXT)
            haz = f"[{theme.CRITICAL}]⚠[/{theme.CRITICAL}]" if hazardous else f"[{theme.MUTED}]·[/{theme.MUTED}]"
            lines.append(
                f"  {haz} [{theme.TEXT}]{name:<20}[/{theme.TEXT}]"
                f"  [{theme.MUTED}]{score:>5.1f}[/{theme.MUTED}]"
                f"  [{color}]{risk_level}[/{color}]"
            )

        # Risk distribution bars
        dist: dict[str, int] = {}
        for a in asteroids:
            lvl = a.get("risk_level", "?")
            dist[lvl] = dist.get(lvl, 0) + 1

        total = len(asteroids)
        max_count = max(dist.values()) if dist else 1
        bar_max = 12

        lines.append(f"\n  [{theme.BORDER_DIM}]{'─' * 32}[/{theme.BORDER_DIM}]")
        lines.append(f"  [{theme.MUTED}]DISTRIBUTION  ·  {total} analyzed[/{theme.MUTED}]")

        for level, color in [
            ("Critical", theme.CRITICAL),
            ("High", theme.HIGH),
            ("Medium", theme.MEDIUM),
            ("Low", theme.LOW),
        ]:
            count = dist.get(level, 0)
            filled = round(count / max_count * bar_max) if max_count else 0
            bar = (
                f"[{color}]{'█' * filled}[/{color}]"
                f"[{theme.BORDER_DIM}]{'░' * (bar_max - filled)}[/{theme.BORDER_DIM}]"
            )
            lines.append(
                f"  [{theme.MUTED}]{level:<8}[/{theme.MUTED}]  {bar}  [{color}]{count}[/{color}]"
            )

        widget.update("\n".join(lines))

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
        try:
            loop = asyncio.get_event_loop()
            status = await loop.run_in_executor(None, get_system_status)
            backend = status.get("backend", {})
            rust = status.get("rust_engine", {})

            backend_ok = backend.get("status") == "healthy"
            mongodb_ok = backend.get("components", {}).get("mongodb") == "connected"
            rust_ok = rust.get("status") == "ok"

            self._system_status = (backend_ok, mongodb_ok, rust_ok)
            self._update_clock_bar()

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

            if backend_ok:
                stats, asteroids = await asyncio.gather(
                    loop.run_in_executor(None, get_pipeline_stats),
                    loop.run_in_executor(None, lambda: get_analyzed_asteroids(limit=200)),
                )

                # ── Mission stats (left panel) ─────────────────────────────
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

                    ratio = min(high_risks / max(analyzed_today, 1), 1.0)
                    bar_width = self._bar_width(reserve=24)
                    filled = round(ratio * bar_width)
                    if ratio > 0.3:
                        bar_color, threat_label = theme.CRITICAL, "CRITICAL"
                    elif ratio > 0.1:
                        bar_color, threat_label = theme.MEDIUM, "ELEVATED"
                    else:
                        bar_color, threat_label = theme.LOW, "NOMINAL"
                    bar_filled = f"[{bar_color}]{'█' * filled}[/{bar_color}]"
                    bar_empty = f"[{theme.MUTED}]{'░' * (bar_width - filled)}[/{theme.MUTED}]"
                    self.query_one("#risk_bar").update(
                        f"  [{theme.MUTED}]THREAT    {bar_filled}{bar_empty}"
                        f"  {ratio * 100:.0f}%  {threat_label}[/{theme.MUTED}]"
                        if bar_color == theme.LOW else
                        f"  [{theme.MUTED}]THREAT    [/{theme.MUTED}]"
                        f"{bar_filled}{bar_empty}"
                        f"  [{bar_color}]{ratio * 100:.0f}%  {threat_label}[/{bar_color}]"
                    )

                # ── Top threats (right panel) ──────────────────────────────
                self._render_top_threats(asteroids)

            else:
                self.query_one("#top_threats", Static).update(
                    f"[{theme.CRITICAL}]Backend unavailable.[/{theme.CRITICAL}]"
                )

        except Exception as e:
            logger.error(f"Failed to refresh home data: {e}")

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
