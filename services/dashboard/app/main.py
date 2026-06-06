from textual.app import App
from textual.binding import Binding
from textual.widgets import Header, Footer

from app.screens.home import HomeScreen
from app.screens.asteroids import AsteroidsScreen
from app.screens.charts import ChartsScreen
from app.screens.pipeline import PipelineScreen
from app.screens.logs import LogsScreen


class AstroForgeDashboard(App):
    """AstroForge Dashboard - Terminal UI for Asteroid Analysis"""

    CSS = """
    Screen {
        background: #12170f;
        color: #f1e7af;
    }

    Button {
        margin: 0 1;
    }

    Button.primary {
        background: #8f9a4d;
        color: #1c2113;
    }

    DataTable {
        border: solid #b9982f;
    }

    DataTable > .datatable--header {
        background: #2f341e;
        color: #f1e7af;
        text-style: bold;
    }

    RichLog {
        border: solid #b9982f;
    }
    """

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
        self.push_screen("home")

    def action_show_home(self) -> None:
        """Navigate to home screen."""
        self.push_screen("home")

    def action_show_asteroids(self) -> None:
        """Navigate to asteroids screen."""
        self.push_screen("asteroids")

    def action_show_charts(self) -> None:
        """Navigate to charts screen."""
        self.push_screen("charts")

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