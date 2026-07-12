import asyncio
import logging

from textual import work
from textual.widgets import Static

from app.client.api_client import get_system_status
from app import theme

logger = logging.getLogger(__name__)

_REFRESH_INTERVAL = 10


class GlobalStatusBar(Static):
    """Service-status strip docked at the top of every screen, independent of Home."""

    DEFAULT_CSS = theme.apply("""
    GlobalStatusBar {
        height: 1;
        background: $surface;
        content-align: center middle;
    }
    """)

    def on_mount(self) -> None:
        self.refresh_data()
        self.set_interval(_REFRESH_INTERVAL, self.refresh_data)

    @work(exclusive=True)
    async def refresh_data(self) -> None:
        try:
            loop = asyncio.get_event_loop()
            status = await loop.run_in_executor(None, get_system_status)

            backend = status.get("backend", {})
            rust = status.get("rust_engine", {})
            backend_ok = backend.get("status") == "healthy"
            mongodb_ok = backend.get("components", {}).get("mongodb") == "connected"
            rust_ok = rust.get("status") == "ok"

            def _dot(ok: bool) -> str:
                c = theme.LOW if ok else theme.CRITICAL
                return f"[{c}]●[/{c}]"

            dots = (
                f"{_dot(backend_ok)} [{theme.MUTED}]Backend[/{theme.MUTED}]  "
                f"{_dot(mongodb_ok)} [{theme.MUTED}]MongoDB[/{theme.MUTED}]  "
                f"{_dot(rust_ok)} [{theme.MUTED}]Rust Engine[/{theme.MUTED}]"
            )
            self.update(dots)
        except Exception as e:
            logger.error(f"GlobalStatusBar refresh failed: {e}")
