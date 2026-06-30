import asyncio
import logging
from datetime import datetime

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static
from textual import work

from app.client.api_client import get_system_status, get_pipeline_stats
from app import theme

logger = logging.getLogger(__name__)

_REFRESH_INTERVAL = 10
_BAR_LABEL_W = 12


class StatusPanel(Widget):
    """Left home panel: service status, mission stats, and live bars."""

    class StatusChanged(Message):
        """Posted when service health is fetched. HomeScreen uses this to update the clock bar."""
        def __init__(self, backend_ok: bool, mongodb_ok: bool, rust_ok: bool) -> None:
            super().__init__()
            self.backend_ok = backend_ok
            self.mongodb_ok = mongodb_ok
            self.rust_ok = rust_ok

    DEFAULT_CSS = theme.apply("""
    StatusPanel {
        border: solid $border_dim;
        padding: 1;
        height: 100%;
    }

    StatusPanel .sp-title {
        color: $accent;
        text-style: bold;
        margin: 0 0 1 0;
    }
    """)

    _countdown: int = _REFRESH_INTERVAL

    def compose(self) -> ComposeResult:
        yield Static("", id="sp_title", classes="sp-title")
        yield Static("", id="sp_backend")
        yield Static("", id="sp_mongodb")
        yield Static("", id="sp_rust")
        yield Static("", id="sp_separator")
        yield Static("", id="sp_unprocessed")
        yield Static("", id="sp_analyzed")
        yield Static("", id="sp_risks")
        yield Static("", id="sp_lastrun")
        yield Static("", id="sp_risk_bar")
        yield Static("", id="sp_age_bar")

    def on_mount(self) -> None:
        self.query_one("#sp_title", Static).update(
            f"[{theme.ACCENT}]── SYSTEM STATUS  /  MISSION STATS[/{theme.ACCENT}]"
        )
        self.query_one("#sp_separator", Static).update(
            f"[{theme.BORDER_DIM}]  {'─' * 28}[/{theme.BORDER_DIM}]"
        )
        self._update_age_bar()
        self.refresh_data()
        self.set_interval(1.0, self._tick)

    # ── Tick ──────────────────────────────────────────────────────────────────

    def _tick(self) -> None:
        self._update_age_bar()
        self._countdown -= 1
        if self._countdown <= 0:
            self._countdown = _REFRESH_INTERVAL
            self.refresh_data()

    # ── Bar helpers ───────────────────────────────────────────────────────────

    def _bar_width(self) -> int:
        try:
            panel_w = (self.app.size.width // 2) - 8
        except Exception:
            panel_w = 40
        return max(8, min(panel_w - _BAR_LABEL_W - 16, 24))

    def _render_bar(self, ratio: float, color: str) -> str:
        bw = self._bar_width()
        filled = round(ratio * bw)
        return (
            f"[{color}]{'█' * filled}[/{color}]"
            f"[{theme.BORDER_DIM}]{'░' * (bw - filled)}[/{theme.BORDER_DIM}]"
        )

    def _update_age_bar(self) -> None:
        elapsed = _REFRESH_INTERVAL - self._countdown
        ratio = elapsed / _REFRESH_INTERVAL
        bar = self._render_bar(ratio, theme.MUTED)
        age_str = f"{elapsed}s ago" if elapsed > 0 else "just updated"
        label = f"{'DATA AGE':<{_BAR_LABEL_W}}"
        try:
            self.query_one("#sp_age_bar").update(
                f"\n  [{theme.MUTED}]{label}[/{theme.MUTED}]"
                f"  {bar}"
                f"  [{theme.MUTED}]{age_str}[/{theme.MUTED}]"
            )
        except Exception:
            pass

    # ── Data refresh ──────────────────────────────────────────────────────────

    @work(exclusive=True)
    async def refresh_data(self) -> None:
        self._countdown = _REFRESH_INTERVAL
        try:
            loop = asyncio.get_event_loop()
            status, stats = await asyncio.gather(
                loop.run_in_executor(None, get_system_status),
                loop.run_in_executor(None, get_pipeline_stats),
            )

            backend = status.get("backend", {})
            rust = status.get("rust_engine", {})
            backend_ok = backend.get("status") == "healthy"
            mongodb_ok = backend.get("components", {}).get("mongodb") == "connected"
            rust_ok = rust.get("status") == "ok"

            # Notify HomeScreen so it can update the clock bar dots
            self.post_message(self.StatusChanged(backend_ok, mongodb_ok, rust_ok))

            def _row(label: str, ok: bool, ok_text: str, err_text: str) -> str:
                dot = "●" if ok else "○"
                c = theme.LOW if ok else theme.CRITICAL
                return (
                    f"  [{c}]{dot}[/{c}]"
                    f"  [{theme.TEXT}]{label:<14}[/{theme.TEXT}]"
                    f"[{c}]{ok_text if ok else err_text}[/{c}]"
                )

            self.query_one("#sp_backend").update(
                _row("Backend", backend_ok, "ONLINE", "OFFLINE")
            )
            self.query_one("#sp_mongodb").update(
                _row("MongoDB", mongodb_ok, "CONNECTED", "DISCONNECTED")
            )
            self.query_one("#sp_rust").update(
                _row("Rust Engine", rust_ok, "READY", "UNREACHABLE")
            )

            if stats.get("status") != "error":
                unprocessed = stats.get("unprocessed", 0)
                analyzed_today = stats.get("analyzed_today", 0)
                total_analyzed = stats.get("total_analyzed", 0)
                high_risks = stats.get("high_risks", 0)
                last_run = stats.get("last_pipeline_run")

                self.query_one("#sp_unprocessed").update(
                    f"  [{theme.ACCENT}]{unprocessed:>5}[/{theme.ACCENT}]"
                    f"  [{theme.MUTED}]unprocessed[/{theme.MUTED}]"
                )
                self.query_one("#sp_analyzed").update(
                    f"  [{theme.LOW}]{analyzed_today:>5}[/{theme.LOW}]"
                    f"  [{theme.MUTED}]analyzed today[/{theme.MUTED}]"
                )
                risk_color = theme.CRITICAL if high_risks > 0 else theme.LOW
                self.query_one("#sp_risks").update(
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
                self.query_one("#sp_lastrun").update(
                    f"  [{theme.MUTED}]last run[/{theme.MUTED}]"
                    f"  [{theme.ACCENT}]{lr_str}[/{theme.ACCENT}]"
                )

                ratio = high_risks / max(total_analyzed, 1)
                if ratio > 0.3:
                    bar_color, threat_label = theme.CRITICAL, "CRITICAL"
                elif ratio > 0.1:
                    bar_color, threat_label = theme.MEDIUM, "ELEVATED"
                else:
                    bar_color, threat_label = theme.LOW, "NOMINAL"
                bar = self._render_bar(ratio, bar_color)
                label = f"{'THREAT LVL':<{_BAR_LABEL_W}}"
                self.query_one("#sp_risk_bar").update(
                    f"\n  [{theme.MUTED}]{label}[/{theme.MUTED}]"
                    f"  {bar}"
                    f"  [{bar_color}]{ratio * 100:.0f}%  {threat_label}[/{bar_color}]"
                )

        except Exception as e:
            logger.error(f"StatusPanel refresh failed: {e}")
