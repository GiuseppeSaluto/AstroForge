from rich.style import Style
from rich.text import Text
from textual.widget import Widget

from app import theme

_RISK_STYLE: dict[str, str] = {
    "Low":      theme.LOW,
    "Medium":   theme.MEDIUM,
    "High":     theme.HIGH,
    "Critical": theme.CRITICAL,
}

_ASCII_FRAMES: dict[str, list[str]] = {
    "Low": [
        "    .  *  .   \n"
        "  .  ░░░░  .  \n"
        "    ░░░░░░    \n"
        "  .  ░░░░  .  \n"
        "    .  *  .   ",

        "    *  .  *   \n"
        "  .  ░░░░  .  \n"
        "    ░░░░░░    \n"
        "  .  ░░░░  .  \n"
        "    *  .  *   ",
    ],
    "Medium": [
        "   .  *  .    \n"
        "  . ▒▒▒▒▒ .  \n"
        "  ▒▒▒▒▒▒▒▒   \n"
        " ▒▒▒▒▒▒▒▒▒▒  \n"
        "  . ▒▒▒▒▒ .  \n"
        "   .  *  .    ",

        "   *  .  *    \n"
        "  . ▒▒▒▒▒ .  \n"
        "  ▒▒▒▒▒▒▒▒   \n"
        " ▒▒▒▒▒▒▒▒▒▒  \n"
        "  . ▒▒▒▒▒ .  \n"
        "   *  .  *    ",
    ],
    "High": [
        "  *   .   *   \n"
        "  . ████▓ .  \n"
        "  ████████   \n"
        " ██████████  \n"
        "  . ████▓ .  \n"
        "  *   .   *   ",

        "  .   *   .   \n"
        "  . ████▓ .  \n"
        "  ████████   \n"
        " ██████████  \n"
        "  . ████▓ .  \n"
        "  .   *   .   ",
    ],
    "Critical": [
        " * .  ☄  . * \n"
        "  .██████▓.  \n"
        " ██  ████████\n"
        " ████████  ██\n"
        "  .██████▓.  \n"
        " * .  ☄  . * ",

        " . *  ☄  * . \n"
        "  .██████▓.  \n"
        " ██  ████████\n"
        " ████████  ██\n"
        "  .██████▓.  \n"
        " . *  ☄  * . ",
    ],
}

_FALLBACK = _ASCII_FRAMES["Low"]


class AsteroidSprite(Widget):
    """Animated ASCII asteroid, color and shape driven by risk level."""

    DEFAULT_CSS = """
    AsteroidSprite {
        width: 22;
        height: 8;
        content-align: center middle;
    }
    """

    def __init__(self, risk_level: str) -> None:
        super().__init__()
        self._frames = _ASCII_FRAMES.get(risk_level, _FALLBACK)
        self._style = Style(color=_RISK_STYLE.get(risk_level, theme.MUTED))
        self._idx = 0

    def on_mount(self) -> None:
        self.set_interval(0.5, self._advance)

    def _advance(self) -> None:
        self._idx = (self._idx + 1) % len(self._frames)
        self.refresh()

    def render(self) -> Text:
        t = Text(self._frames[self._idx], no_wrap=True)
        t.stylize(self._style)
        return t
