import asyncio
import logging
from datetime import datetime

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static
from textual import work

from app.client.api_client import get_close_approaches
from app import theme

logger = logging.getLogger(__name__)

_LUNAR_DIST_KM = 384_400


class CloseApproachesPanel(Widget):
    """Bottom-right home panel: NEOs ranked by miss distance."""

    DEFAULT_CSS = theme.apply("""
    CloseApproachesPanel {
        border: solid $border_dim;
        padding: 1;
        height: 1fr;
    }

    CloseApproachesPanel .ca-title {
        color: $accent;
        text-style: bold;
        margin: 0 0 1 0;
    }
    """)

    def compose(self) -> ComposeResult:
        yield Static("", id="ca_title", classes="ca-title")
        yield Static("", id="ca_meta")
        yield Static("", id="ca_list")

    def on_mount(self) -> None:
        self.query_one("#ca_title", Static).update(
            f"[{theme.ACCENT}]CLOSE APPROACHES  ·  Sorted by Miss Distance[/{theme.ACCENT}]"
        )
        self.refresh_data()

    @work(exclusive=True)
    async def refresh_data(self) -> None:
        try:
            loop = asyncio.get_event_loop()
            approaches = await loop.run_in_executor(
                None, lambda: get_close_approaches(limit=8)
            )

            now_str = datetime.now().strftime("%H:%M:%S")

            if not approaches:
                self.query_one("#ca_meta").update(
                    f"  [{theme.MUTED}]updated {now_str}[/{theme.MUTED}]"
                )
                self.query_one("#ca_list").update(
                    f"\n  [{theme.MUTED}]No data available.[/{theme.MUTED}]"
                )
                return

            self.query_one("#ca_meta").update(
                f"  [{theme.MUTED}]{len(approaches)} nearest  ·  {now_str}[/{theme.MUTED}]"
            )

            header = (
                f"  [{theme.MUTED}]"
                f"{'DATE':<12}{'MISS DIST':>12}{'LUNAR':>7}{'VEL km/s':>9}  RISK        NAME"
                f"[/{theme.MUTED}]"
            )
            lines = [header]

            for a in approaches:
                risk_level = a.get("risk_level", "Unknown")
                miss_km = a.get("miss_km", 0)
                miss_m_km = miss_km / 1_000_000
                lunar = miss_km / _LUNAR_DIST_KM
                vel = a.get("velocity_kps", 0.0)
                date = a.get("close_approach_date", "?")
                name = (a.get("name") or "?").strip("()")[:22]
                color = theme.RISK_COLOR.get(risk_level, theme.TEXT)
                hazard_marker = (
                    f"[{theme.CRITICAL}]![/{theme.CRITICAL}]"
                    if a.get("is_hazardous") else " "
                )

                lines.append(
                    f"  [{theme.MUTED}]{date:<12}[/{theme.MUTED}]"
                    f"[{theme.ACCENT}]{miss_m_km:>10.2f}M[/{theme.ACCENT}]"
                    f"[{theme.MUTED}]{lunar:>6.1f}L[/{theme.MUTED}]"
                    f"[{theme.MUTED}]{vel:>9.2f}[/{theme.MUTED}]"
                    f"  [{color}]{risk_level:<8}[/{color}]"
                    f"  [{theme.TEXT}]{name}[/{theme.TEXT}]"
                    f" {hazard_marker}"
                )

            self.query_one("#ca_list").update("\n".join(lines))

        except Exception as e:
            logger.error(f"CloseApproachesPanel refresh failed: {e}")
            self.query_one("#ca_list").update(
                f"  [{theme.CRITICAL}]Failed to load data.[/{theme.CRITICAL}]"
            )
