from textual.screen import Screen
from textual.widgets import Static


class HomeScreen(Screen):
    """Home screen of the AstroForge dashboard."""

    def compose(self):
        yield Static("AstroForge", id="title")
        yield Static("Backend: unknown", id="status")
        yield Static("Hints: q - Quit, h - Home", id="hints")