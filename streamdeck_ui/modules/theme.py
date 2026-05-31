"""Light and dark theme handling for the Stream Deck UI window.

Applies a dark colour palette to the whole Qt application when dark mode is
enabled, and restores the platform default look when it is disabled. The
preference is persisted with :class:`~PySide6.QtCore.QSettings` so it survives
restarts.
"""

from typing import Optional

from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

DARK_MODE_SETTING = "dark_mode"

# Tooltips are not covered by the palette consistently across styles, so they
# get an explicit stylesheet when dark mode is active.
_DARK_TOOLTIP_STYLE = "QToolTip { color: #dcdcdc; background-color: #2a2a2a; border: 1px solid #3a3a3a; }"

# The platform default look, captured the first time a theme is applied so it
# can be restored when the user turns dark mode back off.
_default_palette: Optional[QPalette] = None
_default_style: Optional[str] = None


def _build_dark_palette() -> QPalette:
    """Builds a dark colour palette suitable for the Fusion style."""
    window = QColor(53, 53, 53)
    base = QColor(35, 35, 35)
    alternate_base = QColor(45, 45, 45)
    text = QColor(220, 220, 220)
    disabled_text = QColor(127, 127, 127)
    highlight = QColor(42, 130, 218)

    palette = QPalette()
    role = QPalette.ColorRole
    group = QPalette.ColorGroup

    palette.setColor(role.Window, window)
    palette.setColor(role.WindowText, text)
    palette.setColor(role.Base, base)
    palette.setColor(role.AlternateBase, alternate_base)
    palette.setColor(role.ToolTipBase, window)
    palette.setColor(role.ToolTipText, text)
    palette.setColor(role.Text, text)
    palette.setColor(role.Button, window)
    palette.setColor(role.ButtonText, text)
    palette.setColor(role.BrightText, QColor(255, 80, 80))
    palette.setColor(role.Link, highlight)
    palette.setColor(role.Highlight, highlight)
    palette.setColor(role.HighlightedText, QColor(0, 0, 0))
    palette.setColor(role.PlaceholderText, disabled_text)

    for disabled_role in (role.WindowText, role.Text, role.ButtonText):
        palette.setColor(group.Disabled, disabled_role, disabled_text)
    palette.setColor(group.Disabled, role.Highlight, QColor(80, 80, 80))
    palette.setColor(group.Disabled, role.HighlightedText, disabled_text)

    return palette


def apply_theme(app: QApplication, dark: bool) -> None:
    """Applies the dark or light theme to the whole application."""
    global _default_palette, _default_style

    if _default_palette is None:
        _default_palette = app.palette()
    if _default_style is None:
        current_style = app.style()
        _default_style = current_style.objectName() if current_style else ""

    if dark:
        app.setStyle("Fusion")
        app.setPalette(_build_dark_palette())
        app.setStyleSheet(_DARK_TOOLTIP_STYLE)
    else:
        if _default_style:
            app.setStyle(_default_style)
        app.setPalette(_default_palette)
        app.setStyleSheet("")


def is_dark_mode_enabled(settings: QSettings) -> bool:
    """Returns the persisted dark mode preference (defaults to off)."""
    return bool(settings.value(DARK_MODE_SETTING, False, type=bool))


def set_dark_mode_enabled(settings: QSettings, enabled: bool) -> None:
    """Persists the dark mode preference."""
    settings.setValue(DARK_MODE_SETTING, enabled)
