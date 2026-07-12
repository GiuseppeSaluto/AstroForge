from textual.app import App
from textual.binding import Binding
from textual.theme import Theme
from textual.widgets import Header, Footer

from app.screens.home import HomeScreen
from app.screens.asteroids import AsteroidsScreen
from app.screens.charts import ChartsScreen
from app.screens.pipeline import PipelineScreen
from app.screens.logs import LogsScreen
from app import theme

VOID_THEME = Theme(
    name="void",
    primary=theme.ACCENT,
    secondary=theme.MUTED,
    accent=theme.ACCENT,
    foreground=theme.TEXT,
    background=theme.BG,
    surface=theme.SURFACE,
    panel=theme.SURFACE,
    error=theme.CRITICAL,
    warning=theme.HIGH,
    success=theme.LOW,
    dark=True,
)


class AstroForgeDashboard(App):
    """AstroForge Dashboard - Terminal UI for Asteroid Analysis"""

    CSS = theme.apply("""
    Screen {
        background: $bg;
        color: $text;
    }

    Button {
        margin: 0 1;
    }

    Button.-primary {
        background: $accent;
        color: $bg;
        text-style: bold;
        border-top: tall $accent;
        border-bottom: tall $border_dim;
    }

    Button.-primary:hover {
        background: $muted;
        color: $bg;
        border-top: tall $accent;
        border-bottom: tall $border_dim;
    }

    DataTable {
        border: solid $border;
    }

    DataTable > .datatable--header {
        background: $surface;
        color: $accent;
        text-style: bold;
    }

    RichLog {
        border: solid $border_dim;
    }
    """)

    TITLE = "AstroForge"
    SUB_TITLE = "Asteroid Risk Analysis Dashboard"

    SCREENS = {
        "home": HomeScreen,
        "asteroids": AsteroidsScreen,
        "charts": ChartsScreen,
        "pipeline": PipelineScreen,
        "logs": LogsScreen,
    }

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("h", "show_home", "Home", show=True),
        Binding("a", "show_asteroids", "Asteroids", show=True),
        Binding("c", "show_charts", "Charts", show=True),
        Binding("p", "show_pipeline", "Pipeline", show=True),
        Binding("l", "show_logs", "Logs", show=True),
    ]

    def on_mount(self) -> None:
        """Initialize the application and show home screen."""
        self.register_theme(VOID_THEME)
        self.theme = "void"
        self.push_screen("home")

    def action_show_home(self) -> None:
        """Navigate to home screen."""
        self.switch_screen("home")

    def action_show_asteroids(self) -> None:
        """Navigate to asteroids screen."""
        self.switch_screen("asteroids")

    def action_show_charts(self) -> None:
        """Navigate to charts screen."""
        self.switch_screen("charts")

    def action_show_pipeline(self) -> None:
        """Navigate to pipeline control screen."""
        self.switch_screen("pipeline")

    def action_show_logs(self) -> None:
        """Navigate to logs screen."""
        self.switch_screen("logs")


def run():
    """Entry point for the dashboard."""
    app = AstroForgeDashboard()
    app.run()


if __name__ == "__main__":
    run()