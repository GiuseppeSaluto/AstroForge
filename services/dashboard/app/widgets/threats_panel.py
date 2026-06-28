import asyncio
import logging
from datetime import datetime

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static
from textual import work

from app.client.api_client import get_analyzed_asteroids
from app import theme

logger = logging.getLogger(__name__)

# Sort priority: lower = more dangerous
_RISK_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


class TopThreatsPanel(Widget):
    """Right home panel: top analyzed asteroids ranked by risk score from the Rust engine."""

    DEFAULT_CSS = theme.apply("""
    TopThreatsPanel {
        border: solid $border_dim;
        padding: 1;
        height: 100%;
    }

    TopThreatsPanel .tp-title {
        color: $accent;
        text-style: bold;
        margin: 0 0 1 0;
    }
    """)

    def compose(self) -> ComposeResult:
        yield Static("", id="tp_title", classes="tp-title")
        yield Static("", id="tp_meta")
        yield Static("", id="tp_list")

    def on_mount(self) -> None:
        self.query_one("#tp_title", Static).update(
            f"[{theme.ACCENT}]── TOP THREATS  ─  Rust Engine Output[/{theme.ACCENT}]"
        )
        self.refresh_data()

    @work(exclusive=True)
    async def refresh_data(self) -> None:
        try:
            loop = asyncio.get_event_loop()
            asteroids = await loop.run_in_executor(
                None, lambda: get_analyzed_asteroids(limit=200)
            )

            now_str = datetime.now().strftime("%H:%M:%S")

            if not asteroids:
                self.query_one("#tp_meta").update(
                    f"  [{theme.MUTED}]updated {now_str}[/{theme.MUTED}]"
                )
                self.query_one("#tp_list").update(
                    f"\n  [{theme.MUTED}]No analyzed asteroids yet.\n"
                    f"  Run the pipeline to populate.[/{theme.MUTED}]"
                )
                return

            # Deduplicate by id, sort by risk level then score descending
            seen: set[str] = set()
            unique: list[dict] = []
            for a in asteroids:
                aid = a.get("id", "")
                if aid and aid not in seen:
                    seen.add(aid)
                    unique.append(a)

            ranked = sorted(
                unique,
                key=lambda a: (
                    _RISK_ORDER.get(a.get("risk_level", "Low"), 3),
                    -a.get("risk_score", 0.0),
                ),
            )

            total = len(unique)
            critical = sum(1 for a in unique if a.get("risk_level") == "Critical")
            high = sum(1 for a in unique if a.get("risk_level") == "High")

            self.query_one("#tp_meta").update(
                f"  [{theme.MUTED}]{total} analyzed  ·  "
                f"[{theme.CRITICAL}]{critical} critical[/{theme.CRITICAL}]"
                f"[{theme.MUTED}]  /  [/{theme.MUTED}]"
                f"[{theme.HIGH}]{high} high[/{theme.HIGH}]"
                f"[{theme.MUTED}]  ·  {now_str}[/{theme.MUTED}]"
            )

            header = (
                f"  [{theme.MUTED}]{'LEVEL':<10}{'SCORE':>6}{'ENERGY':>10}  NAME[/{theme.MUTED}]"
            )
            lines = [header]
            for a in ranked[:8]:
                risk_level = a.get("risk_level", "Low")
                score = a.get("risk_score", 0.0)
                energy = a.get("energy_mt", 0.0)
                name = (a.get("name") or "?").strip("()")[:24]
                color = theme.RISK_COLOR.get(risk_level, theme.TEXT)

                lines.append(
                    f"  [{color}]{risk_level:<10}[/{color}]"
                    f"[{theme.ACCENT}]{score:>6.1f}[/{theme.ACCENT}]"
                    f"[{theme.MUTED}]{energy:>9.2f}MT[/{theme.MUTED}]"
                    f"  [{theme.TEXT}]{name}[/{theme.TEXT}]"
                )

            self.query_one("#tp_list").update("\n".join(lines))

        except Exception as e:
            logger.error(f"TopThreatsPanel refresh failed: {e}")
            self.query_one("#tp_list").update(
                f"  [{theme.CRITICAL}]Failed to load threat data.[/{theme.CRITICAL}]"
            )
