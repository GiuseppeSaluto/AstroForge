"""Void theme — single source of truth for all palette values.

TCSS (Textual CSS) doesn't support web-standard CSS custom properties.
Instead, call theme.apply(css_string) to substitute $token placeholders:

    CSS = theme.apply(\"\"\"
    Screen {
        background: $bg;
        color: $text;
    }
    \"\"\")

Available tokens: $bg $surface $accent $muted $border $border_dim $text
                  $critical $high $medium $low

Python code (Rich markup, plotext) imports the constants directly.
"""
import string as _string

# ── Base palette ──────────────────────────────────────────────────────────────
BG         = "#0c0c0c"   # main background
SURFACE    = "#1a1a1a"   # panels, header bars, dialog backgrounds
ACCENT     = "#ffffff"   # primary: active borders, titles, primary buttons
MUTED      = "#777777"   # secondary text, dim labels, inactive elements
BORDER     = "#ffffff"   # prominent borders (table outlines, active panels)
BORDER_DIM = "#333333"   # subtle borders (inactive sections)
TEXT       = "#e0e0e0"   # body text

# ── Semantic / risk ───────────────────────────────────────────────────────────
CRITICAL = "#ff1744"
HIGH     = "#ff6d00"
MEDIUM   = "#ffd600"
LOW      = "#69f0ae"

# ── Plotext chart colors (plotext uses named colors, not hex) ─────────────────
CHART_SAFE      = "bright-green"
CHART_HAZARDOUS = "red"
CHART_BAR       = "white"

# ── Lookup tables for Rich markup ─────────────────────────────────────────────
RISK_COLOR: dict[str, str] = {
    "Critical": CRITICAL,
    "High":     HIGH,
    "Medium":   MEDIUM,
    "Low":      LOW,
}

LOG_COLOR: dict[str, str] = {
    "ERROR":   CRITICAL,
    "WARNING": HIGH,
    "DEBUG":   MUTED,
    "INFO":    LOW,
}

def apply(css: str) -> str:
    """Substitute theme tokens into a TCSS string using $name placeholders."""
    return _string.Template(css).substitute(
        bg=BG, surface=SURFACE, accent=ACCENT,
        muted=MUTED, border=BORDER, border_dim=BORDER_DIM, text=TEXT,
        critical=CRITICAL, high=HIGH, medium=MEDIUM, low=LOW,
    )
