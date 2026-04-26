from textual.app import App
from textual.binding import Binding
from textual.widgets import Header, Footer

from app.screens.home import HomeScreen
from app.screens.asteroids import AsteroidsScreen
from app.screens.pipeline import PipelineScreen
from app.screens.logs import LogsScreen


class AstroForgeDashboard(App):
    """AstroForge Dashboard - Terminal UI for Asteroid Analysis"""

    CSS = """
    Screen {
        background: $surface;
        color: $text;
    }

    Button {
        margin: 0 1;
    }

    Button.primary {
        background: $primary;
        color: $panel;
    }

    DataTable {
        border: solid $accent;
    }

    DataTable > .datatable--header {
        background: $boost;
        color: $text;
        text-style: bold;
    }

    RichLog {
        border: solid $accent;
    }
    """

    TITLE = "AstroForge"
    SUB_TITLE = "Asteroid Risk Analysis Dashboard"

    SCREENS = {
        "home": HomeScreen,
        "asteroids": AsteroidsScreen,
        "pipeline": PipelineScreen,
        "logs": LogsScreen,
    }

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("h", "show_home", "Home", show=True),
        Binding("a", "show_asteroids", "Asteroids", show=True),
        Binding("p", "show_pipeline", "Pipeline", show=True),
        Binding("l", "show_logs", "Logs", show=True),
    ]

    def on_mount(self) -> None:
        """Initialize the application and show home screen."""
        self.push_screen("home")

    def action_show_home(self) -> None:
        """Navigate to home screen."""
        self.push_screen("home")

    def action_show_asteroids(self) -> None:
        """Navigate to asteroids screen."""
        self.push_screen("asteroids")

    def action_show_pipeline(self) -> None:
        """Navigate to pipeline control screen."""
        self.push_screen("pipeline")

    def action_show_logs(self) -> None:
        """Navigate to logs screen."""
        self.push_screen("logs")


def run():
    """Entry point for the dashboard."""
    app = AstroForgeDashboard()
    app.run()


if __name__ == "__main__":
    run()