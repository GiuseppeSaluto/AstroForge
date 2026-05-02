from textual.widgets import Static


class StatsPanel(Static):
    """A reusable widget for displaying statistics."""

    DEFAULT_CSS = """
    StatsPanel {
        border: solid #b9982f;
        padding: 0 1;
        height: auto;
    }

    StatsPanel > Static {
        margin: 0;
        height: 1;
    }
    """

    def __init__(self, title: str, stats: dict | None = None):
        super().__init__()
        self.title = title
        self.stats = stats or {}

    def render(self) -> str:
        """Render the stats panel."""
        lines = [f"[bold]{self.title}[/bold]"]
        for key, value in self.stats.items():
            lines.append(f"  {key}: {value}")
        return "\n".join(lines)

    def update_stats(self, stats: dict) -> None:
        """Update statistics."""
        self.stats = stats
        self.update(self.render())
