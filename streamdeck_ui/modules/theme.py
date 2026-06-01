"""Light, dark and Windows XP theme handling for the Stream Deck UI window.

Applies a colour palette (and, for the XP theme, a full stylesheet) to the whole
Qt application, and restores the platform default look when no special theme is
enabled. The preferences are persisted with
:class:`~PySide6.QtCore.QSettings` so they survive restarts.
"""

from typing import Optional

from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

DARK_MODE_SETTING = "dark_mode"
XP_THEME_SETTING = "xp_theme"

# Tooltips are not covered by the palette consistently across styles, so they
# get an explicit stylesheet when dark mode is active.
_DARK_TOOLTIP_STYLE = "QToolTip { color: #dcdcdc; background-color: #2a2a2a; border: 1px solid #3a3a3a; }"

# The platform default look, captured the first time a theme is applied so it
# can be restored when the user turns the special themes back off.
_default_palette: Optional[QPalette] = None
_default_style: Optional[str] = None

# The signature Windows XP "Luna" surface colours.
_XP_FACE = QColor(236, 233, 216)  # #ECE9D8 dialog / control background
_XP_SELECTION = QColor(49, 106, 197)  # #316AC5 highlight blue
_XP_TOOLTIP = QColor(255, 255, 225)  # #FFFFE1 classic pale-yellow tooltip

# A Luna-flavoured stylesheet: rounded, gradient buttons, blue selection,
# white sunken inputs and blue menu highlights. The deck keys carry their own
# per-widget stylesheets, which take precedence over this application-wide one,
# so the black key grid is left untouched.
_XP_STYLESHEET = """
QMainWindow, QDialog, QWidget#centralwidget {
    background-color: #ECE9D8;
}
* {
    font-family: "Tahoma", "Segoe UI", "DejaVu Sans", sans-serif;
}

QMenuBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #FBFBF8, stop:1 #ECE9D8);
    border-bottom: 1px solid #ACA899;
}
QMenuBar::item {
    background: transparent;
    padding: 3px 8px;
}
QMenuBar::item:selected {
    background: #C1D2EE;
    border: 1px solid #316AC5;
    border-radius: 2px;
}
QMenu {
    background-color: #FFFFFF;
    border: 1px solid #ACA899;
}
QMenu::item {
    padding: 3px 24px 3px 20px;
}
QMenu::item:selected {
    background-color: #316AC5;
    color: #FFFFFF;
}
QMenu::separator {
    height: 1px;
    background: #ACA899;
    margin: 3px 0;
}

QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #FFFFFF, stop:0.45 #F5F4EE, stop:0.5 #ECE9D8, stop:1 #DEDACA);
    border: 1px solid #8A8A7A;
    border-radius: 3px;
    padding: 3px 12px;
    min-height: 18px;
    color: #000000;
}
QPushButton:hover {
    border: 1px solid #E8A200;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #FFFFFF, stop:0.45 #FEFBF0, stop:0.5 #FDF4D8, stop:1 #FCEEBE);
}
QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #DEDACA, stop:1 #ECE9D8);
    border: 1px solid #707064;
}
QPushButton:default {
    border: 1px solid #316AC5;
}
QPushButton:disabled {
    color: #A0A0A0;
    border: 1px solid #C5C2B8;
    background: #ECE9D8;
}

QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox {
    background-color: #FFFFFF;
    border: 1px solid #7F9DB9;
    border-radius: 0px;
    padding: 2px;
    selection-background-color: #316AC5;
    selection-color: #FFFFFF;
}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #316AC5;
}

QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #7F9DB9;
    border-radius: 0px;
    padding: 2px 4px;
    min-height: 18px;
}
QComboBox:focus {
    border: 1px solid #316AC5;
}
QComboBox::drop-down {
    width: 18px;
    border-left: 1px solid #7F9DB9;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #FFFFFF, stop:1 #DEDACA);
}
QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    border: 1px solid #7F9DB9;
    selection-background-color: #316AC5;
    selection-color: #FFFFFF;
}

QTabWidget::pane {
    border: 1px solid #919B9C;
    background: #ECE9D8;
    top: -1px;
}
QTabBar::tab {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #FCFCFB, stop:1 #E3DFD0);
    border: 1px solid #919B9C;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 4px 12px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #FFFFFF, stop:1 #ECE9D8);
    border-bottom: 1px solid #ECE9D8;
}
QTabBar::tab:hover:!selected {
    background: #FDF4D8;
}

QGroupBox {
    border: 1px solid #ACA899;
    border-radius: 3px;
    margin-top: 8px;
    background: #ECE9D8;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 3px;
    color: #15428B;
}

QProgressBar {
    border: 1px solid #7F9DB9;
    border-radius: 0px;
    background: #FFFFFF;
    text-align: center;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #A6E27F, stop:1 #4CA11E);
    width: 8px;
    margin: 1px;
}

QCheckBox::indicator, QRadioButton::indicator {
    width: 13px;
    height: 13px;
}
QCheckBox::indicator:unchecked, QRadioButton::indicator:unchecked {
    background: #FFFFFF;
    border: 1px solid #7F9DB9;
}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background: #FFFFFF;
    border: 1px solid #316AC5;
}

QScrollBar:vertical {
    background: #ECE9D8;
    width: 16px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #F5F4EE, stop:1 #C9C5B4);
    border: 1px solid #919B9C;
    border-radius: 2px;
    min-height: 20px;
}
QScrollBar:horizontal {
    background: #ECE9D8;
    height: 16px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #F5F4EE, stop:1 #C9C5B4);
    border: 1px solid #919B9C;
    border-radius: 2px;
    min-width: 20px;
}
QScrollBar::add-line, QScrollBar::sub-line {
    background: none;
    border: none;
}

QMenuBar, QStatusBar {
    color: #000000;
}
QToolTip {
    color: #000000;
    background-color: #FFFFE1;
    border: 1px solid #000000;
    padding: 2px;
}
"""


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


def _build_xp_palette() -> QPalette:
    """Builds a Windows XP "Luna" colour palette for the Fusion style."""
    text = QColor(0, 0, 0)
    disabled_text = QColor(160, 160, 160)

    palette = QPalette()
    role = QPalette.ColorRole
    group = QPalette.ColorGroup

    palette.setColor(role.Window, _XP_FACE)
    palette.setColor(role.WindowText, text)
    palette.setColor(role.Base, QColor(255, 255, 255))
    palette.setColor(role.AlternateBase, QColor(245, 244, 238))
    palette.setColor(role.ToolTipBase, _XP_TOOLTIP)
    palette.setColor(role.ToolTipText, text)
    palette.setColor(role.Text, text)
    palette.setColor(role.Button, _XP_FACE)
    palette.setColor(role.ButtonText, text)
    palette.setColor(role.BrightText, QColor(255, 0, 0))
    palette.setColor(role.Link, QColor(0, 0, 238))
    palette.setColor(role.Highlight, _XP_SELECTION)
    palette.setColor(role.HighlightedText, QColor(255, 255, 255))
    palette.setColor(role.PlaceholderText, disabled_text)

    for disabled_role in (role.WindowText, role.Text, role.ButtonText):
        palette.setColor(group.Disabled, disabled_role, disabled_text)

    return palette


def _capture_default_look(app: QApplication) -> None:
    """Remembers the platform default palette/style on first use."""
    global _default_palette, _default_style

    if _default_palette is None:
        _default_palette = app.palette()
    if _default_style is None:
        current_style = app.style()
        _default_style = current_style.objectName() if current_style else ""


def apply_theme(app: QApplication, dark: bool = False, xp: bool = False) -> None:
    """Applies the selected theme to the whole application.

    The XP theme takes precedence over dark mode when both are requested; the
    callers keep the two preferences mutually exclusive.
    """
    _capture_default_look(app)

    if xp:
        app.setStyle("Fusion")
        app.setPalette(_build_xp_palette())
        app.setStyleSheet(_XP_STYLESHEET)
    elif dark:
        app.setStyle("Fusion")
        app.setPalette(_build_dark_palette())
        app.setStyleSheet(_DARK_TOOLTIP_STYLE)
    else:
        if _default_style:
            app.setStyle(_default_style)
        if _default_palette is not None:
            app.setPalette(_default_palette)
        app.setStyleSheet("")


def is_dark_mode_enabled(settings: QSettings) -> bool:
    """Returns the persisted dark mode preference (defaults to off)."""
    return bool(settings.value(DARK_MODE_SETTING, False, type=bool))


def set_dark_mode_enabled(settings: QSettings, enabled: bool) -> None:
    """Persists the dark mode preference."""
    settings.setValue(DARK_MODE_SETTING, enabled)


def is_xp_theme_enabled(settings: QSettings) -> bool:
    """Returns the persisted Windows XP theme preference (defaults to off)."""
    return bool(settings.value(XP_THEME_SETTING, False, type=bool))


def set_xp_theme_enabled(settings: QSettings, enabled: bool) -> None:
    """Persists the Windows XP theme preference."""
    settings.setValue(XP_THEME_SETTING, enabled)
